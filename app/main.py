import json
import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.logging import configure_logging
from app.models import TelegramAudio, TelegramMessage, TelegramUpdate, TelegramVoice, WebhookAck
from app.responses import error_response, success_response
from app.telegram_normalizer import (
    FORWARDED_EMPTY_PROMPT,
    UNSUPPORTED_MESSAGE_PROMPT,
    VOICE_ONLY_PROMPT,
    normalize_update,
)
from app.todoist import (
    TodoistServiceError,
    cleanup_completed_subtasks,
    create_subtask,
    ensure_todo_later_task,
)
from app.telegram import download_telegram_file, get_telegram_file_url, send_telegram_message
from app.transcribe import TranscriptionError, transcribe_audio_with_gemini

logger = logging.getLogger("gatchan")

@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    try:
        get_settings()
        logger.info("settings_loaded")
        yield
    except Exception as exc:
        logger.error("settings_load_failed", exc_info=exc)
        raise


app = FastAPI(title="Gatchan Webhook", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("validation_failed", extra={"errors": exc.errors()})
    return error_response("Invalid request payload", status_code=422)


def _message_metadata(message: Optional[TelegramMessage]) -> dict:
    if not message:
        return {}
    return {
        "message_id": message.message_id,
        "chat_id": message.chat.id if message.chat else None,
        "from_id": message.from_user.id if message.from_user else None,
        "date": message.date,
    }


def _todoist_description(update_id: int, message: Optional[TelegramMessage]) -> str:
    metadata = _message_metadata(message)
    parts = [
        f"update_id={update_id}",
        f"message_id={metadata.get('message_id')}",
        f"chat_id={metadata.get('chat_id')}",
        f"from_id={metadata.get('from_id')}",
        f"date={metadata.get('date')}",
    ]
    return "meta: " + " ".join(parts)


def _append_image_url(description: str, image_url: str) -> str:
    return f"{description}\nimage_url={image_url}"


def _extract_photo_file_id(message: Optional[TelegramMessage]) -> Optional[str]:
    if not message or not message.photo:
        return None
    return message.photo[-1].file_id


def _extract_audio_info(
    message: Optional[TelegramMessage],
) -> Optional[tuple[str, str]]:
    if not message:
        return None
    voice: Optional[TelegramVoice] = message.voice
    audio: Optional[TelegramAudio] = message.audio
    if voice:
        return voice.file_id, (voice.mime_type or "audio/ogg")
    if audio:
        return audio.file_id, (audio.mime_type or "audio/mpeg")
    return None


def _should_transcribe(message: Optional[TelegramMessage]) -> bool:
    if not message:
        return False
    if message.text or message.caption:
        return False
    return bool(message.voice or message.audio)


def _is_whitelisted(message: Optional[TelegramMessage], settings: Settings) -> bool:
    allowed_users = settings.telegram_allowed_user_ids
    allowed_chats = settings.telegram_allowed_chat_ids
    if not allowed_users and not allowed_chats:
        return True
    if not message:
        return False
    chat_id = message.chat.id if message.chat else None
    user_id = message.from_user.id if message.from_user else None
    return (chat_id in allowed_chats if chat_id is not None else False) or (
        user_id in allowed_users if user_id is not None else False
    )


@app.get("/health")
def health() -> JSONResponse:
    return success_response({"status": "ok"})


@app.post("/webhook")
def webhook(
    update: TelegramUpdate,
    settings: Settings = Depends(get_settings),
    telegram_secret: Optional[str] = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> JSONResponse:
    if telegram_secret != settings.telegram_webhook_secret.get_secret_value():
        logger.warning("webhook_forbidden")
        return error_response("Unauthorized", status_code=401)

    request_id = str(uuid4())
    message = update.message or update.edited_message or update.channel_post or update.edited_channel_post
    if not _is_whitelisted(message, settings):
        metadata = {
            "request_id": request_id,
            "update_id": update.update_id,
            **_message_metadata(message),
        }
        logger.info("webhook_denied %s", json.dumps(metadata, separators=(",", ":"), sort_keys=True))
        if settings.telegram_whitelist_reply:
            _send_telegram_feedback(
                message,
                "未授权：请联系管理员开通权限。",
                settings.telegram_bot_token.get_secret_value(),
                request_id,
            )
        return success_response({"received": True, "authorized": False}, meta={"request_id": request_id})

    audio_info = _extract_audio_info(message)
    transcript: Optional[str] = None
    if audio_info and _should_transcribe(message):
        if settings.transcribe_provider != "gemini" or not settings.gemini_api_key:
            _send_telegram_feedback(
                message,
                "转写失败：未配置转写服务。",
                settings.telegram_bot_token.get_secret_value(),
                request_id,
            )
            return success_response(
                WebhookAck(received=True, normalized_text=VOICE_ONLY_PROMPT).model_dump(),
                meta={"request_id": request_id},
            )
        file_id, mime_type = audio_info
        try:
            file_url = get_telegram_file_url(file_id, settings.telegram_bot_token.get_secret_value())
            audio_bytes = download_telegram_file(file_url)
            transcript = transcribe_audio_with_gemini(
                audio_bytes,
                mime_type,
                settings.gemini_api_key.get_secret_value(),
            )
        except TranscriptionError as exc:
            _send_telegram_feedback(
                message,
                f"转写失败：{exc.user_message}",
                settings.telegram_bot_token.get_secret_value(),
                request_id,
            )
            return success_response(
                WebhookAck(received=True, normalized_text=VOICE_ONLY_PROMPT).model_dump(),
                meta={"request_id": request_id},
            )
        except Exception as exc:  # pragma: no cover - safety net
            logger.warning("transcription_failed", extra={"request_id": request_id, "error": str(exc)})
            _send_telegram_feedback(
                message,
                "转写失败：服务不可用。",
                settings.telegram_bot_token.get_secret_value(),
                request_id,
            )
            return success_response(
                WebhookAck(received=True, normalized_text=VOICE_ONLY_PROMPT).model_dump(),
                meta={"request_id": request_id},
            )

    normalized_text = transcript or normalize_update(update)
    metadata = {
        "request_id": request_id,
        "update_id": update.update_id,
        **_message_metadata(message),
    }
    logger.info("webhook_received %s", json.dumps(metadata, separators=(",", ":"), sort_keys=True))

    content = normalized_text
    if normalized_text in {UNSUPPORTED_MESSAGE_PROMPT, FORWARDED_EMPTY_PROMPT}:
        content = f"[Unsupported] {normalized_text}"
    description = _todoist_description(update.update_id, message)
    photo_file_id = _extract_photo_file_id(message)
    if photo_file_id:
        try:
            image_url = get_telegram_file_url(
                photo_file_id,
                settings.telegram_bot_token.get_secret_value(),
            )
            description = _append_image_url(description, image_url)
        except Exception as exc:  # pragma: no cover - non-critical attachment
            logger.warning("telegram_file_fetch_failed", extra={"request_id": request_id, "error": str(exc)})

    try:
        parent_id = ensure_todo_later_task(
            settings.todo_later_task_name,
            settings.todoist_api_token.get_secret_value(),
        )
        try:
            cleanup_completed_subtasks(
                parent_id,
                settings.todoist_api_token.get_secret_value(),
                older_than_days=settings.todoist_cleanup_days,
            )
        except TodoistServiceError as exc:
            logger.warning("todoist_cleanup_failed", extra={"request_id": request_id, "error": exc.user_message})
        created = create_subtask(
            content,
            parent_id,
            settings.todoist_api_token.get_secret_value(),
            description=description,
        )
    except TodoistServiceError as exc:
        logger.warning("todoist_failed", extra={"request_id": request_id, "error": exc.user_message})
        _send_telegram_feedback(
            message,
            f"创建失败：{exc.user_message}",
            settings.telegram_bot_token.get_secret_value(),
            request_id,
        )
        return error_response(exc.user_message, status_code=502, meta={"request_id": request_id})
    except Exception as exc:  # pragma: no cover - safety net
        logger.error("todoist_unexpected", exc_info=exc, extra={"request_id": request_id})
        _send_telegram_feedback(
            message,
            "创建失败：Todoist unavailable",
            settings.telegram_bot_token.get_secret_value(),
            request_id,
        )
        return error_response("Todoist unavailable", status_code=500, meta={"request_id": request_id})

    task_url = created.get("url") if isinstance(created, dict) else None
    completion_text = "已创建 Todoist 任务。"
    if task_url:
        completion_text = f"已创建 Todoist 任务：{task_url}"
    _send_telegram_feedback(
        message,
        completion_text,
        settings.telegram_bot_token.get_secret_value(),
        request_id,
    )

    return success_response(
        WebhookAck(received=True, normalized_text=normalized_text).model_dump(),
        meta={"request_id": request_id},
    )


def _send_telegram_feedback(
    message: Optional[TelegramMessage],
    text: str,
    api_token: str,
    request_id: str,
) -> None:
    if not message or not message.chat:
        return
    try:
        send_telegram_message(message.chat.id, text, api_token)
    except Exception as exc:  # pragma: no cover - non-critical feedback
        logger.warning("telegram_feedback_failed", extra={"request_id": request_id, "error": str(exc)})

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
from app.models import TelegramMessage, TelegramUpdate, WebhookAck
from app.responses import error_response, success_response

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
    metadata = {
        "request_id": request_id,
        "update_id": update.update_id,
        **_message_metadata(message),
    }
    logger.info("webhook_received %s", json.dumps(metadata, separators=(",", ":"), sort_keys=True))

    return success_response(WebhookAck(received=True).model_dump(), meta={"request_id": request_id})

from __future__ import annotations

from typing import Optional

from app.models import TelegramEntity, TelegramMessage, TelegramUpdate

UNSUPPORTED_MESSAGE_PROMPT = "Unsupported message type. Please send text or a message with a caption."
IMAGE_ONLY_PROMPT = "Image from Telegram"
VOICE_ONLY_PROMPT = "Voice memo from Telegram"
FORWARDED_EMPTY_PROMPT = "Forwarded message has no text. Please add a note."


def normalize_update(update: TelegramUpdate) -> str:
    message = update.message or update.edited_message or update.channel_post or update.edited_channel_post
    if not message:
        return UNSUPPORTED_MESSAGE_PROMPT
    return normalize_message(message)


def normalize_message(message: TelegramMessage) -> str:
    text = _normalized_text(message.text, message.entities)
    if not text:
        text = _normalized_text(message.caption, message.caption_entities)
    if text:
        return text
    if message.photo:
        return IMAGE_ONLY_PROMPT
    if message.voice or message.audio:
        return VOICE_ONLY_PROMPT
    if _is_forwarded(message):
        return FORWARDED_EMPTY_PROMPT
    return UNSUPPORTED_MESSAGE_PROMPT


def _normalized_text(text: Optional[str], entities: Optional[list[TelegramEntity]]) -> str:
    if not text:
        return ""
    if not entities:
        return text.strip()
    return _apply_text_links(text, entities).strip()


def _apply_text_links(text: str, entities: list[TelegramEntity]) -> str:
    inserts: list[tuple[int, str]] = []
    for entity in entities:
        if entity.type == "text_link" and entity.url:
            inserts.append((entity.offset + entity.length, f" ({entity.url})"))

    if not inserts:
        return text

    inserts.sort(key=lambda item: item[0])
    result: list[str] = []
    cursor = 0
    for position, snippet in inserts:
        if position < cursor or position > len(text):
            continue
        result.append(text[cursor:position])
        result.append(snippet)
        cursor = position

    result.append(text[cursor:])
    return "".join(result)


def _is_forwarded(message: TelegramMessage) -> bool:
    return bool(
        message.forward_from
        or message.forward_from_chat
        or message.forward_sender_name
        or message.forward_origin
    )

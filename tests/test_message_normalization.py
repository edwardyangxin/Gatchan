import pytest

from app.models import TelegramUpdate
from app.telegram_normalizer import (
    IMAGE_ONLY_PROMPT,
    DOCUMENT_ONLY_PROMPT,
    VOICE_ONLY_PROMPT,
    FORWARDED_EMPTY_PROMPT,
    UNSUPPORTED_MESSAGE_PROMPT,
    normalize_update,
)


def test_normalize_text_message_preserves_plain_text() -> None:
    update = TelegramUpdate(
        update_id=1,
        message={
            "message_id": 100,
            "text": "hello world",
        },
    )

    assert normalize_update(update) == "hello world"


def test_normalize_caption_message_preserves_text_links() -> None:
    update = TelegramUpdate(
        update_id=2,
        message={
            "message_id": 101,
            "caption": "Read link",
            "caption_entities": [
                {
                    "type": "text_link",
                    "offset": 5,
                    "length": 4,
                    "url": "https://example.com",
                }
            ],
        },
    )

    assert normalize_update(update) == "Read link (https://example.com)"


def test_normalize_text_message_keeps_url_entities() -> None:
    update = TelegramUpdate(
        update_id=3,
        message={
            "message_id": 102,
            "text": "Visit https://example.com",
            "entities": [
                {
                    "type": "url",
                    "offset": 6,
                    "length": 19,
                }
            ],
        },
    )

    assert normalize_update(update) == "Visit https://example.com"


def test_normalize_forwarded_message_without_text_prompts() -> None:
    update = TelegramUpdate(
        update_id=4,
        message={
            "message_id": 103,
            "forward_sender_name": "Alice",
        },
    )

    assert normalize_update(update) == FORWARDED_EMPTY_PROMPT


def test_normalize_missing_message_prompts() -> None:
    update = TelegramUpdate(update_id=5)

    assert normalize_update(update) == UNSUPPORTED_MESSAGE_PROMPT


def test_normalize_photo_only_message_uses_image_prompt() -> None:
    update = TelegramUpdate(
        update_id=6,
        message={
            "message_id": 104,
            "photo": [
                {"file_id": "small", "width": 90, "height": 90},
                {"file_id": "large", "width": 320, "height": 320},
            ],
        },
    )

    assert normalize_update(update) == IMAGE_ONLY_PROMPT


def test_normalize_voice_only_message_uses_voice_prompt() -> None:
    update = TelegramUpdate(
        update_id=7,
        message={
            "message_id": 105,
            "voice": {"file_id": "voice-1", "duration": 2, "mime_type": "audio/ogg"},
        },
    )

    assert normalize_update(update) == VOICE_ONLY_PROMPT


def test_normalize_document_only_message_uses_document_prompt() -> None:
    update = TelegramUpdate(
        update_id=8,
        message={
            "message_id": 106,
            "document": {"file_id": "doc-1", "file_name": "note.pdf"},
        },
    )

    assert normalize_update(update) == DOCUMENT_ONLY_PROMPT

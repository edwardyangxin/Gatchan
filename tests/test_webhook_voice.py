from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.transcribe import TranscriptionError


def test_webhook_transcribes_voice_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get_file_url(file_id: str, api_token: str, *, client: Any = None) -> str:
        captured["file_id"] = file_id
        return "https://files.example.com/voice.ogg"

    def fake_download(file_url: str, *, client: Any = None) -> bytes:
        captured["file_url"] = file_url
        return b"audio-bytes"

    def fake_transcribe(*_: Any, **__: Any) -> str:
        return "hello from voice"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["content"] = content
        return {"id": "child-voice"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get_file_url)
    monkeypatch.setattr("app.main.download_telegram_file", fake_download)
    monkeypatch.setattr("app.main.transcribe_audio_with_gemini", fake_transcribe)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 31,
            "message": {
                "message_id": 200,
                "chat": {"id": 555, "type": "private"},
                "voice": {
                    "file_id": "voice-1",
                    "mime_type": "audio/ogg",
                    "duration": 3,
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["normalized_text"] == "hello from voice"
    assert captured["file_id"] == "voice-1"
    assert captured["content"] == "hello from voice"


def test_webhook_transcription_failure_sends_feedback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"create": 0}
    messages: list[str] = []

    def fake_get_file_url(file_id: str, api_token: str, *, client: Any = None) -> str:
        return "https://files.example.com/voice.ogg"

    def fake_download(file_url: str, *, client: Any = None) -> bytes:
        return b"audio-bytes"

    def fake_transcribe(*_: Any, **__: Any) -> str:
        raise TranscriptionError("transcribe failed")

    def fake_create(*_: Any, **__: Any) -> dict[str, Any]:
        calls["create"] += 1
        return {"id": "child-voice"}

    def fake_send(chat_id: int, text: str, api_token: str, *, client: Any = None) -> None:
        messages.append(text)

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get_file_url)
    monkeypatch.setattr("app.main.download_telegram_file", fake_download)
    monkeypatch.setattr("app.main.transcribe_audio_with_gemini", fake_transcribe)
    monkeypatch.setattr("app.main.create_subtask", fake_create)
    monkeypatch.setattr("app.main.send_telegram_message", fake_send)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 32,
            "message": {
                "message_id": 201,
                "chat": {"id": 555, "type": "private"},
                "voice": {
                    "file_id": "voice-2",
                    "mime_type": "audio/ogg",
                    "duration": 3,
                },
            },
        },
    )

    assert response.status_code == 200
    assert calls["create"] == 0
    assert messages


def test_webhook_voice_with_caption_skips_transcription(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"transcribe": 0}

    def fake_transcribe(*_: Any, **__: Any) -> str:
        calls["transcribe"] += 1
        return "ignored"

    monkeypatch.setattr("app.main.transcribe_audio_with_gemini", fake_transcribe)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 33,
            "message": {
                "message_id": 202,
                "chat": {"id": 555, "type": "private"},
                "caption": "use caption",
                "voice": {
                    "file_id": "voice-3",
                    "mime_type": "audio/ogg",
                    "duration": 3,
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["normalized_text"] == "use caption"
    assert calls["transcribe"] == 0

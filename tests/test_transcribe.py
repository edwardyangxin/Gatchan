import json

import httpx
import pytest

from app.transcribe import TranscriptionError, transcribe_audio_with_gemini


def test_transcribe_audio_with_gemini_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        )
        payload = json.loads(request.content.decode("utf-8"))
        parts = payload["contents"][0]["parts"]
        assert parts[0]["text"].startswith("Transcribe")
        assert "inline_data" in parts[1]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "hello world"}]}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    result = transcribe_audio_with_gemini(
        b"audio-bytes",
        "audio/ogg",
        "test-key",
        client=client,
    )

    assert result == "hello world"


def test_transcribe_audio_with_gemini_rejects_empty_audio() -> None:
    with pytest.raises(TranscriptionError):
        transcribe_audio_with_gemini(b"", "audio/ogg", "test-key")

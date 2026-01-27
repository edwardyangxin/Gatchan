from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Optional

import httpx

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


@dataclass(frozen=True)
class TranscriptionError(Exception):
    user_message: str

    def __str__(self) -> str:  # pragma: no cover - defaults to user_message
        return self.user_message


def transcribe_audio_with_gemini(
    audio_bytes: bytes,
    mime_type: str,
    api_key: str,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
    client: Optional[httpx.Client] = None,
) -> str:
    if not api_key:
        raise TranscriptionError("Gemini API key is required")
    if not audio_bytes:
        raise TranscriptionError("Audio payload is empty")
    if not mime_type:
        raise TranscriptionError("Audio mime type is required")

    encoded = base64.b64encode(audio_bytes).decode("utf-8")
    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"text": "Transcribe the speech in this audio. Respond with plain text only."},
                    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ]
    }

    close_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        close_client = True

    try:
        response = client.post(
            f"{GEMINI_API_BASE}/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise TranscriptionError("Gemini request failed") from exc
    except ValueError as exc:
        raise TranscriptionError("Gemini response invalid") from exc
    finally:
        if close_client:
            client.close()

    try:
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        content = candidates[0].get("content", {}) if candidates else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        transcript = "".join(text_parts).strip()
    except Exception as exc:  # pragma: no cover - defensive
        raise TranscriptionError("Gemini response invalid") from exc

    if not transcript:
        raise TranscriptionError("Gemini response empty")
    return transcript

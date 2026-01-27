from __future__ import annotations

from typing import Optional

import httpx


def get_telegram_file_url(
    file_id: str,
    api_token: str,
    *,
    client: Optional[httpx.Client] = None,
) -> str:
    if not api_token:
        raise ValueError("Telegram API token is required")
    if not file_id:
        raise ValueError("Telegram file id is required")

    url = f"https://api.telegram.org/bot{api_token}/getFile"

    close_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        close_client = True

    try:
        response = client.get(url, params={"file_id": file_id})
        response.raise_for_status()
        payload = response.json()
    finally:
        if close_client:
            client.close()

    if not isinstance(payload, dict):
        raise ValueError("Telegram response invalid")
    if not payload.get("ok"):
        raise ValueError("Telegram response invalid")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("Telegram response invalid")
    file_path = result.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("Telegram response invalid")
    return f"https://api.telegram.org/file/bot{api_token}/{file_path}"


def download_telegram_file(
    file_url: str,
    *,
    client: Optional[httpx.Client] = None,
) -> bytes:
    if not file_url:
        raise ValueError("Telegram file url is required")

    close_client = False
    if client is None:
        client = httpx.Client(timeout=20.0)
        close_client = True

    try:
        response = client.get(file_url)
        response.raise_for_status()
        return response.content
    finally:
        if close_client:
            client.close()


def send_telegram_message(
    chat_id: int,
    text: str,
    api_token: str,
    *,
    client: Optional[httpx.Client] = None,
) -> None:
    if not api_token:
        raise ValueError("Telegram API token is required")
    if not text or not text.strip():
        raise ValueError("Telegram message text is required")

    url = f"https://api.telegram.org/bot{api_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text.strip()}

    close_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        close_client = True

    try:
        response = client.post(url, json=payload)
        response.raise_for_status()
    finally:
        if close_client:
            client.close()

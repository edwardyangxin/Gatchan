from __future__ import annotations

from typing import Optional

import httpx


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

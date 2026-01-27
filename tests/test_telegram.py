import json

import httpx
import pytest

from app.telegram import send_telegram_message


def test_send_telegram_message_posts_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.telegram.org/bottest-token/sendMessage")
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"chat_id": 123, "text": "hello"}
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    send_telegram_message(123, "hello", "test-token", client=client)


def test_send_telegram_message_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        send_telegram_message(123, " ", "test-token")

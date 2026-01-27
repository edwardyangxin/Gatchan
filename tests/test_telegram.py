import json

import httpx
import pytest

from app.telegram import get_telegram_file_url, send_telegram_message


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


def test_get_telegram_file_url_builds_download_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.telegram.org/bottest-token/getFile?file_id=file-123")
        return httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/file-123.jpg"}})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    url = get_telegram_file_url("file-123", "test-token", client=client)

    assert url == "https://api.telegram.org/file/bottest-token/photos/file-123.jpg"


def test_get_telegram_file_url_rejects_missing_result() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with pytest.raises(ValueError):
        get_telegram_file_url("file-123", "test-token", client=client)

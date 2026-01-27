from fastapi.testclient import TestClient


def test_webhook_rejects_missing_secret(client: TestClient) -> None:
    response = client.post("/webhook", json={"update_id": 1})

    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Unauthorized"


def test_webhook_accepts_valid_secret(client: TestClient) -> None:
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 2,
            "message": {
                "message_id": 10,
                "date": 123,
                "chat": {"id": 99, "type": "private"},
                "from": {"id": 50, "is_bot": False},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["received"] is True
    assert "request_id" in payload["meta"]


def test_webhook_returns_normalized_text(client: TestClient) -> None:
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 3,
            "message": {
                "message_id": 11,
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
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["normalized_text"] == "Read link (https://example.com)"


def test_webhook_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={"message": {"message_id": 1}},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Invalid request payload"

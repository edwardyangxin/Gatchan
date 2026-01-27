from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

TODOIST_TASKS_URL = "https://api.todoist.com/rest/v2/tasks"


@dataclass(frozen=True)
class TodoistServiceError(Exception):
    user_message: str

    def __str__(self) -> str:  # pragma: no cover - defaults to user_message
        return self.user_message


def _validate_inputs(content: str, parent_id: str, api_token: str) -> None:
    if not content or not content.strip():
        raise TodoistServiceError("Message text is required")
    if not parent_id:
        raise TodoistServiceError("Todoist parent task id is required")
    if not api_token:
        raise TodoistServiceError("Todoist API token is required")


def create_subtask(
    content: str,
    parent_id: str,
    api_token: str,
    *,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    _validate_inputs(content, parent_id, api_token)

    payload = {"content": content.strip(), "parent_id": parent_id}
    headers = {"Authorization": f"Bearer {api_token}"}

    close_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        close_client = True

    try:
        response = client.post(TODOIST_TASKS_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise TodoistServiceError("Todoist request failed") from exc
    except ValueError as exc:
        raise TodoistServiceError("Todoist response invalid") from exc
    finally:
        if close_client:
            client.close()

    if not isinstance(data, dict) or "id" not in data:
        raise TodoistServiceError("Todoist response invalid")

    return data

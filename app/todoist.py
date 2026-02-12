from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx

TODOIST_TASKS_URL = "https://api.todoist.com/api/v1/tasks"
TODOIST_SYNC_URL = "https://api.todoist.com/sync/v9"
DEFAULT_TODO_LATER_DUE_STRING = "every day"
TODAY_DUE_STRING = "today"
CLEANUP_MAX_ITEMS = 50
TODOIST_TASK_CONTENT_MAX_CHARS = 500
CONTENT_TRUNCATION_SUFFIX = "..."


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


def _normalize_task_content(content: str) -> str:
    normalized = content.strip()
    if len(normalized) <= TODOIST_TASK_CONTENT_MAX_CHARS:
        return normalized
    max_prefix_length = TODOIST_TASK_CONTENT_MAX_CHARS - len(CONTENT_TRUNCATION_SUFFIX)
    if max_prefix_length <= 0:
        return normalized[:TODOIST_TASK_CONTENT_MAX_CHARS]
    return normalized[:max_prefix_length].rstrip() + CONTENT_TRUNCATION_SUFFIX


def _validate_task_name(task_name: str, api_token: str) -> None:
    if not task_name or not task_name.strip():
        raise TodoistServiceError("Todo later task name is required")
    if not api_token:
        raise TodoistServiceError("Todoist API token is required")


def _validate_parent_id(parent_id: str, api_token: str) -> None:
    if not parent_id:
        raise TodoistServiceError("Todoist parent task id is required")
    if not api_token:
        raise TodoistServiceError("Todoist API token is required")


def _request_json(response: httpx.Response, user_message: str) -> dict[str, Any] | list[dict[str, Any]]:
    try:
        data = response.json()
    except ValueError as exc:
        raise TodoistServiceError("Todoist response invalid") from exc
    if not isinstance(data, (dict, list)):
        raise TodoistServiceError("Todoist response invalid")
    return data


def _extract_tasks(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [task for task in payload if isinstance(task, dict)]
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return [task for task in results if isinstance(task, dict)]
    raise TodoistServiceError("Todoist response invalid")


def _is_due_today(due: dict[str, Any] | None) -> bool:
    if not due:
        return False
    if due_date := due.get("date"):
        try:
            return date.fromisoformat(due_date) == date.today()
        except ValueError:
            return False
    if due_datetime := due.get("datetime"):
        try:
            cleaned = due_datetime.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned).date() == date.today()
        except ValueError:
            return False
    return False


def _set_task_due_today(task_id: str, headers: dict[str, str], client: httpx.Client) -> None:
    response = client.post(
        f"{TODOIST_TASKS_URL}/{task_id}",
        json={"due_string": TODAY_DUE_STRING},
        headers=headers,
    )
    response.raise_for_status()


def _parse_completed_at(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def cleanup_completed_subtasks(
    parent_id: str,
    api_token: str,
    *,
    older_than_days: int = 7,
    max_delete: int = CLEANUP_MAX_ITEMS,
    client: Optional[httpx.Client] = None,
    now: Optional[datetime] = None,
) -> int:
    _validate_parent_id(parent_id, api_token)
    if older_than_days < 1:
        raise TodoistServiceError("Cleanup window must be at least 1 day")
    if max_delete < 1:
        return 0

    headers = {"Authorization": f"Bearer {api_token}"}
    close_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        close_client = True

    try:
        response = client.get(
            f"{TODOIST_SYNC_URL}/archive/items",
            params={"item_id": parent_id, "limit": max_delete},
            headers=headers,
        )
        response.raise_for_status()
        archive_items = _request_json(response, "Todoist response invalid")
        if not isinstance(archive_items, list):
            raise TodoistServiceError("Todoist response invalid")

        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=older_than_days)
        delete_ids: list[object] = []
        for item in archive_items:
            if not isinstance(item, dict):
                continue
            completed_at = _parse_completed_at(item.get("completed_at"))
            if not completed_at:
                continue
            if completed_at <= cutoff:
                item_id = item.get("id")
                if item_id is not None:
                    delete_ids.append(item_id)
            if len(delete_ids) >= max_delete:
                break

        if not delete_ids:
            return 0

        commands = [
            {
                "type": "item_delete",
                "uuid": str(item_id),
                "args": {"id": item_id},
            }
            for item_id in delete_ids
        ]
        sync_response = client.post(
            f"{TODOIST_SYNC_URL}/sync",
            json={"commands": commands},
            headers=headers,
        )
        sync_response.raise_for_status()
        _request_json(sync_response, "Todoist response invalid")
        return len(delete_ids)
    except httpx.HTTPError as exc:
        raise TodoistServiceError("Todoist request failed") from exc
    finally:
        if close_client:
            client.close()


def ensure_todo_later_task(
    task_name: str,
    api_token: str,
    *,
    client: Optional[httpx.Client] = None,
) -> str:
    _validate_task_name(task_name, api_token)

    headers = {"Authorization": f"Bearer {api_token}"}
    close_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        close_client = True

    try:
        response = client.get(TODOIST_TASKS_URL, headers=headers)
        response.raise_for_status()
        tasks_payload = _request_json(response, "Todoist response invalid")
        for task in _extract_tasks(tasks_payload):
            if task.get("content") == task_name:
                task_id = task.get("id")
                if task_id:
                    if not _is_due_today(task.get("due")):
                        _set_task_due_today(str(task_id), headers, client)
                    return str(task_id)

        payload = {"content": task_name.strip(), "due_string": DEFAULT_TODO_LATER_DUE_STRING}
        create_response = client.post(TODOIST_TASKS_URL, json=payload, headers=headers)
        create_response.raise_for_status()
        created = _request_json(create_response, "Todoist response invalid")
    except httpx.HTTPError as exc:
        raise TodoistServiceError("Todoist request failed") from exc
    finally:
        if close_client:
            client.close()

    if not isinstance(created, dict) or "id" not in created:
        raise TodoistServiceError("Todoist response invalid")

    return str(created["id"])


def create_subtask(
    content: str,
    parent_id: str,
    api_token: str,
    *,
    description: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    _validate_inputs(content, parent_id, api_token)

    payload: dict[str, Any] = {
        "content": _normalize_task_content(content),
        "parent_id": parent_id,
    }
    if description:
        payload["description"] = description.strip()
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

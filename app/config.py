from functools import lru_cache
from typing import Iterable

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: SecretStr
    telegram_webhook_secret: SecretStr
    todoist_api_token: SecretStr
    todo_later_task_name: str
    telegram_allowed_user_ids: set[int] = set()
    telegram_allowed_chat_ids: set[int] = set()
    telegram_whitelist_reply: bool = False
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("telegram_allowed_user_ids", "telegram_allowed_chat_ids", mode="before")
    @classmethod
    def _parse_id_set(cls, value: object) -> set[int]:
        if value is None or value == "":
            return set()
        if isinstance(value, set):
            return value
        if isinstance(value, int):
            return {value}
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            if not parts:
                return set()
            try:
                return {int(part) for part in parts}
            except ValueError as exc:
                raise ValueError("Whitelist IDs must be comma-separated integers") from exc
        if isinstance(value, Iterable):
            try:
                return {int(item) for item in value}
            except (TypeError, ValueError) as exc:
                raise ValueError("Whitelist IDs must be integers") from exc
        raise ValueError("Whitelist IDs must be comma-separated integers")


@lru_cache
def get_settings() -> Settings:
    return Settings()

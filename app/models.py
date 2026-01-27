from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")


class TelegramChat(BaseModel):
    id: int
    type: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TelegramEntity(BaseModel):
    type: str
    offset: int
    length: int
    url: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TelegramMessage(BaseModel):
    message_id: int
    date: Optional[int] = None
    chat: Optional[TelegramChat] = None
    from_user: Optional[TelegramUser] = Field(default=None, alias="from")
    text: Optional[str] = None
    caption: Optional[str] = None
    entities: Optional[list[TelegramEntity]] = None
    caption_entities: Optional[list[TelegramEntity]] = None
    forward_from: Optional[TelegramUser] = None
    forward_from_chat: Optional[TelegramChat] = None
    forward_sender_name: Optional[str] = None
    forward_origin: Optional[dict] = None

    model_config = ConfigDict(extra="ignore")


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
    channel_post: Optional[TelegramMessage] = None
    edited_channel_post: Optional[TelegramMessage] = None

    model_config = ConfigDict(extra="ignore")


class WebhookAck(BaseModel):
    received: bool = True
    normalized_text: Optional[str] = None

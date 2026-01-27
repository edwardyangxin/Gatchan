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


class TelegramPhotoSize(BaseModel):
    file_id: str
    file_unique_id: Optional[str] = None
    width: int
    height: int
    file_size: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class TelegramVoice(BaseModel):
    file_id: str
    file_unique_id: Optional[str] = None
    duration: Optional[int] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class TelegramAudio(BaseModel):
    file_id: str
    file_unique_id: Optional[str] = None
    duration: Optional[int] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    file_name: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TelegramMessage(BaseModel):
    message_id: int
    date: Optional[int] = None
    chat: Optional[TelegramChat] = None
    from_user: Optional[TelegramUser] = Field(default=None, alias="from")
    text: Optional[str] = None
    caption: Optional[str] = None
    photo: Optional[list[TelegramPhotoSize]] = None
    voice: Optional["TelegramVoice"] = None
    audio: Optional["TelegramAudio"] = None
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

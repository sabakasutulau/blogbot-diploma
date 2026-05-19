from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PostBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10)


class PostCreate(PostBase):
    author_telegram_id: Optional[int] = None
    author_name: Optional[str] = None
    status: str = "draft"


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    body: Optional[str] = Field(default=None, min_length=10)
    status: Optional[str] = None


class PostRead(PostBase):
    id: int
    slug: str
    status: str
    author_telegram_id: Optional[int]
    author_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    telegram_channel_id: Optional[str] = None
    telegram_message_id: Optional[int] = None
    telegram_message_url: Optional[str] = None
    published_to_channel_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StatsRead(BaseModel):
    total: int
    published: int
    drafts: int

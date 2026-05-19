from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(240), unique=True, index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    author_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Telegram channel publication fields
    telegram_channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    telegram_message_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    published_to_channel_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

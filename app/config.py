from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BlogBot Diploma"
    database_url: str = "sqlite:///./blogbot.db"
    admin_token: str = "change-me"
    bot_token: str = ""
    public_base_url: str = "http://127.0.0.1:8000"
    telegram_channel_id: str = ""
    # Comma-separated Telegram user IDs allowed to manage the bot.
    # Example: BOT_OWNER_IDS=123456789,987654321
    bot_owner_ids: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def owner_ids(self) -> List[int]:
        """Parse BOT_OWNER_IDS into a list of integers."""
        raw = self.bot_owner_ids.strip()
        if not raw:
            return []
        result = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                result.append(int(part))
        return result

    @property
    def has_channel(self) -> bool:
        """True when TELEGRAM_CHANNEL_ID is configured."""
        return bool(self.telegram_channel_id.strip())

    @property
    def has_site(self) -> bool:
        """True when PUBLIC_BASE_URL is set to something other than the default dev URL."""
        return bool(self.public_base_url.strip())


settings = Settings()

"""
Точка входа для запуска Telegram-бота.

Запуск:
    python -m app.bot_runner

Убедитесь что в .env задан BOT_TOKEN.
"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

from app.bot import run_bot


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError as exc:
        # BOT_TOKEN is empty or other config error
        logging.error(str(exc))
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user (KeyboardInterrupt).")

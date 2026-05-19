import sys
from pathlib import Path

# Ensure project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import crud
from app.db import SessionLocal, init_db
from app.schemas import PostCreate

SAMPLE_POSTS = [
    {
        "title": "Первый демонстрационный пост",
        "body": "Это тестовая публикация для проверки публичной ленты блога.",
        "status": "published",
        "author_name": "Администратор",
    },
    {
        "title": "Черновик из Telegram",
        "body": "Эта запись показывает, как в системе хранится материал до публикации.",
        "status": "draft",
        "author_name": "Telegram user",
    },
]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        for item in SAMPLE_POSTS:
            crud.create_post(db, PostCreate(**item))
    print("Demo posts created")


if __name__ == "__main__":
    main()

# Дипломный проект: Telegram-бот для создания и ведения блогов

Практическая часть дипломного проекта по теме **«Разработка Telegram-бота для создания и ведения блогов»**.

Проект сделан как небольшая автоматизированная система для автора блога: пользователь создает публикации через Telegram-бота, администратор может управлять материалами через веб-панель, опубликованные записи отображаются в публичной веб-ленте.

## Состав системы

1. Telegram-бот для создания черновиков, просмотра черновиков и публикации материалов.
2. Backend на FastAPI с REST API.
3. Веб-интерфейс публичного блога на Jinja2, HTML, CSS и JavaScript.
4. Панель администратора для создания, публикации и удаления постов.
5. База данных через SQLAlchemy: SQLite для локальной демонстрации, PostgreSQL для дипломного запуска.
6. API-тесты на pytest.
7. Postman-коллекция для демонстрации запросов.
8. Документация, подготовленная под разделы дипломного проекта: требования, сценарии, архитектура, тестирование, внедрение, экономический расчет.

## Технологический стек

- Python 3.11+
- FastAPI
- SQLAlchemy
- Jinja2
- Aiogram 3
- PostgreSQL / SQLite
- Pytest
- Uvicorn
- HTML, CSS, JavaScript
- Postman

## Быстрый запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

После запуска:

- публичный блог: http://127.0.0.1:8000/
- панель администратора: http://127.0.0.1:8000/admin
- API-документация: http://127.0.0.1:8000/docs
- проверка состояния API: http://127.0.0.1:8000/api/health

Токен администратора задается в `.env` как `ADMIN_TOKEN`. Для демонстрации можно оставить значение из `.env.example`, но в реальной эксплуатации его нужно заменить.

## Запуск с PostgreSQL

```bash
docker compose up -d db
cp .env.example .env
# В .env поставить DATABASE_URL=postgresql+psycopg://blogbot:blogbot@localhost:5432/blogbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Запуск Telegram-бота

1. Создать бота через BotFather.
2. Вставить токен в `.env`:

```env
BOT_TOKEN=<token_from_BotFather>
```

3. Запустить бота отдельным процессом:

```bash
python -m app.bot_runner
```

## Тесты

```bash
pytest
```

Если зависимости не установлены, сначала выполнить:

```bash
pip install -r requirements.txt
```

## Что показывать на защите

1. Репозиторий проекта.
2. Запущенный сайт с публичной лентой постов.
3. Панель администратора.
4. API-документацию FastAPI.
5. Postman-запросы из `postman_collection.json`.
6. Тесты `pytest`.
7. Демонстрацию Telegram-бота или заранее записанное видео, если Telegram/инфраструктура не работает на месте.

## Документация в проекте

Папка `docs/` содержит материалы, которые потом можно перенести в пояснительную записку и приложения:

- `PROJECT_COMPLIANCE_CHECKLIST.md` - соответствие проекта требованиям методички.
- `TECHNICAL_REQUIREMENTS.md` - технические требования к программному продукту.
- `USER_SCENARIOS.md` - пользовательские сценарии.
- `TECHNOLOGY_CHOICE.md` - выбор и обоснование технологий.
- `ARCHITECTURE.md` - архитектура системы и схемы взаимодействия.
- `TEST_PLAN.md` - план тестирования.
- `DEPLOYMENT_GUIDE.md` - установка и внедрение.
- `ECONOMIC_CALCULATION_DRAFT.md` - черновик расчета технико-экономических показателей.
- `SOURCE_FILES.md` - перечень исходных файлов проекта.

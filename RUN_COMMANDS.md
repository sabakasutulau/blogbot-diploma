# RUN COMMANDS — BlogBot Diploma

Краткая инструкция для запуска проекта на Windows (PowerShell).

---

## 1. Установка окружения

```powershell
# Перейти в папку проекта
cd путь\до\blogbot-diploma

# Создать виртуальное окружение
python -m venv .venv

# Активировать окружение
.\.venv\Scripts\Activate.ps1

# Если PowerShell блокирует активацию — выполнить один раз:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Затем повторить активацию выше
```

---

## 2. Установка зависимостей

```powershell
# Обновить pip
python -m pip install --upgrade pip

# Установить все пакеты
pip install -r requirements.txt

# Проверить установку
python -c "import fastapi, uvicorn, sqlalchemy, jinja2, aiogram, pytest, httpx; print('OK')"
```

---

## 3. Настройка переменных окружения

```powershell
# Создать .env (если ещё не создан)
Copy-Item .env.example .env

# Проверить настройки
python scripts/check_environment.py
```

В `.env` заполните нужные переменные:

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота из BotFather |
| `TELEGRAM_CHANNEL_ID` | Username канала, например `@mychannel` |
| `ADMIN_TOKEN` | Токен для API-администрирования |
| `PUBLIC_BASE_URL` | Публичный URL сайта |

> Токены не публикуются в репозитории. Файл `.env` добавлен в `.gitignore`.

---

## 4. Наполнение базы данных тестовыми данными

```powershell
python scripts/seed.py
```

> **Важно:** если модель БД изменилась, можно удалить `blogbot.db` и пересоздать:
> ```powershell
> Remove-Item blogbot.db -ErrorAction SilentlyContinue
> python scripts/seed.py
> ```

---

## 5. Запуск веб-сайта

```powershell
# Запуск с автоперезагрузкой (для разработки)
python -m uvicorn app.main:app --reload

# Или на конкретном хосте/порту
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Открыть в браузере:
| Адрес | Описание |
|-------|----------|
| http://127.0.0.1:8000/ | Публичная лента блога |
| http://127.0.0.1:8000/admin | Административная панель |
| http://127.0.0.1:8000/docs | Swagger API документация |
| http://127.0.0.1:8000/api/health | Проверка работоспособности API |
| http://127.0.0.1:8000/post/id/{id} | Пост по числовому ID |

---

## 6. Запуск тестов

```powershell
pytest -v
```

Ожидаемый результат: **12 passed**

---

## 7. Запуск Telegram-бота

> ⚠️ Предварительно необходимо вставить `BOT_TOKEN` в `.env`

```powershell
# В отдельном окне PowerShell (с активированным .venv)
.\.venv\Scripts\Activate.ps1
python -m app.bot_runner
```

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список команд |
| `/help` | Справка |
| `/newpost` | Создать новый пост (пошагово) |
| `/drafts` | Посмотреть мои черновики |
| `/posts` | Посмотреть мои опубликованные записи |
| `/cancel` | Отменить текущую операцию |

### Кнопки предпросмотра публикации

| Кнопка | Действие |
|--------|----------|
| 🌐 Опубликовать на сайте | Переводит в status=published, даёт ссылку |
| 📢 Опубликовать в канале | Публикует на сайте и отправляет в Telegram-канал |
| 🚀 Опубликовать везде | Публикует на сайте и в Telegram-канале |
| ✏️ Редактировать заголовок | Запрашивает новый заголовок |
| 📝 Редактировать текст | Запрашивает новый текст |
| 💾 Оставить черновиком | Сохраняет черновик без публикации |
| 🗑 Удалить | Мягкое удаление (status=deleted) |

---

## 8. Подключение Telegram-канала

1. Создать канал в Telegram.
2. Добавить бота администратором канала.
3. Выдать боту право публиковать сообщения.
4. В `.env` добавить:
   ```
   TELEGRAM_CHANNEL_ID=@username_канала
   ```
5. Запустить сайт:
   ```powershell
   python -m uvicorn app.main:app --reload
   ```
6. Во втором терминале запустить бота:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m app.bot_runner
   ```

> Если `TELEGRAM_CHANNEL_ID` не задан, бот работает без падения — просто без публикации в канал.

---

## 9. Проверка Telegram-сценария

1. Написать боту `/start`.
2. Написать `/newpost`.
3. Ввести заголовок.
4. Ввести текст.
5. Проверить предпросмотр (7 кнопок).
6. Нажать «Опубликовать на сайте».
7. Открыть ссылку.
8. Проверить пост на сайте (http://127.0.0.1:8000/).
9. Создать второй пост.
10. Нажать «Опубликовать везде».
11. Проверить сайт.
12. Проверить Telegram-канал.
13. Проверить `/drafts`.
14. Проверить `/posts`.
15. Проверить удаление.

---

## 10. Запуск PostgreSQL через Docker (опционально)

> Требуется установленный [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```powershell
# Запустить базу данных в контейнере
docker compose up -d db

# В .env изменить строку подключения:
# DATABASE_URL=postgresql+psycopg://blogbot:blogbot@localhost:5432/blogbot
```

> Если Docker не установлен — проект работает на SQLite без дополнительных программ.

---

## Быстрый старт (всё вместе)

```powershell
# Первый запуск
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# → Вставить BOT_TOKEN и TELEGRAM_CHANNEL_ID в .env

python scripts/seed.py

# Терминал 1 — веб-сайт
python -m uvicorn app.main:app --reload

# Терминал 2 — Telegram-бот
.\.venv\Scripts\Activate.ps1
python -m app.bot_runner
```

Открыть в браузере: **http://127.0.0.1:8000/**

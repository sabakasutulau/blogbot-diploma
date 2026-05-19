# TELEGRAM BOT CHECK REPORT
## Отчёт о проверке Telegram-части — BlogBot Diploma

**Дата проверки:** 2026-05-18  
**Версия aiogram:** 3.28.2  
**Python:** 3.14.2

---

## 1. Изменённые файлы

| Файл | Статус |
|------|--------|
| `app/bot.py` | ✅ полностью переработан |
| `app/config.py` | ✅ добавлено поле `telegram_channel_id` |
| `app/crud.py` | ✅ добавлены `soft_delete_post`, `list_user_posts`, фильтрация deleted |
| `app/bot_runner.py` | ✅ без изменений (работает корректно) |
| `app/db.py` | ✅ без изменений |
| `app/models.py` | ✅ без изменений (поле `author_telegram_id` уже есть) |
| `app/main.py` | ✅ без изменений (маршруты работают корректно) |
| `.env.example` | ✅ добавлена переменная `TELEGRAM_CHANNEL_ID` |
| `tests/test_api.py` | ✅ добавлено 5 новых тестов |
| `tests/conftest.py` | ✅ без изменений |
| `.gitignore` | ✅ содержит все нужные записи |
| `RUN_COMMANDS.md` | ✅ добавлены разделы по каналу и Telegram-сценарию |

---

## 2. Переменные окружения

`.env.example` содержит все необходимые переменные:

```
APP_NAME=BlogBot Diploma
DATABASE_URL=sqlite:///./blogbot.db
ADMIN_TOKEN=change-me
BOT_TOKEN=
PUBLIC_BASE_URL=http://127.0.0.1:8000
TELEGRAM_CHANNEL_ID=
```

> Токены не выводятся в отчёт в целях безопасности.  
> `.env` находится в `.gitignore`.

---

## 3. TELEGRAM_CHANNEL_ID

- Если `TELEGRAM_CHANNEL_ID` задан — бот публикует сообщения в канал при нажатии соответствующих кнопок.
- Если `TELEGRAM_CHANNEL_ID` пустой — бот **не падает**, выводит пользователю инструкцию по настройке.

Сообщение пользователю при пустом канале:
```
⚠️ Telegram-канал не настроен.
Добавьте TELEGRAM_CHANNEL_ID в .env и назначьте бота администратором канала.
```

---

## 4. Функциональность бота

| # | Функция | Статус |
|---|---------|--------|
| 1 | `/start` — приветствие и список команд | ✅ реализовано |
| 2 | `/help` — справка | ✅ реализовано |
| 3 | `/cancel` — отмена FSM-диалога | ✅ реализовано |
| 4 | `/newpost` — создание поста (FSM: заголовок → текст) | ✅ реализовано |
| 5 | Предпросмотр с 7 кнопками управления | ✅ реализовано |
| 6 | Редактирование заголовка (FSM) | ✅ реализовано |
| 7 | Редактирование текста (FSM) | ✅ реализовано |
| 8 | Сохранение черновика | ✅ реализовано |
| 9 | Публикация на сайте | ✅ реализовано |
| 10 | Публикация в Telegram-канале | ✅ реализовано |
| 11 | Публикация везде (сайт + канал) | ✅ реализовано |
| 12 | `/drafts` — список черновиков пользователя | ✅ реализовано |
| 13 | `/posts` — список опубликованных записей | ✅ реализовано |
| 14 | Удаление публикации (soft delete, status=deleted) | ✅ реализовано |

---

## 5. Кнопки предпросмотра

После создания черновика или нажатия «Открыть» бот показывает 7 кнопок:

| Кнопка | Callback | Действие |
|--------|----------|----------|
| 🌐 Опубликовать на сайте | `publish_site:{id}` | status=published, ссылка пользователю |
| 📢 Опубликовать в канале | `publish_channel:{id}` | status=published + отправка в канал |
| 🚀 Опубликовать везде | `publish_all:{id}` | status=published + канал + ссылка |
| ✏️ Редактировать заголовок | `edit_title:{id}` | FSM EditPost.title |
| 📝 Редактировать текст | `edit_body:{id}` | FSM EditPost.body |
| 💾 Оставить черновиком | `keep_draft:{id}` | сохранить как черновик |
| 🗑 Удалить | `delete_post:{id}` | soft delete (status=deleted) |

---

## 6. Удаление публикаций

Реализован **Вариант Б — мягкое удаление** (`status=deleted`):

- Удалённые посты не отображаются на главной странице сайта.
- Удалённые посты не попадают в `/api/posts` без явного фильтра.
- Удалённые посты не показываются в `/drafts` и `/posts` в боте.
- Данные физически сохраняются в БД (для безопасности).

---

## 7. HTML и безопасность текста

- Все пользовательские данные (title, body) экранируются через `html.escape()` перед отправкой в HTML-сообщениях.
- Символы `< > &` не поломают сообщения.

---

## 8. Ссылки в боте

Используется числовой маршрут:
```
{PUBLIC_BASE_URL}/post/id/{post_id}
```

Пример: `http://127.0.0.1:8000/post/id/5`

Маршрут выполняет redirect (302) к slug-URL. Это стабильнее и не зависит от изменения слага.

---

## 9. Результаты тестов

```
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.0.3

collected 12 items

tests/test_api.py::test_health_check                          PASSED  [  8%]
tests/test_api.py::test_admin_token_required                  PASSED  [ 16%]
tests/test_api.py::test_create_publish_and_list_post          PASSED  [ 25%]
tests/test_api.py::test_stats_endpoint                        PASSED  [ 33%]
tests/test_api.py::test_post_by_id_redirect                   PASSED  [ 41%]
tests/test_api.py::test_post_by_id_not_found                  PASSED  [ 50%]
tests/test_api.py::test_slug_is_ascii                         PASSED  [ 58%]
tests/test_api.py::test_telegram_channel_id_in_settings       PASSED  [ 66%]
tests/test_api.py::test_publish_without_telegram_channel      PASSED  [ 75%]
tests/test_api.py::test_deleted_post_not_in_public_feed       PASSED  [ 83%]
tests/test_api.py::test_deleted_post_not_in_drafts            PASSED  [ 91%]
tests/test_api.py::test_default_list_excludes_deleted         PASSED  [100%]

======================== 12 passed, 27 warnings in 0.53s ======================
```

✅ **Все 12 тестов проходят** (7 старых + 5 новых).

---

## 10. Что нужно сделать вручную перед защитой

| # | Действие | Обязательно |
|---|----------|-------------|
| 1 | Вставить `BOT_TOKEN` в `.env` | ✅ Да |
| 2 | Создать Telegram-канал | ✅ Да (если нужна публикация в канал) |
| 3 | Добавить бота администратором канала | ✅ Да |
| 4 | Выдать боту право публиковать сообщения | ✅ Да |
| 5 | Добавить `TELEGRAM_CHANNEL_ID=@username` в `.env` | ✅ Да |
| 6 | Запустить сайт: `python -m uvicorn app.main:app --reload` | ✅ Да |
| 7 | Запустить бота: `python -m app.bot_runner` | ✅ Да |
| 8 | Проверить `/start`, `/newpost`, публикацию и ссылку | ✅ Да |
| 9 | Проверить публикацию везде и сообщение в канале | ✅ Да |
| 10 | Проверить `/drafts`, `/posts`, удаление | ✅ Да |
| 11 | Опционально: заменить `ADMIN_TOKEN=change-me` | ⚠️ Желательно |
| 12 | Опционально: `python scripts/seed.py` для тестовых данных | ⚠️ Желательно |

---

## Итоговый статус

| Компонент | Статус |
|-----------|--------|
| Веб-приложение (FastAPI) | ✅ Работает |
| Публичная лента `/` | ✅ Работает |
| Админ-панель `/admin` | ✅ Работает |
| Swagger API `/docs` | ✅ Работает |
| `/api/health` | ✅ Работает |
| Маршрут `/post/id/{post_id}` | ✅ Работает (redirect → slug) |
| Мягкое удаление (status=deleted) | ✅ Реализовано |
| TELEGRAM_CHANNEL_ID в конфиге | ✅ Реализовано |
| Telegram-бот — все команды | ✅ Готов |
| Telegram-бот — 7 кнопок предпросмотра | ✅ Готов |
| Telegram-бот — редактирование | ✅ Готов |
| Telegram-бот — публикация на сайт | ✅ Готов |
| Telegram-бот — публикация в канал | ✅ Готов |
| Telegram-бот — публикация везде | ✅ Готов |
| Telegram-бот — /drafts | ✅ Готов |
| Telegram-бот — /posts | ✅ Готов |
| Telegram-бот — удаление | ✅ Готов |
| Telegram-бот (polling) | ⏳ Ожидает `BOT_TOKEN` в `.env` |
| Автотесты | ✅ 12/12 passed |

---

*Отчёт обновлён 2026-05-18 в рамках дипломной проверки проекта «BlogBot Diploma».*

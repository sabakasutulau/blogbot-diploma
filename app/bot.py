"""
Telegram-бот BlogBot — Telegram-first режим.

Команды: /start /help /newpost /drafts /posts /stats /settings /cancel
"""
import html
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import crud
from app.config import settings
from app.db import SessionLocal, init_db
from app.schemas import PostCreate

logger = logging.getLogger(__name__)
router = Router()


# ── Проверка владельца ────────────────────────────────────────────────────────

def _is_owner(user_id: int) -> bool:
    ids = settings.owner_ids
    if not ids:
        return True  # dev mode: no restriction
    return user_id in ids


async def _deny(message: Message) -> None:
    await message.answer("⛔ У вас нет прав для управления этим ботом.")


# ── Тексты ────────────────────────────────────────────────────────────────────

def _welcome_text() -> str:
    channel = settings.telegram_channel_id.strip() or "не настроен"
    return (
        "👋 Добро пожаловать в <b>BlogBot</b>!\n\n"
        f"📢 Канал публикации: <code>{html.escape(channel)}</code>\n\n"
        "Доступные команды:\n"
        "/newpost — создать публикацию\n"
        "/drafts  — мои черновики\n"
        "/posts   — мои опубликованные записи\n"
        "/stats   — статистика\n"
        "/settings — настройки бота\n"
        "/help    — справка\n"
        "/cancel  — отменить текущее действие"
    )


def _help_text() -> str:
    return (
        "<b>BlogBot — справка</b>\n\n"
        "1. /newpost — ввести заголовок и текст\n"
        "2. Кнопки управления публикацией:\n"
        "   • 📢 Опубликовать в канал — главный способ\n"
        "   • 🌐 Опубликовать на сайт\n"
        "   • 🚀 Везде (канал + сайт)\n"
        "   • ✏️ Редактировать заголовок\n"
        "   • 📝 Редактировать текст\n"
        "   • 💾 Оставить черновиком\n"
        "   • 🗑 Удалить\n\n"
        "/drafts — черновики\n"
        "/posts  — опубликованные\n"
        "/stats  — статистика публикаций"
    )


# ── FSM-состояния ─────────────────────────────────────────────────────────────

class NewPost(StatesGroup):
    title = State()
    body = State()


class EditPost(StatesGroup):
    title = State()
    body = State()


# ── Клавиатуры ────────────────────────────────────────────────────────────────

def _preview_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликовать в канал", callback_data=f"pub_ch:{post_id}")],
        [InlineKeyboardButton(text="🌐 На сайт", callback_data=f"pub_site:{post_id}"),
         InlineKeyboardButton(text="🚀 Везде", callback_data=f"pub_all:{post_id}")],
        [InlineKeyboardButton(text="✏️ Заголовок", callback_data=f"edit_title:{post_id}"),
         InlineKeyboardButton(text="📝 Текст", callback_data=f"edit_body:{post_id}")],
        [InlineKeyboardButton(text="💾 Черновик", callback_data=f"keep_draft:{post_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_post:{post_id}")],
    ])


def _drafts_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Открыть", callback_data=f"open:{post_id}"),
         InlineKeyboardButton(text="📢 В канал", callback_data=f"pub_ch:{post_id}")],
        [InlineKeyboardButton(text="🚀 Везде", callback_data=f"pub_all:{post_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_post:{post_id}")],
    ])


def _posts_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Открыть", callback_data=f"open:{post_id}"),
         InlineKeyboardButton(text="📢 В канал", callback_data=f"pub_ch:{post_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_post:{post_id}")],
    ])


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _preview_text(post_id: int, title: str, body: str, status: str,
                  msg_url: str | None = None) -> str:
    st = {"draft": "черновик", "published": "опубликован", "deleted": "удалён"}.get(status, status)
    t = html.escape(title)
    b = html.escape(body[:500]) + ("..." if len(body) > 500 else "")
    lines = [
        "<b>📋 Предпросмотр публикации</b>\n",
        f"<b>Заголовок:</b> {t}",
        f"<b>Текст:</b>\n{b}",
        f"<b>Статус:</b> {st}",
    ]
    if status == "published":
        if settings.has_site:
            lines.append(f"<b>Сайт:</b> {settings.public_base_url}/post/id/{post_id}")
        if msg_url:
            lines.append(f"<b>Канал:</b> {msg_url}")
    lines.append("\nЧто сделать с публикацией?")
    return "\n".join(lines)


def _channel_post_text(title: str, body: str, post_id: int) -> str:
    """Формат сообщения для Telegram-канала."""
    t = html.escape(title)
    b = html.escape(body)
    text = f"<b>{t}</b>\n\n{b}"
    if settings.has_site:
        url = f"{settings.public_base_url}/post/id/{post_id}"
        text += f"\n\nЧитать на сайте:\n{url}"
    return text


async def _send_to_channel(bot: Bot, post_id: int, title: str, body: str) -> tuple[bool, int | None]:
    """Отправить пост в канал. Возвращает (ok, message_id)."""
    channel = settings.telegram_channel_id.strip()
    if not channel:
        return False, None
    try:
        msg = await bot.send_message(
            chat_id=channel,
            text=_channel_post_text(title, body, post_id),
            parse_mode="HTML",
        )
        return True, msg.message_id
    except Exception as exc:
        logger.error("Channel send error: %s", exc)
        return False, None


# ── Команды ───────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(_welcome_text(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_help_text(), parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("❌ Операция отменена.")


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _is_owner(user_id):
        await _deny(message)
        return
    channel = settings.telegram_channel_id.strip() or "не настроен"
    owner_ids = settings.owner_ids
    owners_str = ", ".join(str(i) for i in owner_ids) if owner_ids else "не задан (режим разработки)"
    await message.answer(
        "<b>⚙️ Настройки бота</b>\n\n"
        f"<b>Канал:</b> <code>{html.escape(channel)}</code>\n"
        f"<b>Владельцы:</b> <code>{html.escape(owners_str)}</code>\n"
        f"<b>Сайт:</b> <code>{html.escape(settings.public_base_url)}</code>\n"
        f"<b>База данных:</b> <code>{html.escape(settings.database_url)}</code>",
        parse_mode="HTML",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _is_owner(user_id):
        await _deny(message)
        return
    with SessionLocal() as db:
        s = crud.stats(db)
    await message.answer(
        "<b>📊 Статистика BlogBot</b>\n\n"
        f"📝 Всего постов: <b>{s['total']}</b>\n"
        f"✅ Опубликовано: <b>{s['published']}</b>\n"
        f"📋 Черновиков: <b>{s['drafts']}</b>\n"
        f"📢 В Telegram-канале: <b>{s['in_channel']}</b>",
        parse_mode="HTML",
    )


@router.message(Command("newpost"))
async def cmd_newpost(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _is_owner(user_id):
        await _deny(message)
        return
    await state.set_state(NewPost.title)
    await message.answer(
        "📝 <b>Создание нового поста</b>\n\nВведите заголовок (минимум 3 символа).\nДля отмены — /cancel",
        parse_mode="HTML",
    )


@router.message(Command("drafts"))
async def cmd_drafts(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _is_owner(user_id):
        await _deny(message)
        return
    with SessionLocal() as db:
        posts = crud.list_user_posts(db, user_id, "draft")
    if not posts:
        await message.answer("Черновиков пока нет.")
        return
    await message.answer(f"📋 <b>Ваши черновики ({len(posts)}):</b>", parse_mode="HTML")
    for p in posts[:10]:
        preview = html.escape(p.body[:200]) + ("..." if len(p.body) > 200 else "")
        await message.answer(
            f"<b>#{p.id}: {html.escape(p.title)}</b>\n{preview}",
            reply_markup=_drafts_kb(p.id),
            parse_mode="HTML",
        )


@router.message(Command("posts"))
async def cmd_posts(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not _is_owner(user_id):
        await _deny(message)
        return
    with SessionLocal() as db:
        posts = crud.list_user_posts(db, user_id, "published")
    if not posts:
        await message.answer("Опубликованных записей пока нет.")
        return
    await message.answer(f"📰 <b>Ваши публикации ({len(posts)}):</b>", parse_mode="HTML")
    for p in posts[:10]:
        links = []
        if settings.has_site:
            links.append(f'🌐 <a href="{settings.public_base_url}/post/id/{p.id}">Сайт</a>')
        if p.telegram_message_url:
            links.append(f'📢 <a href="{p.telegram_message_url}">Канал</a>')
        link_line = "  ".join(links) if links else ""
        await message.answer(
            f"<b>#{p.id}: {html.escape(p.title)}</b>\n{link_line}",
            reply_markup=_posts_kb(p.id),
            parse_mode="HTML",
        )


# ── FSM: /newpost ─────────────────────────────────────────────────────────────

@router.message(NewPost.title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("⚠️ Заголовок должен быть не короче 3 символов.")
        return
    await state.update_data(title=text)
    await state.set_state(NewPost.body)
    await message.answer(
        "Теперь введите <b>текст поста</b> (минимум 10 символов).\nДля отмены — /cancel",
        parse_mode="HTML",
    )


@router.message(NewPost.body)
async def fsm_body(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 10:
        await message.answer("⚠️ Текст поста должен быть не короче 10 символов.")
        return
    data = await state.get_data()
    user = message.from_user
    with SessionLocal() as db:
        post = crud.create_post(db, PostCreate(
            title=data["title"], body=text, status="draft",
            author_telegram_id=user.id if user else None,
            author_name=user.full_name if user else None,
        ))
        post_id, post_title, post_body, post_status = post.id, post.title, post.body, post.status
    await state.clear()
    await message.answer(
        _preview_text(post_id, post_title, post_body, post_status),
        reply_markup=_preview_kb(post_id),
        parse_mode="HTML",
    )


# ── FSM: редактирование ───────────────────────────────────────────────────────

@router.message(EditPost.title)
async def fsm_edit_title(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("⚠️ Заголовок должен быть не короче 3 символов.")
        return
    data = await state.get_data()
    post_id = data["post_id"]
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await state.clear()
            await message.answer("❌ Публикация не найдена.")
            return
        post.title = text
        db.commit()
        db.refresh(post)
        pt, pb, ps, mu = post.title, post.body, post.status, post.telegram_message_url
    await state.clear()
    await message.answer(
        "✅ Заголовок обновлён!\n\n" + _preview_text(post_id, pt, pb, ps, mu),
        reply_markup=_preview_kb(post_id), parse_mode="HTML",
    )


@router.message(EditPost.body)
async def fsm_edit_body(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 10:
        await message.answer("⚠️ Текст поста должен быть не короче 10 символов.")
        return
    data = await state.get_data()
    post_id = data["post_id"]
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await state.clear()
            await message.answer("❌ Публикация не найдена.")
            return
        post.body = text
        db.commit()
        db.refresh(post)
        pt, pb, ps, mu = post.title, post.body, post.status, post.telegram_message_url
    await state.clear()
    await message.answer(
        "✅ Текст обновлён!\n\n" + _preview_text(post_id, pt, pb, ps, mu),
        reply_markup=_preview_kb(post_id), parse_mode="HTML",
    )


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("open:"))
async def cb_open(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        pt, pb, ps, mu = post.title, post.body, post.status, post.telegram_message_url
    await callback.message.answer(
        _preview_text(post_id, pt, pb, ps, mu),
        reply_markup=_preview_kb(post_id), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pub_site:"))
async def cb_pub_site(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        if post.status == "published":
            url = f"{settings.public_base_url}/post/id/{post.id}"
            await callback.message.answer(f"ℹ️ Пост уже опубликован.\n🔗 {url}")
            await callback.answer()
            return
        crud.publish_post(db, post)
        pt = post.title
    url = f"{settings.public_base_url}/post/id/{post_id}"
    await callback.message.answer(
        f"✅ <b>Пост опубликован на сайте!</b>\n🔗 {url}", parse_mode="HTML",
    )
    await callback.answer("Опубликовано ✅")


@router.callback_query(F.data.startswith("pub_ch:"))
async def cb_pub_channel(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    if not settings.has_channel:
        await callback.message.answer(
            "⚠️ Telegram-канал не настроен.\n"
            "Добавьте TELEGRAM_CHANNEL_ID в .env и назначьте бота администратором канала."
        )
        await callback.answer()
        return
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        pt, pb = post.title, post.body

    ok, msg_id = await _send_to_channel(callback.bot, post_id, pt, pb)
    if not ok:
        await callback.message.answer(
            "❌ Не удалось отправить сообщение в канал.\n"
            "Проверьте, что бот добавлен администратором канала и имеет право публиковать сообщения."
        )
        await callback.answer()
        return

    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        post = crud.save_channel_publish(db, post, settings.telegram_channel_id.strip(), msg_id)
        msg_url = post.telegram_message_url

    lines = ["✅ <b>Пост опубликован в Telegram-канале!</b>"]
    if msg_url:
        lines.append(f"📢 <a href=\"{msg_url}\">Открыть в канале</a>")
    if settings.has_site:
        lines.append(f"🌐 {settings.public_base_url}/post/id/{post_id}")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer("Опубликовано в канале ✅")


@router.callback_query(F.data.startswith("pub_all:"))
async def cb_pub_all(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        if post.status != "published":
            crud.publish_post(db, post)
        pt, pb = post.title, post.body

    lines = []
    if settings.has_site:
        site_url = f"{settings.public_base_url}/post/id/{post_id}"
        lines.append(f"✅ <b>Сайт:</b> {site_url}")

    if not settings.has_channel:
        lines.append("ℹ️ Telegram-канал не настроен. Добавьте TELEGRAM_CHANNEL_ID в .env.")
    else:
        ok, msg_id = await _send_to_channel(callback.bot, post_id, pt, pb)
        if ok:
            with SessionLocal() as db:
                post = crud.get_post(db, post_id)
                post = crud.save_channel_publish(db, post, settings.telegram_channel_id.strip(), msg_id)
                msg_url = post.telegram_message_url
            if msg_url:
                lines.append(f"✅ <b>Канал:</b> <a href=\"{msg_url}\">Открыть сообщение</a>")
            else:
                lines.append("✅ <b>Пост отправлен в канал.</b>")
        else:
            lines.append(
                "⚠️ Пост опубликован на сайте, но не удалось отправить в канал.\n"
                "Проверьте права бота в канале."
            )

    await callback.message.answer("\n".join(lines) if lines else "✅ Готово.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title:"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    await state.set_state(EditPost.title)
    await state.update_data(post_id=post_id)
    await callback.message.answer("✏️ Введите новый заголовок (минимум 3 символа).\nДля отмены — /cancel")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_body:"))
async def cb_edit_body(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    await state.set_state(EditPost.body)
    await state.update_data(post_id=post_id)
    await callback.message.answer("📝 Введите новый текст (минимум 10 символов).\nДля отмены — /cancel")
    await callback.answer()


@router.callback_query(F.data.startswith("keep_draft:"))
async def cb_keep_draft(callback: CallbackQuery) -> None:
    await callback.answer("💾 Черновик сохранён")
    await callback.message.answer("💾 Черновик сохранён. Вернитесь к нему командой /drafts")


@router.callback_query(F.data.startswith("del_post:"))
async def cb_delete(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":", 1)[1])
    with SessionLocal() as db:
        post = crud.get_post(db, post_id)
        if post is None:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        crud.soft_delete_post(db, post)
    await callback.message.answer(f"🗑 Публикация #{post_id} удалена.")
    await callback.answer("Удалено")


# ── Запуск ────────────────────────────────────────────────────────────────────

async def create_dispatcher() -> Dispatcher:
    init_db()
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp


async def run_bot() -> None:
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN не задан. Добавьте токен бота в файл .env:\n"
            "BOT_TOKEN=ваш_токен_из_BotFather"
        )
    if not settings.owner_ids:
        logger.warning(
            "BOT_OWNER_IDS не задан — бот работает в режиме разработки "
            "(доступен всем пользователям). Добавьте свой Telegram user ID в .env."
        )
    bot = Bot(token=settings.bot_token)
    dp = await create_dispatcher()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

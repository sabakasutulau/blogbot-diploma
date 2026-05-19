from datetime import datetime
import re
from uuid import uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Post
from app.schemas import PostCreate, PostUpdate

_ALLOWED_STATUSES = {"draft", "published", "archived", "deleted"}


_TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "j", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}


def _translit(text: str) -> str:
    """Transliterate Cyrillic characters to ASCII equivalents."""
    result = []
    for ch in text.lower():
        result.append(_TRANSLIT_MAP.get(ch, ch))
    return "".join(result)


def slugify(value: str) -> str:
    value = _translit(value.strip())
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-") or "post"
    return f"{value[:80]}-{uuid4().hex[:8]}"


def make_channel_message_url(channel_id: str, message_id: int) -> str | None:
    """
    Build a t.me link to a channel message.

    Works for:
      - public channels:  @channelusername → https://t.me/channelusername/123
      - private channels: -100123456789   → https://t.me/c/123456789/123
    """
    channel = channel_id.strip()
    if not channel or not message_id:
        return None
    if channel.startswith("@"):
        username = channel.lstrip("@")
        return f"https://t.me/{username}/{message_id}"
    # Numeric channel ID (private channels start with -100)
    numeric = channel.lstrip("-")
    if numeric.startswith("100"):
        numeric = numeric[3:]  # strip the -100 prefix
    return f"https://t.me/c/{numeric}/{message_id}"


def create_post(db: Session, data: PostCreate) -> Post:
    status = data.status if data.status in _ALLOWED_STATUSES else "draft"
    post = Post(
        title=data.title,
        slug=slugify(data.title),
        body=data.body,
        status=status,
        author_telegram_id=data.author_telegram_id,
        author_name=data.author_name,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def list_posts(db: Session, status: str | None = None) -> list[Post]:
    stmt: Select[tuple[Post]] = select(Post).order_by(Post.created_at.desc())
    if status:
        stmt = stmt.where(Post.status == status)
    else:
        # By default exclude deleted posts from public listings
        stmt = stmt.where(Post.status != "deleted")
    return list(db.scalars(stmt).all())


def list_user_posts(db: Session, telegram_user_id: int, status: str) -> list[Post]:
    """Return posts for a specific Telegram user filtered by status."""
    stmt = (
        select(Post)
        .where(Post.author_telegram_id == telegram_user_id)
        .where(Post.status == status)
        .order_by(Post.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_post(db: Session, post_id: int) -> Post | None:
    return db.get(Post, post_id)


def get_post_by_slug(db: Session, slug: str) -> Post | None:
    stmt = select(Post).where(Post.slug == slug)
    return db.scalars(stmt).first()


def update_post(db: Session, post: Post, data: PostUpdate) -> Post:
    if data.title is not None:
        post.title = data.title
    if data.body is not None:
        post.body = data.body
    if data.status is not None and data.status in _ALLOWED_STATUSES:
        post.status = data.status
        post.published_at = datetime.utcnow() if data.status == "published" and post.published_at is None else post.published_at
    db.commit()
    db.refresh(post)
    return post


def publish_post(db: Session, post: Post) -> Post:
    post.status = "published"
    if post.published_at is None:
        post.published_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


def save_channel_publish(
    db: Session,
    post: Post,
    channel_id: str,
    message_id: int,
) -> Post:
    """Save Telegram channel publication metadata to the post."""
    post.telegram_channel_id = channel_id
    post.telegram_message_id = message_id
    post.telegram_message_url = make_channel_message_url(channel_id, message_id)
    post.published_to_channel_at = datetime.utcnow()
    # Also ensure the post is published on the site
    if post.status != "published":
        post.status = "published"
        if post.published_at is None:
            post.published_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


def soft_delete_post(db: Session, post: Post) -> None:
    """Mark post as deleted (soft delete). Does not physically remove from DB."""
    post.status = "deleted"
    db.commit()


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)
    db.commit()


def stats(db: Session) -> dict[str, int]:
    total = db.scalar(select(func.count(Post.id)).where(Post.status != "deleted")) or 0
    published = db.scalar(select(func.count(Post.id)).where(Post.status == "published")) or 0
    drafts = db.scalar(select(func.count(Post.id)).where(Post.status == "draft")) or 0
    in_channel = db.scalar(
        select(func.count(Post.id)).where(Post.telegram_message_id.isnot(None))
    ) or 0
    return {"total": total, "published": published, "drafts": drafts, "in_channel": in_channel}

"""
API tests for the BlogBot diploma project.
Uses the `client` fixture from conftest.py (isolated SQLite test DB).
"""
from app.config import settings


# ── Базовые тесты ──────────────────────────────────────────────────────────────

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_token_required(client):
    response = client.post(
        "/api/posts",
        json={"title": "Без токена", "body": "Этот запрос должен быть отклонён."},
    )
    assert response.status_code == 401


def test_create_publish_and_list_post(client):
    headers = {"X-Admin-Token": settings.admin_token}

    # Create draft
    create_response = client.post(
        "/api/posts",
        json={
            "title": "Тестовый пост",
            "body": "Текст тестового поста для проверки API.",
            "status": "draft",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    post = create_response.json()
    assert post["status"] == "draft"

    # Publish
    publish_response = client.patch(
        f"/api/posts/{post['id']}/publish", headers=headers
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    # List published
    list_response = client.get("/api/posts?status=published")
    assert list_response.status_code == 200
    assert any(item["id"] == post["id"] for item in list_response.json())


def test_stats_endpoint(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "published" in data
    assert "drafts" in data


def test_post_by_id_redirect(client):
    """Verify that /post/id/{post_id} redirects to the slug URL for published posts."""
    headers = {"X-Admin-Token": settings.admin_token}

    # Create and publish a post
    create_resp = client.post(
        "/api/posts",
        json={"title": "Ссылка по ID", "body": "Проверка маршрута по числовому ID поста."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    post = create_resp.json()
    post_id = post["id"]

    client.patch(f"/api/posts/{post_id}/publish", headers=headers)

    # /post/id/{post_id} should redirect (302) to /post/{slug}
    response = client.get(f"/post/id/{post_id}", follow_redirects=False)
    assert response.status_code == 302
    assert "/post/" in response.headers["location"]


def test_post_by_id_not_found(client):
    """Draft or non-existent posts should return 404."""
    headers = {"X-Admin-Token": settings.admin_token}

    create_resp = client.post(
        "/api/posts",
        json={"title": "Черновик без публикации", "body": "Только черновик, не публикуем."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    draft_id = create_resp.json()["id"]

    # Draft post → 404
    response = client.get(f"/post/id/{draft_id}", follow_redirects=False)
    assert response.status_code == 404

    # Non-existent ID → 404
    response = client.get("/post/id/99999", follow_redirects=False)
    assert response.status_code == 404


def test_slug_is_ascii(client):
    """Slugs generated from Cyrillic titles must be ASCII-only."""
    headers = {"X-Admin-Token": settings.admin_token}

    create_resp = client.post(
        "/api/posts",
        json={"title": "Кириллический заголовок поста", "body": "Проверка транслитерации слага."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    slug = create_resp.json()["slug"]
    assert slug.isascii(), f"Slug is not ASCII: {slug!r}"


# ── Новые тесты ────────────────────────────────────────────────────────────────

def test_telegram_channel_id_in_settings():
    """TELEGRAM_CHANNEL_ID читается из настроек (может быть пустым, но поле существует)."""
    assert hasattr(settings, "telegram_channel_id")
    # Поле должно быть строкой (пустой или с реальным ID канала)
    assert isinstance(settings.telegram_channel_id, str)


def test_publish_without_telegram_channel(client):
    """Публикация на сайте работает без TELEGRAM_CHANNEL_ID."""
    headers = {"X-Admin-Token": settings.admin_token}

    create_resp = client.post(
        "/api/posts",
        json={"title": "Публикация без канала", "body": "Проверяем публикацию на сайте без Telegram-канала."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    publish_resp = client.patch(f"/api/posts/{post_id}/publish", headers=headers)
    assert publish_resp.status_code == 200
    assert publish_resp.json()["status"] == "published"

    # Пост доступен по ID
    id_resp = client.get(f"/post/id/{post_id}", follow_redirects=False)
    assert id_resp.status_code == 302


def test_deleted_post_not_in_public_feed(client):
    """Удалённые посты (status=deleted) не отображаются в публичной ленте."""
    headers = {"X-Admin-Token": settings.admin_token}

    # Создаём и публикуем пост
    create_resp = client.post(
        "/api/posts",
        json={"title": "Пост для удаления", "body": "Этот пост будет помечен как удалённый."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    client.patch(f"/api/posts/{post_id}/publish", headers=headers)

    # Переводим в статус deleted
    update_resp = client.patch(
        f"/api/posts/{post_id}",
        json={"status": "deleted"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "deleted"

    # Удалённый пост не должен отображаться в публичной ленте
    list_resp = client.get("/api/posts?status=published")
    assert list_resp.status_code == 200
    assert not any(item["id"] == post_id for item in list_resp.json())

    # Удалённый пост недоступен по числовому ID
    id_resp = client.get(f"/post/id/{post_id}", follow_redirects=False)
    assert id_resp.status_code == 404


def test_deleted_post_not_in_drafts(client):
    """Удалённые черновики не отображаются в списке черновиков (/api/posts?status=draft)."""
    headers = {"X-Admin-Token": settings.admin_token}

    create_resp = client.post(
        "/api/posts",
        json={"title": "Черновик для удаления", "body": "Этот черновик будет помечен как удалённый."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    # Помечаем как удалённый
    client.patch(f"/api/posts/{post_id}", json={"status": "deleted"}, headers=headers)

    # Не должен появляться в черновиках
    drafts_resp = client.get("/api/posts?status=draft")
    assert drafts_resp.status_code == 200
    assert not any(item["id"] == post_id for item in drafts_resp.json())


def test_default_list_excludes_deleted(client):
    """Список /api/posts без фильтра не возвращает удалённые посты."""
    headers = {"X-Admin-Token": settings.admin_token}

    create_resp = client.post(
        "/api/posts",
        json={"title": "Ещё один черновик для удаления", "body": "Проверяем фильтрацию удалённых постов по умолчанию."},
        headers=headers,
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    client.patch(f"/api/posts/{post_id}", json={"status": "deleted"}, headers=headers)

    # Без параметра status удалённые не должны попасть в список
    all_resp = client.get("/api/posts")
    assert all_resp.status_code == 200
    assert not any(item["id"] == post_id for item in all_resp.json())

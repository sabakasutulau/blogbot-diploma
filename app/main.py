from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.db import get_db, init_db
from app.schemas import PostCreate, PostRead, PostUpdate, StatsRead


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    posts = crud.list_posts(db, status="published")
    return templates.TemplateResponse(request, "index.html", {"posts": posts, "app_name": settings.app_name})


@app.get("/post/id/{post_id}", response_class=HTMLResponse)
def post_by_id(post_id: int, request: Request, db: Session = Depends(get_db)):
    """Redirect from numeric ID to the slug-based post URL."""
    post = crud.get_post(db, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    return RedirectResponse(url=f"/post/{post.slug}", status_code=302)


@app.get("/post/{slug}", response_class=HTMLResponse)
def post_page(slug: str, request: Request, db: Session = Depends(get_db)):
    post = crud.get_post_by_slug(db, slug)
    if post is None or post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(request, "post.html", {"post": post, "app_name": settings.app_name})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html", {"app_name": settings.app_name})


@app.get("/api/posts", response_model=list[PostRead])
def api_list_posts(status: str | None = None, db: Session = Depends(get_db)):
    return crud.list_posts(db, status=status)


@app.post("/api/posts", response_model=PostRead, status_code=201, dependencies=[Depends(require_admin)])
def api_create_post(data: PostCreate, db: Session = Depends(get_db)):
    return crud.create_post(db, data)


@app.patch("/api/posts/{post_id}", response_model=PostRead, dependencies=[Depends(require_admin)])
def api_update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud.update_post(db, post, data)


@app.patch("/api/posts/{post_id}/publish", response_model=PostRead, dependencies=[Depends(require_admin)])
def api_publish_post(post_id: int, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud.publish_post(db, post)


@app.delete("/api/posts/{post_id}", status_code=204, dependencies=[Depends(require_admin)])
def api_delete_post(post_id: int, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    crud.delete_post(db, post)
    return None


@app.get("/api/health")
def api_health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/stats", response_model=StatsRead)
def api_stats(db: Session = Depends(get_db)):
    return crud.stats(db)

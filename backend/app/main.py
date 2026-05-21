import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_frontend_dist() -> Path:
    override = os.getenv("FRONTEND_DIST", "").strip()
    if override:
        return Path(override)
    return PROJECT_ROOT / "frontend" / "dist"


FRONTEND_DIST = resolve_frontend_dist()
INDEX_HTML = FRONTEND_DIST / "index.html"

from . import crud
from .database import Base, SessionLocal, engine, get_db
from .schemas import (
    BulkTaskCreate,
    BulkTaskResult,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    DayMarkOut,
    DayMarkSet,
    DayMarksBulkSet,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TelegramStatus,
)
from .scheduler import start_scheduler
from .telegram_service import get_bot_debug_info, start_telegram_bot, stop_telegram_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        crud.seed_default_categories(db)
    finally:
        db.close()
    if INDEX_HTML.is_file():
        logger.info("Веб-интерфейс: %s", INDEX_HTML)
    else:
        logger.warning(
            "index.html не найден (%s). Соберите: cd frontend && npm install && npm run build",
            INDEX_HTML,
        )
    start_scheduler()
    await start_telegram_bot()
    yield
    await stop_telegram_bot()


app = FastAPI(title="Task Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/debug/telegram")
def debug_telegram():
    return get_bot_debug_info()


@app.get("/api/debug/frontend")
def debug_frontend():
    files = []
    if FRONTEND_DIST.is_dir():
        files = [p.name for p in sorted(FRONTEND_DIST.iterdir())[:30]]
    return {
        "project_root": str(PROJECT_ROOT),
        "frontend_dist": str(FRONTEND_DIST),
        "index_html": str(INDEX_HTML),
        "dist_exists": FRONTEND_DIST.is_dir(),
        "index_exists": INDEX_HTML.is_file(),
        "files_in_dist": files,
    }


@app.get("/api/tasks", response_model=list[TaskOut])
def get_tasks(db: Session = Depends(get_db)):
    return crud.list_tasks(db)


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def post_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(db, payload.title, payload.notes, payload.due_at)


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def patch_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")
    data = payload.model_dump(exclude_unset=True)
    if data.get("completed") is False and task.reminder_sent:
        data["reminder_sent"] = False
    return crud.update_task(db, task, **data)


@app.delete("/api/tasks/{task_id}", status_code=204)
def remove_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")
    crud.delete_task(db, task)


@app.post("/api/tasks/bulk", response_model=BulkTaskResult, status_code=201)
def post_tasks_bulk(payload: BulkTaskCreate, db: Session = Depends(get_db)):
    tasks = crud.bulk_create_tasks(db, payload.title, payload.notes, payload.due_ats)
    return BulkTaskResult(created=len(tasks), tasks=tasks)


@app.get("/api/categories", response_model=list[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)


@app.post("/api/categories", response_model=CategoryOut, status_code=201)
def post_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, payload.name, payload.color, payload.sort_order)


@app.patch("/api/categories/{category_id}", response_model=CategoryOut)
def patch_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
):
    cat = crud.get_category(db, category_id)
    if not cat:
        raise HTTPException(404, "Категория не найдена")
    return crud.update_category(db, cat, **payload.model_dump(exclude_unset=True))


@app.delete("/api/categories/{category_id}", status_code=204)
def remove_category(category_id: int, db: Session = Depends(get_db)):
    cat = crud.get_category(db, category_id)
    if not cat:
        raise HTTPException(404, "Категория не найдена")
    crud.delete_category(db, cat)


@app.get("/api/day-marks", response_model=list[DayMarkOut])
def get_day_marks(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_day_marks(db, date_from, date_to)


@app.put("/api/day-marks/{day}", response_model=DayMarkOut | None)
def put_day_mark(day: date, payload: DayMarkSet, db: Session = Depends(get_db)):
    if payload.category_id is not None and not crud.get_category(db, payload.category_id):
        raise HTTPException(404, "Категория не найдена")
    return crud.set_day_mark(db, day, payload.category_id)


@app.post("/api/day-marks/bulk", response_model=list[DayMarkOut])
def post_day_marks_bulk(payload: DayMarksBulkSet, db: Session = Depends(get_db)):
    if payload.category_id is not None and not crud.get_category(db, payload.category_id):
        raise HTTPException(404, "Категория не найдена")
    return crud.bulk_set_day_marks(db, payload.days, payload.category_id)


@app.get("/api/telegram/status", response_model=TelegramStatus)
def telegram_status(db: Session = Depends(get_db)):
    linked = crud.is_telegram_linked(db)
    return TelegramStatus(linked=linked, link_code=None)


@app.post("/api/telegram/link-code", response_model=TelegramStatus)
def telegram_link_code(db: Session = Depends(get_db)):
    code = crud.create_link_code(db)
    return TelegramStatus(linked=crud.is_telegram_linked(db), link_code=code)


@app.post("/api/telegram/unlink", response_model=TelegramStatus)
def telegram_unlink(db: Session = Depends(get_db)):
    crud.set_setting(db, crud.CHAT_ID_KEY, None)
    return TelegramStatus(linked=False, link_code=None)


@app.get("/", include_in_schema=False)
def serve_frontend_root():
    if INDEX_HTML.is_file():
        return FileResponse(INDEX_HTML)
    return {
        "message": "API работает. index.html не найден.",
        "health": "/api/health",
        "debug": "/api/debug/frontend",
        "build": "cd frontend && npm install && npm run build",
    }


_assets_dir = FRONTEND_DIST / "assets"
if _assets_dir.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_assets_dir),
        name="frontend-assets",
    )

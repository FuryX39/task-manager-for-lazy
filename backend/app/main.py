import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud
from .database import Base, engine, get_db
from .models import Task
from .schemas import TaskCreate, TaskOut, TaskUpdate, TelegramStatus
from .scheduler import start_scheduler
from .telegram_service import start_telegram_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    start_telegram_bot()
    yield


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

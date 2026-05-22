import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
from fastapi import Depends, FastAPI, HTTPException, Response
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
from .auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    SessionContext,
    create_session_token,
    get_current_session,
    hash_password,
    normalize_email,
    verify_password,
)
from .config import APP_TIMEZONE_NAME, REMINDER_REPEAT_MINUTES, SNOOZE_MINUTES
from .database import Base, engine, get_db
from .google_auth import verify_google_id_token
from .migrations import ensure_schema
from .schemas import (
    AdminUserOut,
    BulkTaskCreate,
    BulkTaskResult,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    DayMarkOut,
    DayMarkSet,
    DayMarksBulkSet,
    DeleteAccountRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TelegramStatus,
    UserOut,
)
from .scheduler import start_scheduler
from .telegram_service import get_bot_debug_info, start_telegram_bot, stop_telegram_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    logger.info(
        "Часовой пояс приложения: %s (повтор напоминаний каждые %s мин)",
        APP_TIMEZONE_NAME,
        REMINDER_REPEAT_MINUTES,
    )
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


@app.get("/api/config")
def get_config():
    return {
        "timezone": APP_TIMEZONE_NAME,
        "reminder_repeat_minutes": REMINDER_REPEAT_MINUTES,
        "snooze_minutes": SNOOZE_MINUTES,
    }


def _user_to_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        has_password=bool(user.password_hash),
        has_google=bool(user.google_sub),
        telegram_linked=bool(user.telegram_chat_id),
        is_admin=bool(user.is_admin),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _require_admin(session: SessionContext = Depends(get_current_session)) -> SessionContext:
    if not session.user.is_admin:
        raise HTTPException(403, "Требуются права администратора")
    return session


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(user_id),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "0").strip() == "1",
        path="/",
    )


@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    existing = crud.get_user_by_email(db, email)
    if existing:
        raise HTTPException(409, "Пользователь с таким email уже существует")
    is_first_user = crud.count_users(db) == 0

    user = crud.create_user(
        db,
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        is_admin=is_first_user,
    )

    # Первый пользователь забирает legacy-данные.
    if is_first_user:
        crud.migrate_legacy_data_to_first_user(db, user.id)
    crud.seed_default_categories(db, user.id)
    user = crud.touch_last_login(db, user)
    _set_session_cookie(response, user.id)
    return _user_to_out(user)


@app.post("/api/auth/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    user = crud.get_user_by_email(db, email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Неверный email или пароль")
    user = crud.touch_last_login(db, user)
    _set_session_cookie(response, user.id)
    return _user_to_out(user)


@app.post("/api/auth/google", response_model=UserOut)
def login_google(
    payload: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    claims = verify_google_id_token(payload.id_token)
    email = normalize_email(claims.get("email", ""))
    sub = claims.get("sub", "")
    name = claims.get("name") or email.split("@")[0]
    if not email or not sub:
        raise HTTPException(400, "В токене Google нет email/sub")

    by_sub = crud.get_user_by_google_sub(db, sub)
    if by_sub:
        user = by_sub
    else:
        user = crud.get_user_by_email(db, email)
        if user:
            if user.google_sub and user.google_sub != sub:
                raise HTTPException(409, "Email уже связан с другим Google аккаунтом")
            user = crud.update_user(db, user, google_sub=sub)
        else:
            is_first_user = crud.count_users(db) == 0
            user = crud.create_user(
                db,
                email=email,
                display_name=name,
                google_sub=sub,
                is_admin=is_first_user,
            )
            if is_first_user:
                crud.migrate_legacy_data_to_first_user(db, user.id)
            crud.seed_default_categories(db, user.id)

    user = crud.touch_last_login(db, user)
    _set_session_cookie(response, user.id)
    return _user_to_out(user)


@app.get("/api/auth/me", response_model=UserOut)
def auth_me(session: SessionContext = Depends(get_current_session)):
    return _user_to_out(session.user)


@app.patch("/api/account/profile", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    user = session.user
    updates: dict = {}

    if payload.display_name is not None:
        updates["display_name"] = payload.display_name.strip()

    if payload.email is not None:
        new_email = normalize_email(payload.email)
        if new_email != user.email:
            existing = crud.get_user_by_email(db, new_email)
            if existing and existing.id != user.id:
                raise HTTPException(409, "Этот email уже используется")
            updates["email"] = new_email

    if payload.new_password is not None:
        if user.password_hash:
            if not payload.current_password or not verify_password(
                payload.current_password, user.password_hash
            ):
                raise HTTPException(400, "Неверный текущий пароль")
        updates["password_hash"] = hash_password(payload.new_password)

    if not updates:
        return _user_to_out(user)

    user = crud.update_user(db, user, **updates)
    return _user_to_out(user)


@app.post("/api/auth/logout", status_code=204)
def auth_logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE, path="/")


@app.get("/api/admin/users", response_model=list[AdminUserOut])
def admin_users(
    db: Session = Depends(get_db),
    _admin: SessionContext = Depends(_require_admin),
):
    users = crud.list_active_users(db)
    out: list[AdminUserOut] = []
    for u in users:
        out.append(
            AdminUserOut(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                is_admin=bool(u.is_admin),
                has_password=bool(u.password_hash),
                has_google=bool(u.google_sub),
                telegram_linked=bool(u.telegram_chat_id),
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
        )
    return out


@app.delete("/api/account", status_code=204)
def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    if normalize_email(payload.confirm_email) != session.user.email:
        raise HTTPException(400, "Email подтверждения не совпадает")
    crud.delete_account_cascade(db, session.user)
    response.delete_cookie(key=SESSION_COOKIE, path="/")


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
def get_tasks(
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    return crud.list_tasks(db, session.user.id)


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def post_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    return crud.create_task(
        db, session.user.id, payload.title, payload.notes, payload.due_at
    )


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def patch_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    task = crud.get_task(db, session.user.id, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")
    data = payload.model_dump(exclude_unset=True)
    return crud.update_task(db, task, **data)


@app.delete("/api/tasks/{task_id}", status_code=204)
def remove_task(
    task_id: int,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    task = crud.get_task(db, session.user.id, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")
    crud.delete_task(db, task)


@app.post("/api/tasks/bulk", response_model=BulkTaskResult, status_code=201)
def post_tasks_bulk(
    payload: BulkTaskCreate,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    tasks = crud.bulk_create_tasks(
        db, session.user.id, payload.title, payload.notes, payload.due_ats
    )
    return BulkTaskResult(created=len(tasks), tasks=tasks)


@app.get("/api/categories", response_model=list[CategoryOut])
def get_categories(
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    return crud.list_categories(db, session.user.id)


@app.post("/api/categories", response_model=CategoryOut, status_code=201)
def post_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    return crud.create_category(
        db, session.user.id, payload.name, payload.color, payload.sort_order
    )


@app.patch("/api/categories/{category_id}", response_model=CategoryOut)
def patch_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    cat = crud.get_category(db, session.user.id, category_id)
    if not cat:
        raise HTTPException(404, "Категория не найдена")
    return crud.update_category(db, cat, **payload.model_dump(exclude_unset=True))


@app.delete("/api/categories/{category_id}", status_code=204)
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    cat = crud.get_category(db, session.user.id, category_id)
    if not cat:
        raise HTTPException(404, "Категория не найдена")
    crud.delete_category(db, cat)


@app.get("/api/day-marks", response_model=list[DayMarkOut])
def get_day_marks(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    return crud.list_day_marks(db, session.user.id, date_from, date_to)


@app.put("/api/day-marks/{day}", response_model=DayMarkOut | None)
def put_day_mark(
    day: date,
    payload: DayMarkSet,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    if payload.category_id is not None and not crud.get_category(
        db, session.user.id, payload.category_id
    ):
        raise HTTPException(404, "Категория не найдена")
    return crud.set_day_mark(db, session.user.id, day, payload.category_id)


@app.post("/api/day-marks/bulk", response_model=list[DayMarkOut])
def post_day_marks_bulk(
    payload: DayMarksBulkSet,
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    if payload.category_id is not None and not crud.get_category(
        db, session.user.id, payload.category_id
    ):
        raise HTTPException(404, "Категория не найдена")
    return crud.bulk_set_day_marks(
        db, session.user.id, payload.days, payload.category_id
    )


@app.get("/api/telegram/status", response_model=TelegramStatus)
def telegram_status(session: SessionContext = Depends(get_current_session)):
    linked = crud.is_telegram_linked(session.user)
    return TelegramStatus(linked=linked, link_code=None)


@app.post("/api/telegram/link-code", response_model=TelegramStatus)
def telegram_link_code(
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    code = crud.create_link_code_for_user(db, session.user)
    return TelegramStatus(linked=crud.is_telegram_linked(session.user), link_code=code)


@app.post("/api/telegram/unlink", response_model=TelegramStatus)
def telegram_unlink(
    db: Session = Depends(get_db),
    session: SessionContext = Depends(get_current_session),
):
    crud.unlink_telegram(db, session.user)
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

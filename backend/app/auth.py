import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

SESSION_COOKIE = "tm_session"
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(60 * 60 * 24 * 30)))
PASSWORD_ITERATIONS = 120_000


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _secret_key() -> str:
    return os.getenv("SESSION_SECRET", "dev-insecure-change-me")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, raw_iter, raw_salt, raw_digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(raw_iter)
        salt = base64.b64decode(raw_salt.encode("ascii"))
        digest = base64.b64decode(raw_digest.encode("ascii"))
    except Exception:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(check, digest)


def create_session_token(user_id: int) -> str:
    payload = f"{user_id}"
    sig = hmac.new(_secret_key().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def parse_session_token(token: str) -> int | None:
    if "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    expected = hmac.new(
        _secret_key().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return int(payload)
    except ValueError:
        return None


@dataclass
class SessionContext:
    user: User


def get_current_session(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> SessionContext:
    if not session_token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    user_id = parse_session_token(session_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Неверная сессия")
    user = (
        db.query(User)
        .filter(User.id == user_id, User.deleted_at.is_(None))
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return SessionContext(user=user)


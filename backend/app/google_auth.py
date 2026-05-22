import os

from fastapi import HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token


def verify_google_id_token(raw_token: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID не настроен")
    try:
        payload = id_token.verify_oauth2_token(raw_token, requests.Request(), client_id)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Неверный Google токен") from exc
    if not payload.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google email не подтверждён")
    return payload


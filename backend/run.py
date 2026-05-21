"""Запуск API: читает HOST и PORT из .env в корне проекта."""

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT)

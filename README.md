# Таск-менеджер (веб + Telegram)

Личный планировщик задач с датой и временем: основной интерфейс в браузере, напоминания в Telegram-боте.

## Возможности

- Создание задач с датой, временем и заметками
- Группировка: предстоящие, просроченные, выполненные
- Привязка Telegram через одноразовый код `/link`
- Автоматическая отправка напоминания в момент наступления срока

## Быстрый старт

### 1. Telegram-бот

1. Напишите [@BotFather](https://t.me/BotFather), создайте бота командой `/newbot`.
2. Скопируйте токен.

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
# Отредактируйте ..\.env — TELEGRAM_BOT_TOKEN, HOST, PORT
python run.py
```

Для разработки с автоперезагрузкой:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

На сервере в `.env` укажите `HOST=127.0.0.1` (за nginx) или `HOST=0.0.0.0` (прямой доступ) и нужный `PORT`.

### 3. Frontend

В другом терминале:

```powershell
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173

### 4. Привязка Telegram

1. В веб-интерфейсе нажмите **Привязать Telegram**.
2. Отправьте боту команду вида `/link A1B2C3` (код покажет интерфейс).
3. Создайте задачу с ближайшим временем — в срок придёт сообщение в Telegram.

## Стек

| Часть | Технологии |
|-------|------------|
| API | FastAPI, SQLite, APScheduler |
| Бот | python-telegram-bot |
| UI | React, Vite, TypeScript |

Данные хранятся в `backend/data/tasks.db`.

## API (кратко)

- `GET/POST /api/tasks` — список и создание
- `PATCH/DELETE /api/tasks/{id}` — изменение и удаление
- `POST /api/telegram/link-code` — код привязки
- `GET /api/telegram/status` — статус привязки

Планировщик проверяет задачи каждые 30 секунд. Если срок наступил и задача не выполнена — отправляется одно напоминание в привязанный чат.

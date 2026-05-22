# Таск-менеджер (веб + Telegram)

Личный планировщик задач с датой и временем: основной интерфейс в браузере, напоминания в Telegram-боте.

## Возможности

- Отдельные пользователи (собственные задачи, категории, календарные метки и Telegram-привязка)
- Админ-панель (список профилей пользователей без доступа к их задачам)
- Авторизация через email/пароль и Google аккаунт
- Создание задач с датой, временем и заметками
- Календарь с цветными метками дней + массовое добавление задач
- Привязка Telegram через одноразовый код `/link`
- Напоминания каждые N минут (по умолчанию 10), пока задача не выполнена
- Кнопки в боте: **Выполнено** / **Отложить на 10 минут**

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
# Отредактируйте ..\.env — TELEGRAM_BOT_TOKEN, HOST, PORT, SESSION_SECRET, APP_TIMEZONE
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

Для Google входа добавьте в `frontend/.env`:

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

### 4. Авторизация и привязка Telegram

1. Зарегистрируйтесь или войдите через Google.
2. В веб-интерфейсе нажмите **Привязать Telegram**.
3. Отправьте боту команду вида `/link A1B2C3` (код покажет интерфейс).
4. Создайте задачу с ближайшим временем — в срок придёт сообщение в Telegram.

## Стек

| Часть | Технологии |
|-------|------------|
| API | FastAPI, SQLite, APScheduler |
| Бот | python-telegram-bot |
| UI | React, Vite, TypeScript |

Данные хранятся в `backend/data/tasks.db`.

## API (кратко)

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/google`, `GET /api/auth/me`
- `PATCH /api/account/profile` — редактирование профиля (имя/email/пароль)
- `GET /api/admin/users` — сводка по профилям (только для админа)
- `GET/POST /api/tasks` — список и создание
- `PATCH/DELETE /api/tasks/{id}` — изменение и удаление
- `POST /api/telegram/link-code` — код привязки
- `GET /api/telegram/status` — статус привязки

Планировщик проверяет задачи каждые 30 секунд. Если срок наступил и задача не выполнена — напоминание повторяется каждые `REMINDER_REPEAT_MINUTES`.

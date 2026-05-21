# Установка на сервер (Ubuntu/Debian)

Путь проекта: `/opt/task_manager/task-manager-for-lazy`

## 1. Системные пакеты

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
# Для сборки веб-интерфейса (опционально):
sudo apt install -y nodejs npm
```

## 2. Пользователь для сервиса

```bash
sudo useradd --system --home /opt/task_manager --shell /usr/sbin/nologin taskmanager
sudo chown -R taskmanager:taskmanager /opt/task_manager
```

## 3. Код и .env

```bash
cd /opt/task_manager/task-manager-for-lazy
sudo -u taskmanager git pull   # или первый clone от имени taskmanager

sudo -u taskmanager cp .env.example .env
sudo nano /opt/task_manager/task-manager-for-lazy/.env
```

Минимум в `.env`:

```env
TELEGRAM_BOT_TOKEN=...
HOST=127.0.0.1
PORT=8000
CORS_ORIGINS=https://ваш-домен.ru
```

`HOST=127.0.0.1`, если снаружи стоит nginx; `0.0.0.0` — если API доступен напрямую.

## 4. Python-зависимости

```bash
cd /opt/task_manager/task-manager-for-lazy/backend
sudo -u taskmanager python3 -m venv .venv
sudo -u taskmanager .venv/bin/pip install --upgrade pip
sudo -u taskmanager .venv/bin/pip install -r requirements.txt
```

Проверка вручную:

```bash
sudo -u taskmanager .venv/bin/python run.py
# Ctrl+C после проверки
```

## 5. Frontend (если нужен веб на том же сервере)

```bash
cd /opt/task_manager/task-manager-for-lazy/frontend
sudo -u taskmanager npm install
sudo -u taskmanager npm run build
```

После `npm run build` backend отдаёт `frontend/dist/` с корня (`http://IP:PORT/`).
Проверка API без фронта: `http://IP:PORT/api/health` → `{"ok":true}`.

Опционально nginx на 80/443 вместо прямого доступа к порту.

## 6. systemd

```bash
sudo cp /opt/task_manager/task-manager-for-lazy/deploy/task-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable task-manager
sudo systemctl start task-manager
sudo systemctl status task-manager
```

Логи:

```bash
journalctl -u task-manager -f
```

### Telegram-бот не отвечает на /link

1. Проверьте токен в `.env` и перезапуск: `sudo systemctl restart task-manager`
2. Диагностика: `curl http://127.0.0.1:8000/api/debug/telegram`  
   Должно быть `"token_configured": true`, `"polling_running": true`
3. Логи: `journalctl -u task-manager -f` — строка `Telegram-бот запущен: @имя_бота`
4. В Telegram пишите **тому боту**, чей токен в `.env` (проверьте у @BotFather)
5. Команда: `/link КОД` (код из веба, действует 15 минут). Сначала `/start` — если отвечает, polling работает
6. На сервере мог быть включён webhook — в новых версиях он сбрасывается при старте автоматически

### Ошибка `status=203/EXEC`

Systemd не находит исполняемый файл в `ExecStart`. Проверьте:

```bash
# Реальный путь к проекту (часто опечатка в имени папки!)
ls -la /opt/task_manager/

# Должен существовать интерпретатор из venv:
ls -la /opt/task_manager/ВАША_ПАПКА/backend/.venv/bin/python

# Тест запуска вручную:
cd /opt/task_manager/ВАША_ПАПКА/backend
sudo -u taskmanager .venv/bin/python run.py
```

В `/etc/systemd/system/task-manager.service` пути в `WorkingDirectory` и `ExecStart` должны **точно** совпадать с папкой на диске, затем:

```bash
sudo systemctl daemon-reload
sudo systemctl restart task-manager
```

После обновления кода:

```bash
cd /opt/task_manager/task-manager-for-lazy
sudo -u taskmanager git pull
sudo -u taskmanager backend/.venv/bin/pip install -r backend/requirements.txt
sudo systemctl restart task-manager
```

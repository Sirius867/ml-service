# Запуск проекта

## Запуск через Docker Compose

Для запуска потребуются Docker Desktop и Docker Compose.

Склонируйте репозиторий и перейдите в папку проекта:

```powershell
git clone <ссылка-на-репозиторий>
cd ml-service
```

Создайте локальный файл с переменными окружения:

```powershell
Copy-Item app\.env.example app\.env
```

Запустите приложение:

```powershell
docker compose up --build
```

После запуска доступны:

- Web-интерфейс: `http://localhost`;
- Swagger UI: `http://localhost/docs`;
- RabbitMQ Management: `http://localhost:15672`.

Данные для входа в RabbitMQ Management:

```text
Логин: ml_user
Пароль: ml_password
```

Демонстрационный пользователь:

```text
Email: demo@example.com
Пароль: demo1234
```

Для остановки приложения нажмите `Ctrl+C` или выполните в другом терминале:

```powershell
docker compose down
```

## Запуск на Windows без Docker

Для запуска без Docker необходимо установить:

- Python 3.12 или новее;
- PostgreSQL;
- Erlang OTP;
- RabbitMQ Server.

### 1. Установка Python-зависимостей

Выполните из корня проекта:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r app\requirements-dev.txt
```

### 2. Создание базы данных

Откройте SQL Shell (`psql`) под пользователем `postgres` и выполните:

```sql
CREATE USER ml_user WITH PASSWORD 'ml_password';
CREATE DATABASE ml_service OWNER ml_user;
```

Если пользователь и база уже существуют, повторно создавать их не нужно.

### 3. Запуск RabbitMQ

Откройте RabbitMQ Command Prompt от имени администратора:

```powershell
rabbitmq-plugins enable rabbitmq_management
rabbitmq-service start
```

### 4. Настройка переменных окружения

В каждом PowerShell-окне, в котором будет запущено приложение или воркер, выполните:

```powershell
$env:DATABASE_HOST="localhost"
$env:DATABASE_PORT="5432"
$env:DATABASE_NAME="ml_service"
$env:DATABASE_USER="ml_user"
$env:DATABASE_PASSWORD="ml_password"
$env:RABBITMQ_HOST="localhost"
$env:RABBITMQ_PORT="5672"
$env:RABBITMQ_USER="guest"
$env:RABBITMQ_PASSWORD="guest"
$env:RABBITMQ_QUEUE="ml_tasks"
$env:AUTH_SECRET="local_development_secret"
$env:AUTH_TOKEN_TTL_MINUTES="1440"
```

### 5. Запуск приложения

В первом PowerShell-окне:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.src.main:app --host 127.0.0.1 --port 8080
```

Во втором PowerShell-окне повторите настройку переменных окружения и выполните:

```powershell
.\.venv\Scripts\Activate.ps1
$env:WORKER_ID="worker-1"
python -m app.src.worker
```

В третьем PowerShell-окне повторите настройку переменных окружения и выполните:

```powershell
.\.venv\Scripts\Activate.ps1
$env:WORKER_ID="worker-2"
python -m app.src.worker
```

После запуска Web-интерфейс будет доступен по адресу:

```text
http://localhost:8080
```

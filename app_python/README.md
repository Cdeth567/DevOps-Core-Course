[![Python CI (tests + docker)](https://github.com/Cdeth567/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg?branch=lab03)](https://github.com/Cdeth567/DevOps-Core-Course/actions/workflows/python-ci.yml)

# DevOps Info Service

## Overview
DevOps Info Service is a small Flask web application that exposes:
- `GET /` — service metadata, system/runtime info, request details, and visit counter increment
- `GET /visits` — current persisted visit count
- `GET /health` — simple health check endpoint
- `GET /ready` — readiness probe endpoint
- `GET /metrics` — Prometheus metrics

The application stores visit statistics in a file (default: `/data/visits`) so the counter survives container restarts when a volume is mounted.

## Prerequisites
- Python 3.11+
- pip
- (Windows) Python Launcher `py` is recommended

## Installation

### 1) Clone repository
```bash
git clone <repo-url>
cd app_python
```

### 2) Create and activate virtual environment

**Windows (PowerShell):**
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```bat
py -m venv venv
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3) Install dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

Default:
```bash
python app.py
```

Custom config:

**Linux/Mac:**
```bash
HOST=127.0.0.1 PORT=3000 DEBUG=True VISITS_FILE=./data/visits python app.py
```

**Windows (PowerShell):**
```powershell
$env:HOST="127.0.0.1"
$env:PORT="3000"
$env:DEBUG="True"
$env:VISITS_FILE=".\data\visits"
python app.py
```

**Windows (CMD):**
```bat
set HOST=127.0.0.1
set PORT=3000
set DEBUG=True
set VISITS_FILE=.\data\visits
python app.py
```

## API Endpoints
- `GET /` — service and system information, increments the counter
- `GET /visits` — current visit counter value from persisted storage
- `GET /health` — health check
- `GET /ready` — readiness check
- `GET /metrics` — Prometheus metrics

Examples:
```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/visits
curl http://127.0.0.1:5000/health
```

Pretty output:
```bash
curl http://127.0.0.1:5000/ | python -m json.tool
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| HOST | 0.0.0.0 | Bind address |
| PORT | 5000 | HTTP port |
| DEBUG | False | Flask debug mode |
| VISITS_FILE | /data/visits | Path to the persisted visits counter |
| SERVICE_NAME | devops-info-service | Service name shown in the API |
| SERVICE_VERSION | 1.0.0 | Service version shown in the API |
| SERVICE_DESCRIPTION | DevOps course info service | Service description shown in the API |

## Docker

This application can also be built and run as a Docker container.

### Build (local)
```bash
docker build -t devops-info-service:lab12 .
```

### Run with a bind mount
```bash
mkdir -p data
docker run --rm -p 5000:5000 \
  -e VISITS_FILE=/data/visits \
  -v "$(pwd)/data:/data" \
  --name devops-info-service \
  devops-info-service:lab12
```

Then test:
```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/visits
cat ./data/visits
```

### Docker Compose
`docker-compose.yml` is included for local persistence testing.

Start the application:
```bash
mkdir -p data
docker compose up -d --build
```

Verify persistence:
```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/visits
cat ./data/visits
docker compose restart
curl http://127.0.0.1:5000/visits
cat ./data/visits
```

Stop it:
```bash
docker compose down
```

Expected persistence flow:
1. First request to `/` creates `./data/visits` with value `1`
2. Additional requests keep incrementing the file
3. After container restart, `/visits` returns the previously saved value instead of resetting to `0`

### Pull from Docker Hub
Pattern:
```bash
docker pull <dockerhub_username>/<repo_name>:<tag>
docker run --rm -p <host_port>:5000 <dockerhub_username>/<repo_name>:<tag>
```

> Note (Windows PowerShell): `curl` is an alias for `Invoke-WebRequest`.
> For classic curl behavior, use `curl.exe`.

## Testing
Install dev dependencies:
```bash
python -m pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest
```

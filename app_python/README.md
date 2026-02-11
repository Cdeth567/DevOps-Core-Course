# DevOps Info Service

## Overview
DevOps Info Service is a small Flask web application that exposes:
- `GET /` — service metadata, system/runtime info, and request details
- `GET /health` — simple health check endpoint

This project is the foundation for future DevOps labs (Docker, CI/CD, monitoring, Kubernetes).

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
HOST=127.0.0.1 PORT=3000 DEBUG=True python app.py
```

**Windows (PowerShell):**
```powershell
$env:HOST="127.0.0.1"
$env:PORT="3000"
$env:DEBUG="True"
python app.py
```

**Windows (CMD):**
```bat
set HOST=127.0.0.1
set PORT=3000
set DEBUG=True
python app.py
```

## API Endpoints
- `GET /` — service and system information
- `GET /health` — health check

Examples:
```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/health
```

Pretty output:
```bash
curl http://127.0.0.1:5000/ | python -m json.tool
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| HOST     | 0.0.0.0 | Bind address |
| PORT     | 5000    | HTTP port |
| DEBUG    | False   | Flask debug mode |

## Docker

This application can also be built and run as a Docker container.

### Build (local)
Pattern:
```bash
docker build -t <image_name>:<tag> .
```

### Run
Pattern:
```bash
docker run --rm -p <host_port>:5000 --name <container_name> <image_name>:<tag>
```

Then test:
```bash
curl http://127.0.0.1:<host_port>/
curl http://127.0.0.1:<host_port>/health
```

### Pull from Docker Hub
Pattern:
```bash
docker pull <dockerhub_username>/<repo_name>:<tag>
docker run --rm -p <host_port>:5000 <dockerhub_username>/<repo_name>:<tag>
```

> Note (Windows PowerShell): `curl` is an alias for `Invoke-WebRequest`.  
> For classic curl behavior, use `curl.exe`.

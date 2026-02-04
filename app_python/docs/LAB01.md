# LAB01 — DevOps Info Service (Python)

## 1. Framework Selection

**Chosen framework:** Flask

### Why Flask
- **Lightweight and simple**: perfect for a small service with 2 endpoints.
- **Fast to start**: minimal boilerplate, easy routing.
- **Good for DevOps labs**: focus stays on environment/configuration, containerization and CI/CD.

### Comparison

| Framework | Pros | Cons | Decision |
|----------|------|------|----------|
| Flask | Simple, lightweight, flexible | Fewer built-in features than Django/FastAPI | **Chosen** |
| FastAPI | Async support, automatic OpenAPI docs, modern typing | More concepts (Pydantic, async) for beginners | Not chosen |
| Django | Full-featured framework (ORM, admin, auth) | Heavy/overkill for 2 simple endpoints | Not chosen |

## 2. Best Practices Applied

### 2.1 Clean Code Organization
**What:** Logic is separated into small functions: `get_uptime()` and `get_system_info()`.

**Why it matters:** Improves readability, reuse, and makes testing easier (Lab 3).

**Code example:**
```python
START_TIME = datetime.now(timezone.utc)

def get_uptime():
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {"seconds": seconds, "human": f"{hours} hours, {minutes} minutes"}
```

### 2.2 Configuration via Environment Variables
**What:** App settings are controlled by env vars with defaults.

**Why it matters:** Makes the application portable across environments (local, Docker, Kubernetes).

**Code example:**
```python
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
```

### 2.3 Error Handling (JSON Responses)
**What:** Custom JSON handlers for common errors (404, 500).

**Why it matters:** API stays consistent (always JSON), easier monitoring and debugging.

**Code example:**
```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": "Endpoint does not exist"}), 404
```

### 2.4 Logging
**What:** Logging is configured with timestamps and log levels.

**Why it matters:** Logs are essential for troubleshooting, monitoring, and production readiness.

**Code example:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logger.info("Request %s %s from %s", request.method, request.path, request.remote_addr)
```

## 3. API Documentation

> Note: In my local environment I ran the service on port **8080** (via `PORT=8080`).  
> Default port in code is **5000** when `PORT` is not set.

### 3.1 GET /
**Purpose:** Returns service metadata, system information, runtime details, request info, and available endpoints.

**Request example:**
```bash
curl http://127.0.0.1:8080/
```

**Response example (shortened):**
```json
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Flask"
  },
  "system": {
    "hostname": "my-host",
    "platform": "Windows",
    "architecture": "AMD64",
    "cpu_count": 20,
    "python_version": "3.14.0"
  },
  "runtime": {
    "uptime_seconds": 1302,
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "method": "GET",
    "path": "/"
  }
}
```

### 3.2 GET /health
**Purpose:** Health check endpoint for monitoring (used later for Kubernetes probes).

**Request example:**
```bash
curl -i http://127.0.0.1:8080/health
```

**Response example:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T13:41:14.751Z",
  "uptime_seconds": 918
}
```

### 3.3 Testing Commands

**Pretty-printed JSON output:**
```bash
curl -s http://127.0.0.1:8080/ | python -m json.tool
```

## 4. Testing Evidence

Screenshots are included in `app_python/docs/screenshots/`:

- `01-main-endpoint.png` — Main endpoint (`GET /`) showing complete JSON output
- `02-health-check.png` — Health endpoint (`GET /health`) including HTTP 200 status
- `03-formatted-output.png` — Pretty-printed JSON output from terminal (`curl -s ... | python -m json.tool`)

## 5. Challenges & Solutions

**Problem:** On Windows, `python app.py` did not work, while `py app.py` worked.

**Solution:**
- Created and activated a virtual environment using:
  ```bash
  py -m venv venv
  ```
- After activation, `python` points to the venv interpreter.
- Disabled Windows Store Python execution aliases (App Execution Aliases) so `python` runs the correct interpreter.

## 6. GitHub Community

**Why starring repositories matters:** Stars increase visibility of useful projects and are a convenient way to bookmark tools and libraries; they also encourage maintainers.

**Why following developers helps:** Following the professor, TAs, and classmates supports collaboration, helps discover solutions and best practices through activity feeds, and builds a professional network.

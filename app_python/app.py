import json
import logging
import os
import platform
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, g, has_request_context, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from werkzeug.exceptions import HTTPException

SERVICE_NAME = os.getenv("SERVICE_NAME", "devops-info-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
SERVICE_DESCRIPTION = os.getenv("SERVICE_DESCRIPTION", "DevOps course info service")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
START_TIME = datetime.now(timezone.utc)
DEFAULT_VISITS_FILE = "/data/visits"

REQUEST_LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the Flask application",
    ["method", "endpoint", "status_code"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=REQUEST_LATENCY_BUCKETS,
)
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
)
endpoint_calls_total = Counter(
    "devops_info_endpoint_calls_total",
    "Application-specific counter for endpoint usage",
    ["endpoint"],
)
system_info_collection_seconds = Histogram(
    "devops_info_system_collection_seconds",
    "Time spent collecting system information",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1),
)


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON for Loki/Grafana."""

    EXTRA_FIELDS = (
        "event",
        "service",
        "host",
        "port",
        "debug",
        "method",
        "path",
        "endpoint",
        "status_code",
        "client_ip",
        "user_agent",
        "duration_ms",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
        }

        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class VisitCounter:
    """File-backed counter used to persist the number of root endpoint visits."""

    def __init__(self, path_getter):
        self._path_getter = path_getter
        self._lock = threading.Lock()
        self._value = 0
        self.reload()

    def _path(self) -> Path:
        return Path(self._path_getter())

    def _read_from_disk(self) -> int:
        path = self._path()
        try:
            return int(path.read_text(encoding="utf-8").strip() or "0")
        except FileNotFoundError:
            return 0
        except ValueError:
            logger.warning(
                "Visits file contained invalid data, resetting counter to 0",
                extra={
                    "event": "visits.invalid_data",
                    "service": SERVICE_NAME,
                },
            )
            return 0

    def _write_to_disk(self, value: int) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(str(value), encoding="utf-8")
        os.replace(tmp_path, path)

    def reload(self) -> int:
        with self._lock:
            self._value = self._read_from_disk()
            return self._value

    def get_value(self) -> int:
        with self._lock:
            return self._value

    def increment(self) -> int:
        with self._lock:
            self._value += 1
            self._write_to_disk(self._value)
            return self._value



def configure_logging() -> logging.Logger:
    """Configure application logging to stdout in JSON format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.propagate = False
    werkzeug_logger.disabled = True

    return logging.getLogger(SERVICE_NAME)


logger = configure_logging()
app = Flask(__name__)
app.config.setdefault("VISITS_FILE", os.getenv("VISITS_FILE", DEFAULT_VISITS_FILE))


def get_visits_file_path() -> str:
    """Return the configured path to the visits counter file."""
    return app.config.get("VISITS_FILE", DEFAULT_VISITS_FILE)


visit_counter = VisitCounter(get_visits_file_path)


def get_platform_version() -> str:
    """Return a platform version."""
    try:
        if hasattr(platform, "freedesktop_os_release"):
            info = platform.freedesktop_os_release()
            if info.get("PRETTY_NAME"):
                return info["PRETTY_NAME"]
    except Exception:
        pass
    return platform.platform()



def get_uptime() -> dict:
    """Calculate the application's uptime."""
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {
        "seconds": seconds,
        "human": f"{hours} hours, {minutes} minutes",
    }



def get_system_info() -> dict:
    """Collect system information."""
    with system_info_collection_seconds.time():
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": get_platform_version(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "python_version": platform.python_version(),
        }



def get_client_ip() -> str | None:
    """Return the client IP, preferring X-Forwarded-For when present."""
    if not has_request_context():
        return None

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr



def normalize_endpoint() -> str:
    """Return a low-cardinality endpoint label for Prometheus metrics."""
    if not has_request_context():
        return "unknown"
    if request.url_rule and request.url_rule.rule:
        return request.url_rule.rule
    if request.path in {"/", "/health", "/metrics", "/ready", "/visits"}:
        return request.path
    return "unmatched"



def build_request_log_context(status_code: int | None = None) -> dict:
    """Build structured context for request-related logs."""
    context: dict[str, object] = {"event": "http.request", "service": SERVICE_NAME}

    if not has_request_context():
        return context

    context.update(
        {
            "method": request.method,
            "path": request.path,
            "endpoint": request.endpoint,
            "client_ip": get_client_ip(),
            "user_agent": request.headers.get("User-Agent"),
        }
    )

    if status_code is not None:
        context["status_code"] = status_code

    started_at = getattr(g, "request_started_at", None)
    if started_at is not None:
        context["duration_ms"] = round((time.perf_counter() - started_at) * 1000, 2)

    return context



def finalize_request_metrics(status_code: int) -> None:
    """Record Prometheus metrics for the current request exactly once."""
    if not has_request_context() or not getattr(g, "metrics_tracked", False):
        return
    if getattr(g, "metrics_finalized", False):
        return

    duration = time.perf_counter() - g.request_started_at
    endpoint = g.request_metrics_endpoint
    method = request.method

    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
    ).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    endpoint_calls_total.labels(endpoint=endpoint).inc()
    http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
    g.metrics_finalized = True


@app.before_request
def track_request_start() -> None:
    """Store request start time for structured logging and metrics."""
    g.request_started_at = time.perf_counter()
    g.request_metrics_endpoint = normalize_endpoint()
    g.metrics_tracked = True
    g.metrics_finalized = False
    http_requests_in_progress.labels(
        method=request.method,
        endpoint=g.request_metrics_endpoint,
    ).inc()


@app.after_request
def log_response(response):
    """Log every completed HTTP request as JSON and write metrics."""
    finalize_request_metrics(response.status_code)

    level = logging.INFO
    if response.status_code >= 400:
        level = logging.ERROR

    logger.log(
        level,
        "HTTP request completed",
        extra=build_request_log_context(response.status_code),
    )
    return response


@app.teardown_request
def cleanup_request_metrics(exc) -> None:
    """Ensure the in-progress gauge is decremented even on failures."""
    if not has_request_context() or not getattr(g, "metrics_tracked", False):
        return

    if getattr(g, "metrics_finalized", False):
        return

    http_requests_in_progress.labels(
        method=request.method,
        endpoint=g.request_metrics_endpoint,
    ).dec()
    g.metrics_finalized = True


@app.route("/")
def index():
    """Main endpoint - service and system information."""
    current_visits = visit_counter.increment()
    uptime = get_uptime()

    response = {
        "service": {
            "name": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "description": SERVICE_DESCRIPTION,
            "framework": "Flask",
        },
        "system": get_system_info(),
        "runtime": {
            "uptime_seconds": uptime["seconds"],
            "uptime_human": uptime["human"],
            "current_time": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "timezone": "UTC",
        },
        "request": {
            "client_ip": get_client_ip(),
            "user_agent": request.headers.get("User-Agent"),
            "method": request.method,
            "path": request.path,
        },
        "visits": {
            "count": current_visits,
            "storage": get_visits_file_path(),
        },
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Service information"},
            {"path": "/visits", "method": "GET", "description": "Visit counter"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/ready", "method": "GET", "description": "Readiness check"},
            {"path": "/metrics", "method": "GET", "description": "Prometheus metrics"},
        ],
    }

    return jsonify(response)


@app.route("/visits")
def visits():
    """Return the current persisted visit count."""
    return jsonify(
        {
            "visits": visit_counter.get_value(),
            "storage": get_visits_file_path(),
        }
    )


@app.route("/health")
def health():
    """Health check endpoint for monitoring."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "uptime_seconds": get_uptime()["seconds"],
        }
    )


@app.route("/ready")
def ready():
    """Readiness check endpoint for Kubernetes probes."""
    return jsonify(
        {
            "status": "ready",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        }
    )


@app.route("/metrics")
def metrics():
    """Expose Prometheus metrics for scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.errorhandler(404)
def not_found(error):
    return (
        jsonify(
            {
                "error": "Not Found",
                "message": "Endpoint does not exist",
            }
        ),
        404,
    )


@app.errorhandler(405)
def method_not_allowed(error):
    return (
        jsonify(
            {
                "error": "Method Not Allowed",
                "message": "Method is not allowed for this endpoint",
            }
        ),
        405,
    )


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error

    logger.exception(
        "Unhandled application error",
        extra=build_request_log_context(status_code=500),
    )
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            }
        ),
        500,
    )


if __name__ == "__main__":
    visit_counter.reload()
    logger.info(
        "Application startup",
        extra={
            "event": "app.startup",
            "service": SERVICE_NAME,
            "host": HOST,
            "port": PORT,
            "debug": DEBUG,
        },
    )
    app.run(host=HOST, port=PORT, debug=DEBUG)

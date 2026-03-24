import pytest
from app import app as flask_app


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_root_endpoint_returns_200_and_json(client):
    resp = client.get("/", headers={"User-Agent": "pytest"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)

    for key in ["service", "system", "runtime", "request", "endpoints"]:
        assert key in data

    assert data["service"]["name"] == "devops-info-service"
    assert data["service"]["framework"] == "Flask"

    for key in ["hostname", "platform", "architecture", "cpu_count", "python_version"]:
        assert key in data["system"]

    assert "uptime_seconds" in data["runtime"]
    assert isinstance(data["runtime"]["uptime_seconds"], int)

    assert isinstance(data["endpoints"], list)
    assert any(e["path"] == "/" for e in data["endpoints"])
    assert any(e["path"] == "/health" for e in data["endpoints"])
    assert any(e["path"] == "/metrics" for e in data["endpoints"])


def test_health_endpoint_returns_200_and_expected_fields(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], int)


def test_metrics_endpoint_exposes_prometheus_metrics(client):
    client.get("/")
    client.get("/health")
    client.get("/does-not-exist")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    metrics_text = resp.get_data(as_text=True)

    assert "# HELP http_requests_total" in metrics_text
    assert 'http_requests_total{endpoint="/",method="GET",status_code="200"}' in metrics_text
    assert 'http_requests_total{endpoint="/health",method="GET",status_code="200"}' in metrics_text
    assert 'http_requests_total{endpoint="unmatched",method="GET",status_code="404"}' in metrics_text
    assert "# TYPE http_request_duration_seconds histogram" in metrics_text
    assert "http_requests_in_progress" in metrics_text
    assert "devops_info_endpoint_calls_total" in metrics_text
    assert "devops_info_system_collection_seconds" in metrics_text


def test_unknown_endpoint_returns_404_json(client):
    resp = client.get("/no-such-endpoint")
    assert resp.status_code == 404
    data = resp.get_json()

    assert data["error"] == "Not Found"
    assert "message" in data


def test_method_not_allowed_returns_405_json(client):
    resp = client.post("/health")
    assert resp.status_code == 405
    data = resp.get_json()

    assert data["error"] == "Method Not Allowed"
    assert "message" in data

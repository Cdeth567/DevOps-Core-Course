#!/usr/bin/env bash
set -euo pipefail

echo "[info] Loki readiness"
curl -fsS http://localhost:3100/ready

echo "[info] Promtail readiness"
curl -fsS http://localhost:9080/ready

echo "[info] Prometheus health"
curl -fsS http://localhost:9090/-/healthy

echo "[info] Prometheus targets"
curl -fsS http://localhost:9090/api/v1/targets | sed -n '1,40p'

echo "[info] Grafana health"
curl -fsS http://localhost:3000/api/health

echo "[info] Python app health"
curl -fsS http://localhost:8000/health

echo "[info] Python app metrics"
curl -fsS http://localhost:8000/metrics | sed -n '1,40p'

echo "[info] Prometheus up query"
curl -fsS 'http://localhost:9090/api/v1/query?query=up'

echo "[info] Docker Compose status"
docker compose ps

#!/usr/bin/env bash
set -euo pipefail

APP_URL="${APP_URL:-http://localhost:8000}"

echo "[info] Generating successful requests against ${APP_URL}"
for _ in $(seq 1 20); do
  curl -fsS "${APP_URL}/" > /dev/null
  curl -fsS "${APP_URL}/health" > /dev/null
  sleep 0.1
done

echo "[info] Generating client error traffic for ERROR-level log examples"
for _ in $(seq 1 5); do
  curl -s -o /dev/null -w "GET /missing -> %{http_code}\n" "${APP_URL}/missing" || true
  curl -s -X POST -o /dev/null -w "POST /health -> %{http_code}\n" "${APP_URL}/health" || true
  sleep 0.1
done

echo "[ok] Traffic generation completed"

# Lab 07 — Observability & Logging with Loki Stack

## 1. Architecture

This lab deploys a centralized logging stack based on the Grafana Loki ecosystem.

### Components
- **Loki** — stores and indexes logs.
- **Promtail** — discovers Docker containers and ships logs to Loki.
- **Grafana** — visualizes and queries logs with LogQL.
- **Python application** — emits structured JSON logs to stdout.

### Data flow
1. The Python container writes JSON logs to stdout.
2. Docker stores container logs.
3. Promtail discovers running containers through the Docker socket and reads their logs.
4. Promtail pushes log streams to Loki.
5. Grafana connects to Loki as a data source and visualizes logs in Explore and on dashboards.

### Services in the stack
- `loki`
- `promtail`
- `grafana`
- `app-python`

## 2. Setup Guide

### Directory structure
```text
monitoring/
├── docker-compose.yml
├── .env.example
├── loki/
│   └── config.yml
├── promtail/
│   └── config.yml
├── grafana/
│   ├── dashboards/
│   │   └── lab07-observability.json
│   └── provisioning/
│       ├── dashboards/
│       │   └── dashboard.yml
│       └── datasources/
│           └── loki.yml
└── docs/
    ├── LAB07.md
    └── screenshots/
```

### Deployment steps
1. Open the `monitoring` directory.
2. Create a local `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   On Windows PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Set a Grafana admin password in `.env`:
   ```env
   GRAFANA_ADMIN_PASSWORD=your_secure_password
   ```
4. Start the stack:
   ```bash
   docker compose up -d --build
   ```
5. Check service status:
   ```bash
   docker compose ps
   ```
6. Open Grafana:
   - URL: `http://localhost:3000`
   - Username: value from `GF_SECURITY_ADMIN_USER` or default `admin`
   - Password: value from `GRAFANA_ADMIN_PASSWORD`

## 3. Configuration

### Docker Compose
The stack is defined in `monitoring/docker-compose.yml`.

Key implementation details:
- Loki uses image `grafana/loki:3.0.0` and exposes port `3100`.
- Promtail uses image `grafana/promtail:3.0.0` and mounts:
  - `/var/run/docker.sock`
  - Docker log storage
- Grafana uses image `grafana/grafana:12.3.1` and exposes port `3000`.
- All services share the `logging` network.
- Persistent named volumes are used for Loki and Grafana data.
- Health checks are defined for Loki, Grafana, and the Python app.
- Resource limits and reservations are configured for production readiness.

### Loki configuration
File: `monitoring/loki/config.yml`

The Loki configuration includes:
- `auth_enabled: false` for local development.
- HTTP server on port `3100`.
- TSDB storage backend with filesystem storage.
- Schema version `v13`, which is recommended for Loki 3.x.
- Retention period of **7 days** (`168h`).
- Compactor enabled to enforce retention.

Why this configuration was chosen:
- TSDB is the recommended and more efficient index format for Loki 3.0.
- Filesystem storage is sufficient for a single-node lab setup.
- A 7-day retention policy is enough for lab validation while keeping storage bounded.

### Promtail configuration
File: `monitoring/promtail/config.yml`

Promtail is configured to:
- expose its own HTTP endpoint on port `9080`;
- store read offsets in a positions file;
- send logs to `http://loki:3100/loki/api/v1/push`;
- use Docker service discovery via `docker_sd_configs`;
- relabel metadata from Docker into queryable labels such as:
  - `container`
  - `compose_service`
  - `app`
  - `job`
- parse JSON/container log envelopes so logs appear correctly in Loki.

Why this configuration matters:
- Docker service discovery allows Promtail to automatically find running containers.
- Labels make filtering in LogQL much easier.
- Structured labels and parsed JSON logs enable targeted observability use cases.

### Grafana provisioning
Grafana is provisioned automatically with:
- a Loki data source via `grafana/provisioning/datasources/loki.yml`;
- a dashboard provider via `grafana/provisioning/dashboards/dashboard.yml`;
- a prebuilt dashboard file `grafana/dashboards/lab07-observability.json`.

This avoids manual setup after each redeploy.

## 4. Application Logging

The Python application was updated to emit **JSON logs** to stdout.

### Logging requirements implemented
The logs include structured fields such as:
- `timestamp`
- `level`
- `logger`
- `message`
- `service`
- `event`
- `method`
- `path`
- `status_code`
- `client_ip`
- `user_agent`
- `duration_ms`

### Events logged
- application startup;
- successful HTTP requests;
- failed requests, including `404` errors.

### Why JSON logging was used
JSON logs are better for aggregation because they:
- can be parsed automatically;
- support filtering by fields instead of only plain text matching;
- integrate well with Loki and Grafana Explore.

### Example JSON log
```json
{
  "timestamp": "2026-03-11T17:55:15.191Z",
  "level": "ERROR",
  "logger": "devops-info-service",
  "message": "HTTP request completed",
  "service": "devops-info-service",
  "event": "http.request",
  "method": "GET",
  "path": "/not-found",
  "status_code": 404,
  "client_ip": "172.18.0.1",
  "duration_ms": 0.09
}
```

## 5. Dashboard

A Grafana dashboard named **Lab 07 - Loki Observability** was created and provisioned automatically.

### Panels implemented
1. **Logs Table**
   - shows recent logs from all services;
   - based on Loki log streams.

2. **Request Rate by App**
   - time series showing log rate per application;
   - based on `rate()` aggregation grouped by `app`.

3. **Error Logs**
   - displays only logs with error-level data.

4. **Log Level Distribution**
   - shows how log entries are distributed by level.

### Example LogQL queries used
```logql
{job="docker"}
{app="devops-python"}
{app="devops-python"} | json
{app="devops-python"} | json | path="/health"
{app="devops-python"} | json | status_code=404
{app=~"devops-.*"}
sum by (app) (rate({app=~"devops-.*"}[1m]))
sum by (level) (count_over_time({app=~"devops-.*"} | json [5m]))
```

### What was verified in Grafana
- the Loki data source was available and set as default;
- logs were visible from multiple containers;
- JSON fields were extracted and shown in Explore;
- filtering by `path` and `status_code` worked;
- the dashboard displayed real traffic data.

## 6. Production Configuration

Several production-readiness improvements were applied.

### Security
- Anonymous Grafana access was disabled.
- Grafana credentials are supplied through environment variables.
- Secrets are stored in `.env`, which should **not** be committed.

### Resource limits
Resource constraints were configured for the services to avoid uncontrolled resource usage.

Example approach:
```yaml
resources:
  limits:
    cpus: "1.0"
    memory: 1G
  reservations:
    cpus: "0.25"
    memory: 256M
```

### Health checks
Health checks were added for:
- Loki: `http://localhost:3100/ready`
- Grafana: `http://localhost:3000/api/health`
- Python app: `http://localhost:8000/health`

### Retention
Loki retention was set to **7 days**.

This provides a realistic baseline for centralized logging while keeping disk usage under control.

## 7. Testing

### Commands used to validate the stack
```bash
docker compose up -d --build
docker compose ps
docker compose logs app-python
```

### Traffic generation used for testing
PowerShell examples:
```powershell
1..20 | ForEach-Object {
  Invoke-WebRequest http://localhost:8000/ -UseBasicParsing | Out-Null
  Invoke-WebRequest http://localhost:8000/health -UseBasicParsing | Out-Null
}

1..10 | ForEach-Object {
  try {
    Invoke-WebRequest http://localhost:8000/not-found -UseBasicParsing -ErrorAction Stop | Out-Null
  } catch {}
}
```

### Validation results
- all containers started successfully;
- health checks passed;
- JSON logs were produced by `app-python`;
- Grafana showed logs from multiple services;
- Explore queries returned expected results for normal and error traffic.

## 8. Challenges and Solutions

### Challenge 1 — Grafana provisioning directories were missing
At first, Grafana started but did not load the Loki data source or dashboard automatically.

**Cause:**
The provisioning subdirectories and files were missing or empty.

**Solution:**
Created and mounted:
- `grafana/provisioning/datasources/loki.yml`
- `grafana/provisioning/dashboards/dashboard.yml`
- `grafana/dashboards/lab07-observability.json`

### Challenge 2 — Application logs were plain text instead of JSON
Initially the Python app wrote regular text logs, which limited structured querying.

**Solution:**
Updated the logging implementation so the application emits structured JSON logs to stdout.

### Challenge 3 — PowerShell `curl` behavior on Windows
On Windows, `curl` is aliased to `Invoke-WebRequest`, which caused prompts and different behavior.

**Solution:**
Used explicit PowerShell commands with `-UseBasicParsing` for reliable traffic generation.

### Challenge 4 — Filtering logs in Explore
Some filters did not work at first until the JSON parser and labels were confirmed.

**Solution:**
Verified labels and used queries such as:
```logql
{app="devops-python"} | json | status_code=404
```

## 9. Evidence

The following evidence should be attached in `monitoring/docs/screenshots/`:
- `01-datasource-loki.png` — Loki data source page in Grafana.
- `02-dashboard-overview.png` — dashboard with all panels and real data.
- `03-explore-queries.png` — Explore page with LogQL queries.
- `04-explore-results.png` — Explore results with parsed JSON logs.
- `05-json-logs-app-python.png` — terminal output with JSON logs from the app.
- `06-docker-compose-ps.png` — all services running and healthy.

## 10. Conclusion

This lab successfully implemented a centralized logging stack using Loki, Promtail, and Grafana.

The final solution provides:
- centralized collection of container logs;
- structured JSON application logging;
- filtering and analysis through LogQL;
- dashboard-based observability;
- basic production-readiness features such as health checks, retention, and secured Grafana access.

The stack is suitable as a foundation for further observability practices in later DevOps work.

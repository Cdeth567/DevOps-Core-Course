# LAB08 — Metrics & Monitoring with Prometheus

## 1. Architecture

This lab extends the observability stack from Lab 7 by adding metrics collection and visualization.

**Metric flow:**

```text
Python App (/metrics) -> Prometheus -> Grafana
                         ^
                         |
                  Loki / Grafana / Prometheus self-metrics
```

**Components used:**
- **app-python** — Flask-based application exposing `/metrics`
- **Prometheus** — scrapes and stores time-series metrics
- **Grafana** — visualizes metrics through dashboards
- **Loki** — remains part of the observability stack from Lab 7
- **Promtail** — ships logs to Loki

The stack runs in Docker Compose on a shared `logging` network so Prometheus can scrape metrics from all services by service name.

---

## 2. Application Instrumentation

The Python application was instrumented with `prometheus_client` and now exposes metrics at:

```text
http://localhost:8000/metrics
```

### Implemented metric types

#### Counter
Used for counting total HTTP requests handled by the application.

Example metric:
- `http_requests_total`

Why it was added:
- to measure request **rate**
- to split traffic by endpoint, method, and response code
- to support RED-style monitoring

#### Histogram
Used for request latency distribution.

Example metric:
- `http_request_duration_seconds`

Why it was added:
- to measure request **duration**
- to calculate percentiles such as p95
- to build latency graphs and heatmaps

#### Gauge
Used for in-progress requests.

Example metric:
- `http_requests_in_progress`

Why it was added:
- to show current application load
- to visualize active requests in Grafana

### Labels

The application metrics use labels for request dimensions:
- `method`
- `endpoint`
- `status_code` / response status dimension

This makes it possible to filter and aggregate requests by endpoint and status in PromQL.

### Notes

During local verification, the `/metrics` endpoint returned both:
- default Python/process metrics
- custom HTTP application metrics

Observed examples in the output:
- `http_requests_total`
- `http_request_duration_seconds_bucket`
- `http_requests_in_progress`

---

## 3. Prometheus Configuration

Prometheus was added to the Docker Compose stack and configured to scrape all required targets.

### Scrape targets

The following jobs are configured:
- `prometheus`
- `app`
- `loki`
- `grafana`

### Scrape interval

Configured scrape interval:
- `15s`

### Retention

Prometheus retention was configured through container command arguments:

```yaml
command:
  - --config.file=/etc/prometheus/prometheus.yml
  - --storage.tsdb.retention.time=15d
  - --storage.tsdb.retention.size=10GB
```

### Why this configuration is useful

- **15s scrape interval** gives fast enough visibility without excessive load
- **15d retention** keeps enough history for lab analysis
- **10GB size cap** prevents uncontrolled disk growth

### Verification

Prometheus was verified through:
- `/targets` page with all configured jobs shown as **UP**
- PromQL query `up`
- API/UI response showing active targets and successful scraping

---

## 4. Dashboard Walkthrough

A Grafana application dashboard was created/imported and verified with live data.

Dashboard title:
- **Lab 08 - Application Metrics**

### Panels

#### 1. Request Rate by Endpoint
**Purpose:** shows requests per second for each endpoint.

**Query:**
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

#### 2. Error Rate (5xx)
**Purpose:** shows 5xx errors over time.

**Query:**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
```

**Note:** in local testing this panel showed no data because no 5xx errors were generated, which is expected.

#### 3. Request Duration p95
**Purpose:** shows the 95th percentile latency.

**Query:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### 4. Request Duration Heatmap
**Purpose:** visualizes latency distribution over time.

**Query:**
```promql
rate(http_request_duration_seconds_bucket[5m])
```

#### 5. Active Requests
**Purpose:** shows currently active requests.

**Query:**
```promql
http_requests_in_progress
```

#### 6. Status Code Distribution
**Purpose:** shows response code distribution.

**Query:**
```promql
sum by (status) (rate(http_requests_total[5m]))
```

#### 7. Application Uptime
**Purpose:** shows whether the application is up.

**Query:**
```promql
up{job="app"}
```

---

## 5. PromQL Examples

Below are PromQL examples used in this lab.

### 1. Check whether monitored targets are up
```promql
up
```

**Meaning:** returns `1` for healthy targets and `0` for unavailable ones.

### 2. Request rate by endpoint
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

**Meaning:** shows requests per second for each application endpoint.

### 3. Error rate
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
```

**Meaning:** shows server-side error traffic.

### 4. p95 latency
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Meaning:** estimates the 95th percentile of request duration.

### 5. Active requests
```promql
http_requests_in_progress
```

**Meaning:** shows the number of currently processed requests.

### 6. Status code distribution
```promql
sum by (status) (rate(http_requests_total[5m]))
```

**Meaning:** groups request rates by response status.

### 7. Service uptime
```promql
up{job="app"}
```

**Meaning:** shows whether the application target is currently reachable by Prometheus.

### RED method mapping

This dashboard demonstrates the **RED method**:
- **Rate** -> request rate panel
- **Errors** -> error rate panel
- **Duration** -> p95 latency and heatmap

---

## 6. Production Setup

The Docker Compose stack was hardened for production-style usage.

### Health checks

Health checks were configured for key services:
- `app-python`
- `prometheus`
- `grafana`
- `loki`

### Important Windows-related note

During testing on Windows, the original `promtail` health check using `wget` caused startup issues because the image did not include `wget`.

As a workaround:
- the `promtail` health check was removed
- `app-python` dependency on `promtail` was changed from `condition: service_healthy` to a regular dependency

This allowed the stack to start successfully while keeping the rest of the monitoring setup functional.

### Resource limits

Configured limits:
- **Prometheus** — 1G memory, 1 CPU
- **Loki** — 1G memory, 1 CPU
- **Grafana** — 512M memory, 0.5 CPU
- **Application services** — 256M memory, 0.5 CPU

### Retention policy

Prometheus retention:
- **15 days**
- **10GB**

Why retention matters:
- controls disk usage
- improves query performance
- keeps history manageable for monitoring tasks

### Persistent volumes

Persistent volumes are configured for:
- `prometheus-data`
- `loki-data`
- `grafana-data`
- `promtail-positions`

This ensures monitoring state survives container restarts.

---

## 7. Testing Results

The implementation was verified with the following screenshots.

### Screenshots

Stored in:
```text
monitoring/docs/screenshots/
```

Files:
- `01-metrics-endpoint.png`
- `02-prometheus-targets-up.png`
- `03-prometheus-query-up.png`
- `04-docker-compose-ps.png`
- `05-grafana-dashboard-overview.png`
- `06-grafana-dashboard-6-panels.png`
- `07-grafana-persistence-after-restart.png`

### What was verified

#### Metrics endpoint
The application exposed `/metrics` successfully and returned Prometheus-formatted output, including:
- Python runtime metrics
- process metrics
- custom HTTP request metrics

#### Prometheus targets
The `/targets` page showed the following targets as **UP**:
- app
- grafana
- loki
- prometheus

#### PromQL query
The query:

```promql
up
```

returned four active series with value `1`, confirming successful scraping.

#### Docker Compose status
`docker compose ps` showed:
- `app-python` healthy
- `grafana` healthy
- `loki` healthy
- `prometheus` healthy
- `promtail` up

#### Grafana dashboard
The application dashboard displayed:
- 7 panels
- live request and latency data
- status distribution
- uptime
- persistence after restart

#### Persistence
After:

```bash
docker compose down
docker compose up -d
```

the dashboard remained available, confirming that persistent volumes were configured correctly.

---

## 8. Challenges & Solutions

### Challenge 1 — Container name conflicts
**Problem:** old containers such as `loki`, `promtail`, and `app-python` already existed and blocked Compose startup.

**Solution:** old containers were removed before the stack was started again.

---

### Challenge 2 — PowerShell command differences
**Problem:** commands like `head` from bash did not work in PowerShell.

**Solution:** PowerShell-compatible commands were used instead, for example:
```powershell
(curl http://localhost:8000/metrics).Content -split "`n" | Select-Object -First 30
```

---

### Challenge 3 — Promtail unhealthy on Windows
**Problem:** `promtail` became unhealthy because the Docker health check used:

```sh
wget --no-verbose --tries=1 --spider http://localhost:9080/ready
```

but `wget` was not available in the container.

**Solution:** the `promtail` health check was removed and `app-python` dependency was adjusted accordingly.

---

### Challenge 4 — Grafana dashboard import
**Problem:** manual creation of many panels in Grafana was time-consuming.

**Solution:** a ready dashboard JSON was imported and then verified through live data and persistence testing.

---

## 9. Metrics vs Logs (Lab 8 vs Lab 7)

Metrics and logs serve different purposes and should be used together.

### Use metrics when you need:
- trends over time
- alert thresholds
- dashboards
- service-level indicators
- fast aggregation across many events

Examples:
- request rate
- p95 latency
- uptime
- active requests

### Use logs when you need:
- detailed event context
- stack traces
- exact error messages
- request-by-request investigation
- forensic debugging

Examples:
- failed request details
- application exceptions
- deployment troubleshooting

### Practical comparison

- **Metrics answer:** “How many errors per second do we have?”
- **Logs answer:** “What exactly caused this error?”

For real observability, both are necessary:
- metrics detect and summarize problems
- logs explain and debug them

---

## 10. Files Produced

### Documentation
- `monitoring/docs/LAB08.md`

### Dashboard JSON
- `monitoring/grafana/dashboards/lab08-dashboard.json`

### Screenshots
- `monitoring/docs/screenshots/01-metrics-endpoint.png`
- `monitoring/docs/screenshots/02-prometheus-targets-up.png`
- `monitoring/docs/screenshots/03-prometheus-query-up.png`
- `monitoring/docs/screenshots/04-docker-compose-ps.png`
- `monitoring/docs/screenshots/05-grafana-dashboard-overview.png`
- `monitoring/docs/screenshots/06-grafana-dashboard-6-panels.png`
- `monitoring/docs/screenshots/07-grafana-persistence-after-restart.png`

---

## 11. Conclusion

Lab 8 was completed by instrumenting the Python application with Prometheus metrics, deploying Prometheus into the observability stack, visualizing the collected metrics in Grafana, and hardening the stack with health checks, resource limits, retention, and persistent volumes.

The final setup successfully demonstrates:
- application instrumentation with Counter, Gauge, and Histogram
- Prometheus scraping of all required targets
- RED-method dashboards in Grafana
- working persistence after restart
- a complete metrics layer integrated with the Lab 7 logging stack

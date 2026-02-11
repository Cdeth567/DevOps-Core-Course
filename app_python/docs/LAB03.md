# LAB03 — Continuous Integration (CI/CD)

Repository: `Cdeth567/DevOps-Core-Course`  
Branch: `lab03`  
App: `app_python` (DevOps Info Service)

---

## 1. Overview

### 1.1 Testing framework choice
**Framework:** `pytest 8.x`

**Why pytest:**
- Minimal and readable test syntax (simple `assert` statements)
- Great ecosystem and easy CI integration
- Widely used industry standard for Python services

**Dev dependencies file:** `app_python/requirements-dev.txt` (contains `pytest==8.3.4` and `ruff==0.9.6`).

---

### 1.2 What tests cover
Tests are located in: `app_python/tests/test_app.py`

Covered behavior:
- **`GET /`**
  - Returns HTTP 200
  - Returns JSON with expected structure/fields
- **`GET /health`**
  - Returns HTTP 200
  - Returns JSON with `"status": "healthy"` and expected keys
- Includes multiple assertions → not just "smoke tests"

---

### 1.3 CI workflow trigger configuration
Workflow file: `.github/workflows/python-ci.yml`  
Workflow name: **Python CI (tests + docker)**

Triggers:
- **Push** to branches: `master`, `lab03`
- **PRs** targeting `master`
- **Path filters**: runs only if something changed in:
  - `app_python/**`
  - `.github/workflows/python-ci.yml`

Why this matters:
- In monorepos, path filters prevent wasting CI minutes when unrelated files change.
- PR checks still run for code changes that matter.

---

### 1.4 Versioning strategy (Docker images)
**Chosen strategy:** **CalVer** (Calendar Versioning)

Implementation:
- CI generates version on build: `YYYY.MM.DD` (UTC time)

Docker tags produced by CI:
- `cdeth567/devops-info-service:<YYYY.MM.DD>`
- `cdeth567/devops-info-service:latest`

Why CalVer is a good fit here:
- This is a service with frequent small changes.
- It’s easy to understand which build is “today’s”.
- No need to manually manage SemVer releases for a lab service.

---

## 2. Workflow Evidence

### 2.1 Local installation & test evidence (terminal output)

Install dev deps:
```text
py -m pip install -r requirements-dev.txt
Successfully installed ... pytest-8.3.4
```

Install runtime deps:
```text
py -m pip install -r requirements.txt
Successfully installed Flask-3.1.0 ... Werkzeug-3.1.5 ...
```

Run tests (note about Windows PATH):
```text
pytest : The term 'pytest' is not recognized ...
py -m pytest -q
.... [100%]
4 passed in 0.37s
```

**Explanation:** `pytest.exe` was installed into Python Scripts directory not included in PATH. Running `py -m pytest` executes pytest as a module and works reliably on Windows.

---

### 2.2 Linting evidence (ruff)

After installing `ruff` to dev requirements:
```text
py -m pip install -r requirements-dev.txt
Successfully installed ruff-0.9.6
```

Lint run (correct working directory):
```text
py -m ruff check .
All checks passed!
```

Note: The earlier error:
```text
py -m ruff check app_python
app_python:1:1: E902 ... file not found
```
happened because the command was run inside the `app_python/` directory; there is no nested `app_python/app_python` path. Fix was to lint `.`.

---

### 2.3 CI workflow success evidence
GitHub Actions page shows successful runs on `lab03` (green check).  
Badge is green for `lab03` branch.

Workflow URL (Actions):
- `https://github.com/Cdeth567/DevOps-Core-Course/actions/workflows/python-ci.yml`

Status badge in `app_python/README.md`:
```markdown
[![Python CI (tests + docker)](https://github.com/Cdeth567/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg?branch=lab03)](https://github.com/Cdeth567/DevOps-Core-Course/actions/workflows/python-ci.yml)
```

---

### 2.4 Docker Hub evidence
Docker Hub repository:
- `https://hub.docker.com/r/cdeth567/devops-info-service`

CI pushes images with two tags:
- daily CalVer tag (e.g., `2026.02.11` format)
- `latest`

---

## 3. Best Practices Implemented (CI + Security)

### 3.1 Dependency caching (pip)
Implemented using `actions/setup-python@v5` built-in caching:
```yaml
with:
  cache: "pip"
  cache-dependency-path: |
    app_python/requirements.txt
    app_python/requirements-dev.txt
```

Why it matters:
- Cache hits skip downloading packages again
- Faster workflows on repeated runs (especially after first successful run)

How to measure:
- Compare “Install dependencies” step time on first run vs next run
- GitHub Actions logs will show whether cache was restored

---

### 3.2 Matrix builds (multiple Python versions)
Tests run on **Python 3.12 and 3.13** via matrix:
```yaml
matrix:
  python-version: ["3.12", "3.13"]
```

Why it matters:
- Detects version-specific problems early (compatibility across supported versions)
- Good practice for production Python services

---

### 3.3 Fail-fast in matrix
Enabled:
```yaml
fail-fast: true
```

Why it matters:
- Stops wasting CI minutes once a matrix job fails
- Speeds feedback loop (you see failure sooner)

---

### 3.4 Concurrency control
Implemented:
```yaml
concurrency:
  group: python-ci-${{ github.ref }}
  cancel-in-progress: true
```

Why it matters:
- If you push many commits quickly, old runs are canceled
- Avoids queue buildup and wasted CI time

---

### 3.5 Conditional Docker push (protect secrets + reduce risk)
Docker build/push runs only on **push** to `master` or `lab03`:
```yaml
if: github.event_name == 'push' && (github.ref == 'refs/heads/master' || github.ref == 'refs/heads/lab03')
```

Why it matters:
- Prevents Docker pushes from PRs (especially forks)
- Helps avoid leaking secrets in untrusted contexts
- Standard CI/CD safety practice

---

### 3.6 Snyk security scanning
Implemented using **Snyk CLI** in the runner environment:
```yaml
- name: Install Snyk CLI
  run: npm install -g snyk

- name: Snyk scan (dependencies)
  continue-on-error: true
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  run: |
    cd app_python
    snyk test --severity-threshold=high --file=requirements.txt
```

Why it matters:
- Detects known vulnerable dependencies early in pipeline
- Gives visibility into supply-chain security risks

Decision:
- `continue-on-error: true` used so CI doesn’t fully block while still reporting vulnerabilities (appropriate for a lab; in production you might fail builds on high/critical).

---

## 4. Key Decisions

### 4.1 Versioning strategy
**CalVer** used for Docker images (daily tags).  
Rationale: simple automation, no manual release tagging required.

### 4.2 Docker tags produced
- `<username>/devops-info-service:<YYYY.MM.DD>`
- `<username>/devops-info-service:latest`

### 4.3 Workflow triggers
- Push/PR triggers with **path filters** ensure workflow runs only for Python app + workflow changes.

### 4.4 Test coverage
- Endpoints `/` and `/health` are tested via Flask test client (no need to start a real server in CI).  
- Coverage tool (pytest-cov) was **not added** in this submission (bonus task), but tests provide functional coverage for both endpoints.

---

## 5. Challenges & Fixes

### 5.1 `pytest` not recognized on Windows
**Problem:** `pytest` command not found because Python Scripts directory isn’t in PATH.  
**Fix:** Use `py -m pytest` which runs pytest as a module.

### 5.2 `ruff` not recognized / wrong path
**Problem 1:** `ruff` not found → it wasn’t installed yet.  
**Fix:** Added `ruff==0.9.6` to `requirements-dev.txt`.

**Problem 2:** `ruff check app_python` from inside `app_python/` caused file-not-found.  
**Fix:** Run `py -m ruff check .` from the `app_python/` directory.

### 5.3 `.github/workflows` location mistake
Initially workflow file was placed under `app_python/.github/workflows/`, which GitHub Actions does **not** detect.  
Fix: moved workflow to repo root: `.github/workflows/python-ci.yml`.

### 5.4 Snyk scanning issues
There were failures while adjusting working directories.  
Final solution: run Snyk CLI and `cd app_python` before scanning requirements.

---

## 6. Files Changed / Added (Summary)

- `.github/workflows/python-ci.yml` — CI workflow (tests + lint + docker push + Snyk)
- `app_python/tests/test_app.py` — pytest unit tests
- `app_python/requirements-dev.txt` — dev dependencies (`pytest`, `ruff`)
- `app_python/README.md` — added CI status badge + testing instructions
- `app_python/docs/LAB03.md` — this documentation

---

## Appendix — Workflow (reference)
Key jobs:
- `test-and-lint` (matrix: 3.12 + 3.13): install deps, ruff lint, pytest, Snyk scan
- `docker-build-and-push`: build + push to Docker Hub with CalVer + latest

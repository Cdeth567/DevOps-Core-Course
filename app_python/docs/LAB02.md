# LAB02 — Docker Containerization (Python)

## 1. Docker Best Practices Applied

### 1.1 Fixed base image version (pinned tag)
**What I did:** Used `python:3.13-slim` in `Dockerfile`.  
**Why it matters:** A fixed base image version makes builds reproducible and predictable. The `slim` variant reduces image size compared to full images, speeds up pulls/builds, and reduces the attack surface.

**Snippet:**
```dockerfile
FROM python:3.13-slim
```

### 1.2 Non-root user (mandatory)
**What I did:** Created a system user/group `app` and switched to it via `USER app`.  
**Why it matters:** Running as non-root limits privileges inside the container. If the app is compromised, the attacker has fewer permissions, which is a baseline production security practice.

**Snippet:**
```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

### 1.3 Layer caching (dependencies before application code)
**What I did:** Copied `requirements.txt` and installed dependencies **before** copying `app.py`.  
**Why it matters:** Docker caches layers. If only source code changes, the dependency layer stays cached and rebuilds are much faster.

**Snippet:**
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
```

### 1.4 Minimal copy + `.dockerignore`
**What I did:** Copied only runtime-needed files into the image (`requirements.txt`, `app.py`) and used `.dockerignore` to exclude unnecessary files (venv, docs, git, caches).  
**Why it matters:** Smaller build context → faster build. Smaller final image → faster push/pull and reduced risk of leaking development artifacts into production images.

---

## 2. Image Information & Decisions

### 2.1 Base image decision
**Chosen:** `python:3.13-slim`  
**Justification:**
- Modern Python runtime version for container execution
- `slim` gives good balance of small size + compatibility (Debian-based)
- Avoids common issues seen with `alpine` images (musl / Python wheels)

### 2.2 Final image size and assessment
Output:
```text
IMAGE                       ID             DISK USAGE   CONTENT SIZE   EXTRA
devops-info-service:lab02   dc2fdac78d0d        182MB         44.4MB
```

**Assessment:** Content size (~44.4MB) is reasonable for a small Flask app running on Debian-slim. Disk usage is higher due to local storage/overhead, but still acceptable for this lab. Further reductions are possible (e.g., using a production WSGI server, minimizing base layers, or alternative minimal images), but this already follows recommended best practices for beginner containerization.

### 2.3 Layer structure explanation
High-level layers:
1. Base image `python:3.13-slim`
2. Environment variables for predictable Python behavior
3. Create non-root user/group
4. Set working directory
5. Copy and install dependencies (`requirements.txt` → `pip install`)
6. Copy application code (`app.py`)
7. Switch to non-root user
8. Expose port (documentation)
9. Start application with `CMD`

**Evidence (`docker history`):**
```text
IMAGE          CREATED          CREATED BY                                      SIZE      COMMENT
dc2fdac78d0d   47 minutes ago   CMD ["python" "app.py"]                         0B        buildkit.dockerfile.v0
<missing>      47 minutes ago   EXPOSE [5000/tcp]                               0B        buildkit.dockerfile.v0
<missing>      47 minutes ago   USER app                                        0B        buildkit.dockerfile.v0
<missing>      47 minutes ago   COPY app.py . # buildkit                        12.3kB    buildkit.dockerfile.v0
<missing>      47 minutes ago   RUN /bin/sh -c pip install --no-cache-dir -r…   5.53MB    buildkit.dockerfile.v0
<missing>      47 minutes ago   COPY requirements.txt . # buildkit              12.3kB    buildkit.dockerfile.v0
<missing>      47 minutes ago   WORKDIR /app                                    8.19kB    buildkit.dockerfile.v0
<missing>      47 minutes ago   RUN /bin/sh -c addgroup --system app && addu…   45.1kB    buildkit.dockerfile.v0
<missing>      47 minutes ago   ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFER…   0B        buildkit.dockerfile.v0
...
```

### 2.4 Optimization choices
- `python:3.13-slim` for smaller base
- `pip install --no-cache-dir` to avoid storing pip cache inside the image
- Copy only necessary runtime files (no repo-wide `COPY . .`)
- `.dockerignore` reduces build context size and avoids shipping `venv/`, `.git/`, `docs/`, caches

---

## 3. Build & Run Process

### 3.1 Build output
Command:
```bash
docker build -t devops-info-service:lab02 .
```

Terminal output (excerpt):
```text
[+] Building 75.9s (15/15) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load metadata for docker.io/library/python:3.13-slim
 => [internal] load .dockerignore
 => [1/6] FROM docker.io/library/python:3.13-slim@sha256:2b9c9803...
 => [2/6] RUN addgroup --system app && adduser --system --ingroup app app
 => [3/6] WORKDIR /app
 => [4/6] COPY requirements.txt .
 => [5/6] RUN pip install --no-cache-dir -r requirements.txt
 => [6/6] COPY app.py .
 => exporting to image
 => naming to docker.io/library/devops-info-service:lab02
```

### 3.2 Container run output (local image)
Command:
```bash
docker run --rm -p 8080:5000 --name devops-info devops-info-service:lab02
```

Terminal output:
```text
2026-02-04 17:36:37,431 - __main__ - INFO - Starting DevOps Info Service on 0.0.0.0:5000
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.17.0.2:5000
Press CTRL+C to quit
```

**Proof container is running (`docker ps`):**
```text
CONTAINER ID   IMAGE                       COMMAND           CREATED         STATUS         PORTS                                         NAMES
0012d755fc1b   devops-info-service:lab02   "python app.py"   7 seconds ago   Up 6 seconds   0.0.0.0:8080->5000/tcp, [::]:8080->5000/tcp   devops-info
```

### 3.3 Endpoint testing output
Commands:
```bash
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/health
```

Expected results:
- HTTP 200 on both endpoints
- JSON payload returned
- Server header shows Werkzeug + Python 3.13.11 inside container

Example evidence (health):
```text
StatusCode        : 200
StatusDescription : OK
Content           : {"status":"healthy","timestamp":"2026-02-04T17:22:41.912Z","uptime_seconds":68}
Server            : Werkzeug/3.1.5 Python/3.13.11
```

### 3.4 Docker Hub push + pull verification
Login:
```text
docker login
Login Succeeded
```

Tagging strategy:
- `cdeth567/devops-info-service:lab02` — fixed tag for lab submission
- `cdeth567/devops-info-service:latest` — convenience tag for most recent build

Push output:
```text
docker push cdeth567/devops-info-service:lab02
...
lab02: digest: sha256:dc2fdac78d0d5b5e75c3da6a21682aacfdef926ff648356baf54d0437a3d81ec size: 856

docker push cdeth567/devops-info-service:latest
...
latest: digest: sha256:dc2fdac78d0d5b5e75c3da6a21682aacfdef926ff648356baf54d0437a3d81ec size: 856
```

Pull verification:
```text
docker pull cdeth567/devops-info-service:lab02
Status: Image is up to date for cdeth567/devops-info-service:lab02
```

**Docker Hub repository URL:**  
https://hub.docker.com/r/cdeth567/devops-info-service

---

## 4. Technical Analysis

### 4.1 Why does this Dockerfile work the way it does?
- `CMD ["python", "app.py"]` starts the app the same way as local development.
- The app binds to `0.0.0.0` by default (`HOST=0.0.0.0`), so it is reachable from outside the container.
- Port mapping `-p 8080:5000` exposes container port 5000 on host port 8080.
- Dependencies are installed from `requirements.txt` inside the image, making runtime self-contained and portable.

### 4.2 What would happen if I changed the layer order?
If application code was copied before installing dependencies (e.g., `COPY . .` first), then every code change would invalidate the dependency layer cache and force `pip install` to run again. This would slow down rebuilds significantly.

### 4.3 Security considerations implemented
- Non-root execution (`USER app`)
- Slim base image reduces installed packages → smaller attack surface
- `.dockerignore` prevents shipping local artifacts (venv, git metadata, docs) into the container image

### 4.4 How does `.dockerignore` improve the build?
- Reduces build context size → faster builds
- Prevents accidental inclusion of `venv/`, `.git/`, `docs/`, caches
- Lowers risk of leaking local files into the container image

---

## 5. Challenges & Solutions

### 5.1 Port already allocated (8080)
**Issue:** While testing the Docker Hub image, Docker returned:
`Bind for 0.0.0.0:8080 failed: port is already allocated`

**Cause:** Another running container was already mapped to host port 8080.

**Solution:** Stopped the running container (Ctrl+C) or used a different host port mapping (e.g. `-p 8081:5000`).

### 5.2 PowerShell `curl` warning
**Issue:** PowerShell shows a security warning because `curl` is an alias for `Invoke-WebRequest`.  
**Solution:** Confirmed prompt once (“A” = Yes to All) and verified endpoints still return HTTP 200 with JSON.

### 5.3 What I learned
- Dockerfile layer order strongly impacts rebuild speed due to caching.
- Running as non-root is a simple but important security requirement.
- Host port mapping requires a free port; multiple containers cannot bind the same host port simultaneously.
- `.dockerignore` is important both for performance (smaller context) and security (no accidental file leaks).

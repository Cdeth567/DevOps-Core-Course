# syntax=docker/dockerfile:1

FROM python:3.13-slim

# 1) Basic env for predictable Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 2) Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# 3) Workdir
WORKDIR /app

# 4) Install dependencies (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copy only necessary source files
COPY app.py .

# 6) Security: drop privileges
USER app

# 7) Document port (your app uses PORT env, default 5000)
EXPOSE 5000

# 8) Start the app
CMD ["python", "app.py"]

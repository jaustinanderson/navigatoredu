# NavigatorEdu — single-container image (API + static frontend)
FROM python:3.12-slim

# Don't run as root inside the container.
RUN useradd --create-home appuser
WORKDIR /app

# Install dependencies first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application.
COPY backend/ backend/
COPY frontend/ frontend/
COPY data/ data/

# The SQLite file lives in /app/data; compose mounts a volume here so the
# database persists across container restarts. First run auto-seeds it.
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# Honor the platform-injected PORT (e.g. Render) with a local default of
# 8000 — identical behavior locally and in docker compose.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

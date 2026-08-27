# ==============================================================================
# ApexTender v2.0 - Production Multi-Stage Dockerfile (Render Free Tier <512MB)
# ==============================================================================

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-warn-script-location -r requirements.txt

# Final runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH \
    ENVIRONMENT=production \
    PORT=8000 \
    HOST=0.0.0.0

# Create non-root system user for security
RUN groupadd -g 10001 appuser && \
    useradd -u 10000 -g appuser -s /sbin/nologin -m appuser

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appuser app/ ./app/

# Switch to non-root user
USER appuser

# Expose HTTP port
EXPOSE 8000

# Health check probe against Render memory threshold
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Single-worker ASGI configuration to prevent multi-process memory duplication (<120MB RSS)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools", "--no-access-log"]

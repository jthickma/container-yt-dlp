# ============================================
# Media Downloader - Production Docker Image
# ============================================

FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Production Stage
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="Media Downloader"
LABEL org.opencontainers.image.description="Web UI for downloading media using yt-dlp and gallery-dl"

# Install runtime dependencies and gosu
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    tini \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user (IDs will be adjusted by entrypoint)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY --chown=appuser:appgroup app/ app/
COPY --chown=appuser:appgroup scripts/ scripts/

RUN chmod +x /app/scripts/entrypoint.sh && \
    mkdir -p /app/downloads /app/cookies && \
    chown -R appuser:appgroup /app/downloads /app/cookies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DOWNLOAD_DIR=/app/downloads \
    COOKIES_DIR=/app/cookies

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "app:create_app()"]

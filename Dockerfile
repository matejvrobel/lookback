FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Lookback" \
      org.opencontainers.image.description="Self-hosted archive viewer for NVR and security camera recordings" \
      org.opencontainers.image.source="https://github.com/matejvrobel/lookback"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PUID=1000 \
    PGID=1000 \
    LOOKBACK_CONFIG_DIR=/config \
    LOOKBACK_MEDIA_DIR=/recordings \
    LOOKBACK_CACHE_DIR=/cache \
    LOOKBACK_STATIC_DIR=/app/static

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && setpriv --version

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/dist ./static
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN mkdir -p /config /cache /recordings

EXPOSE 8765
VOLUME ["/config", "/cache"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/system/health', timeout=4)"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765", "--proxy-headers", "--forwarded-allow-ips", "*"]

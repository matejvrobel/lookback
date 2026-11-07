FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RV_CONFIG_DIR=/config \
    RV_MEDIA_DIR=/recordings \
    RV_CACHE_DIR=/cache \
    RV_STATIC_DIR=/app/static

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

RUN useradd --uid 1000 --user-group --no-create-home --shell /usr/sbin/nologin recordviewer \
    && mkdir -p /config /cache /recordings \
    && chown recordviewer:recordviewer /config /cache

USER recordviewer
EXPOSE 8765
VOLUME ["/config", "/cache"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/system/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765", "--proxy-headers", "--forwarded-allow-ips", "*"]

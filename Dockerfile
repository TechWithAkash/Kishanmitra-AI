# KisanMitra API (FastAPI + speech, photo and NLP models). Build: docker build -t kisanmitra-api .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_LINK_MODE=copy \
    HF_HOME=/models \
    KISANMITRA_CACHE_DIR=/data

# libgomp: required by onnxruntime / ctranslate2 (faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY kisanmitra ./kisanmitra
COPY data ./data

# Run as an unprivileged user; /models (downloaded AI models) and /data (price cache) are volumes.
RUN useradd --create-home app && mkdir -p /models /data && chown -R app /app /models /data
USER app
VOLUME ["/models", "/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# One worker on purpose: the models are loaded once into memory and requests run in threads.
CMD ["/app/.venv/bin/uvicorn", "kisanmitra.server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

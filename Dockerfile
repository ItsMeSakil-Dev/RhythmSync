# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

LABEL maintainer="@YO_UR_OFFICIAL_CRUSH" \
      org.opencontainers.image.title="RhythmSync" \
      org.opencontainers.image.description="Telegram Music Bot"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Karachi

WORKDIR /app

# ── LAYER 1 — System deps ──
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ── LAYER 2 — Python deps (cached) ──
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# ── LAYER 3 — App code ──
COPY . .

EXPOSE 3000

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["python3", "-m", "RHYTHMSYNC"]

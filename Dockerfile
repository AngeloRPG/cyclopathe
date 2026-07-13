# --- Étape 1 : builder avec dépendances ---
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements.txt

# --- Étape 2 : builder dev (avec tests + Chromium) ---
FROM python:3.12-slim AS dev-builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# Installer dépendances Playwright + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcb1 \
    libxkbcommon0 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-dev.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements-dev.txt \
    && /venv/bin/playwright install chromium

# --- Étape 3 : image production (venv uniquement) ---
FROM python:3.12-slim

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /venv /venv
COPY ./app ./app
COPY ./seed ./seed
COPY .env.example .env.example

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Étape 4 : image tests (avec Playwright + Chromium) ---
FROM dev-builder AS tests

WORKDIR /app
COPY --from=builder /venv /venv
COPY ./app ./app
COPY ./seed ./seed
COPY ./tests ./tests
COPY .env.example .env.example

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["pytest", "tests/", "-v", "--tb=short"]

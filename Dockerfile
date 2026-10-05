# syntax=docker/dockerfile:1

# ---- builder ----------------------------------------------------------------
# Пин по digest (python:3.11-slim-bookworm) для воспроизводимости и безопасности.
FROM python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Отдельный слой под зависимости → кешируется, пока requirements.txt не менялся.
COPY requirements.txt ./
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --upgrade pip setuptools \
    && pip install -r requirements.txt \
    # Триммим вес: байткод, тесты пакетов, C/Cython-исходники в wheels.
    && find "$VIRTUAL_ENV" -type d -name '__pycache__' -prune -exec rm -rf {} + \
    && find "$VIRTUAL_ENV" -type d \( -name tests -o -name test \) -prune -exec rm -rf {} + \
    && find "$VIRTUAL_ENV" -type f \( -name '*.pyc' -o -name '*.pyx' -o -name '*.pyi' \) -delete

# ---- final ------------------------------------------------------------------
FROM python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb AS final

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    TELEMT_BOT_DB_PATH=/data/telemt_bot.db

# Security updates from Debian (libpcre2 and similar).
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Non-root пользователь.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /data /tmp/mpl \
    && chown -R appuser:appuser /data /tmp/mpl

WORKDIR /app

# venv с зависимостями из builder.
COPY --from=builder /opt/venv /opt/venv

# Обновляем системный setuptools (приходит из base image) до версии с пофикшенными
# вендорными wheel и jaraco.context — иначе Trivy находит HIGH CVE в /usr/local.
# pip в рантайме не нужен, а его vendored urllib3 помечается как HIGH.
RUN /usr/local/bin/pip install --upgrade setuptools \
    && rm -rf /usr/local/lib/python3.11/site-packages/pip \
              /usr/local/lib/python3.11/site-packages/pip-*.dist-info \
              /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.11 \
              /opt/venv/lib/python3.11/site-packages/pip \
              /opt/venv/lib/python3.11/site-packages/pip-*.dist-info \
              /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.11

# Только исходники (см. .dockerignore — доки/тесты/секреты не попадают).
COPY --chown=appuser:appuser *.py ./

VOLUME ["/data"]
USER appuser

# Бот — long-polling процесс без HTTP-порта, поэтому health проверяется
# по heartbeat-файлу, который трогает scheduler.py каждые 20с.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD find /tmp/healthy -mmin -1 2>/dev/null | grep -q . || exit 1

ENTRYPOINT ["python", "bot.py"]

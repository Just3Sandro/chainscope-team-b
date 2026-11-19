# Backend ChainScope (issue #4 — socle). Image livrée : python:3.12-slim (D-02).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/chainscope

# Utilisateur non root (spec §8 : surface minimale).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# Dépendances d'abord (couché Docker).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code + migrations.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh ./entrypoint.sh

# Le volume des preuves est monté sur /data/evidence (D-09, compose).
RUN chmod +x entrypoint.sh \
    && mkdir -p /data/evidence \
    && chown -R appuser:appuser /srv/chainscope /data

USER appuser

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

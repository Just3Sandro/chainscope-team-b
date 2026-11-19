#!/bin/sh
# Entrée du conteneur backend (D-16) : migrations d'abord, puis API.
# `set -eu` : toute migration en échec bloque le démarrage (pas de fallback silencieux).
set -eu

echo "[entrypoint] Application des migrations Alembic (upgrade head)..."
alembic upgrade head

echo "[entrypoint] Démarrage de l'API ChainScope sur le port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"

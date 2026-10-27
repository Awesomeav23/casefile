#!/bin/sh
# Start Django for the E2E run on its own database (created if missing).
set -e
PORT="${1:-8020}"
cd "$(dirname "$0")/../../backend"
PY="${PYTHON:-.venv/bin/python}"
export DATABASE_URL="${E2E_DATABASE_URL:-postgres://casefile:casefile_dev_password@localhost:5436/casefile_e2e}"
export SECRET_KEY="${SECRET_KEY:-e2e-only-not-a-real-secret}"
export DEBUG=true
export ALLOWED_HOSTS="localhost,127.0.0.1"
"$PY" ../e2e/scripts/create_db.py
"$PY" manage.py migrate --noinput
exec "$PY" manage.py runserver "$PORT" --noreload

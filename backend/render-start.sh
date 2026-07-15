#!/usr/bin/env sh
set -eu

echo "Sellora backend startup diagnostics"
echo "Render commit: ${RENDER_GIT_COMMIT:-unknown}"
echo "Working directory: $(pwd)"

python scripts/verify_alembic_revision.py
python scripts/verify_sprint_8b_routes.py

echo "Alembic current revision:"
python -m alembic current

echo "Alembic packaged heads:"
python -m alembic heads

echo "Running Alembic migrations..."
python -m alembic upgrade head

echo "Starting Sellora backend..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"

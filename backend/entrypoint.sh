#!/bin/sh

echo "Running database migrations..."
alembic upgrade head || {
    echo "Alembic migrations failed – creating tables directly via SQLAlchemy..."
    python -c "from app.core.database import Base, engine; Base.metadata.create_all(bind=engine)"
}

echo "Starting API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

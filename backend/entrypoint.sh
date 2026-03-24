#!/bin/sh

echo "Running database migrations..."
alembic upgrade head || echo "Alembic migrations had issues, continuing..."

echo "Ensuring all tables exist..."
python -c "
from app.core.database import Base, engine
import app.models.user
import app.models.lead
import app.models.ai_engine
import app.models.engine_message
import app.models.funding
import app.models.research
import app.models.business_idea
import app.models.reward
Base.metadata.create_all(bind=engine)
print('Tables ensured:', list(Base.metadata.tables.keys()))
"

echo "Starting API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

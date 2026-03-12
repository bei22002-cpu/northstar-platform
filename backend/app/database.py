# Re-export from the canonical database module so all routers share one engine.
from app.core.database import Base, engine, SessionLocal, get_db  # noqa: F401

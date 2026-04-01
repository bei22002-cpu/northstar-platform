import os
from dotenv import load_dotenv

load_dotenv()

_raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./northstar.db")
# Render sets DATABASE_URL with postgres:// but SQLAlchemy needs postgresql://
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
DATABASE_URL: str = _raw_db_url
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "change-refresh-in-production")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

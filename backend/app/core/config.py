import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./northstar.db")
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "dev-refresh-secret-change-in-production")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

# Set to "openai" to use LLM-backed generation (requires OPENAI_API_KEY).
# Default is "template" (deterministic, no external dependencies).
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "template")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

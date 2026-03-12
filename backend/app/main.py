from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.api.auth_router import router as auth_router
from app.api.leads_router import router as leads_router
from app.api.outreach_router import router as outreach_router

# Create database tables on startup (SQLite dev default; swap DATABASE_URL for Postgres in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NorthStar Platform API",
    description="AI-powered consulting lead and outreach platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(outreach_router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "NorthStar Platform API"}

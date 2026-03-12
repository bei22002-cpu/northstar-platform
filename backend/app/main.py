from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_router import router as auth_router
from app.api.leads_router import router as leads_router
from app.api.outreach_router import router as outreach_router
from app.core.config import CORS_ORIGINS

app = FastAPI(
    title="NorthStar Consulting AI Platform",
    description="AI-driven consulting platform — Phase 1 (Auth) + Phase 2 (Lead Engine)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(outreach_router)


@app.get("/")
def health_check():
    return {"status": "ok", "platform": "NorthStar"}

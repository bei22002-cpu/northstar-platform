from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_router import router as auth_router
from app.api.leads_router import router as leads_router
from app.api.outreach_router import router as outreach_router
from app.api.ai_engines_router import router as ai_engines_router
from app.api.funding_router import router as funding_router
from app.api.research_router import router as research_router
from app.api.rewards_router import router as rewards_router
from app.api.business_ideas_router import router as business_ideas_router
from app.api.agent_router import router as agent_router
from app.core.config import CORS_ORIGINS

app = FastAPI(
    title="NorthStar Consulting AI Platform",
    description="AI-driven consulting platform with collaborative AI engines, funding management, and business creation tools",
    version="0.4.0",
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
app.include_router(ai_engines_router)
app.include_router(funding_router)
app.include_router(research_router)
app.include_router(rewards_router)
app.include_router(business_ideas_router)
app.include_router(agent_router)


@app.get("/")
def health_check():
    return {"status": "ok", "platform": "NorthStar", "version": "0.4.0"}

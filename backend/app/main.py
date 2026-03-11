from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.api.auth_router import router as auth_router
from app.api.leads_router import router as leads_router
from app.api.outreach_router import router as outreach_router

# Import models so SQLAlchemy picks them up for table creation
import app.models.user  # noqa: F401
import app.models.lead  # noqa: F401
import app.models.outreach  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NorthStar Platform API",
    description="AI-powered lead generation, outreach, and market intelligence platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(outreach_router)


@app.get("/")
def root():
    return {"message": "NorthStar Platform API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}

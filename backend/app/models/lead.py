from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    score = Column(Float, default=0.0)
    classification = Column(String, nullable=True)
    source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

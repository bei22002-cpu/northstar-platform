from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    score = Column(Float, default=0.0)
    classification = Column(String, nullable=True)
    source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

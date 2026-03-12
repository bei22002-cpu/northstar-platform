from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    description = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    status = Column(String, default="new")
    date_discovered = Column(DateTime, server_default=func.now())

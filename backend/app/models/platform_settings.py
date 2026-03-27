"""White-label platform settings."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class PlatformSettings(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, index=True)
    platform_name = Column(String, default="NorthStar")
    tagline = Column(String, default="AI-Powered Consulting Platform")
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    primary_color = Column(String, default="#3182ce")
    accent_color = Column(String, default="#805ad5")
    sidebar_bg = Column(String, default="#1a202c")
    sidebar_text = Column(String, default="#90cdf4")
    custom_css = Column(Text, nullable=True)
    support_email = Column(String, nullable=True)
    enable_marketplace = Column(Boolean, default=True)
    enable_analytics = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

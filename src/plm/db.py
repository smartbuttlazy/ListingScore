"""SQLAlchemy ORM models — optional persistence layer.

These map the domain dataclasses to relational tables.  Use these when
you need a database-backed PLM (dashboard, historical tracking, etc.).
For stateless API-only usage the domain dataclasses in ``plm.models``
are sufficient.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ListingRow(Base):
    __tablename__ = "listings"

    id = Column(String(64), primary_key=True)
    address = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="active")

    list_price = Column(Float, nullable=True)
    original_list_price = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    living_area_sqft = Column(Float, nullable=True)
    lot_size_sqft = Column(Float, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)
    tax_assessed_value = Column(Float, nullable=True)
    hoa_fees = Column(Float, nullable=True)
    stories = Column(Integer, nullable=True)
    garage_spaces = Column(Integer, nullable=True)
    pool = Column(Boolean, nullable=True)
    fireplace = Column(Boolean, nullable=True)

    public_remarks = Column(Text, default="")
    private_remarks = Column(Text, default="")
    virtual_tour_url = Column(String(1024), default="")

    agent_id = Column(String(64), default="")
    brokerage = Column(String(256), default="")
    mls_number = Column(String(64), default="")

    list_date = Column(Date, nullable=True)
    sold_date = Column(Date, nullable=True)
    sold_price = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    photos = relationship("PhotoRow", back_populates="listing", cascade="all, delete-orphan")
    scores = relationship("ScoreRow", back_populates="listing", cascade="all, delete-orphan")
    alerts = relationship("AlertRow", back_populates="listing", cascade="all, delete-orphan")


class PhotoRow(Base):
    __tablename__ = "photos"

    id = Column(String(64), primary_key=True)
    listing_id = Column(String(64), ForeignKey("listings.id"), nullable=False)
    url = Column(String(1024), nullable=False)
    photo_type = Column(String(64), default="")
    ai_quality_score = Column(Float, default=0.0)
    is_ai_generated = Column(Boolean, default=False)
    has_watermark = Column(Boolean, default=False)
    has_people = Column(Boolean, default=False)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)

    listing = relationship("ListingRow", back_populates="photos")


class ScoreRow(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String(64), ForeignKey("listings.id"), nullable=False)
    total_score = Column(Float, nullable=False)
    category = Column(String(32), nullable=False)

    compliance_score = Column(Float, default=0.0)
    photo_score = Column(Float, default=0.0)
    description_score = Column(Float, default=0.0)
    amenity_score = Column(Float, default=0.0)
    price_score = Column(Float, default=0.0)
    engagement_score = Column(Float, default=0.0)
    market_context_score = Column(Float, default=0.0)
    timeliness_score = Column(Float, default=0.0)

    top_issues = Column(Text, default="")  # JSON array string
    computed_at = Column(DateTime, default=func.now())

    listing = relationship("ListingRow", back_populates="scores")


class AlertRow(Base):
    __tablename__ = "alerts"

    id = Column(String(32), primary_key=True)
    listing_id = Column(String(64), ForeignKey("listings.id"), nullable=False)
    alert_type = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime, default=func.now())
    acknowledged = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)

    listing = relationship("ListingRow", back_populates="alerts")


class ViewStatRow(Base):
    __tablename__ = "view_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String(64), ForeignKey("listings.id"), nullable=False)
    stat_date = Column(Date, nullable=False)
    mls_views = Column(Integer, default=0)
    portal_views = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    inquiries = Column(Integer, default=0)


class PriceHistoryRow(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String(64), ForeignKey("listings.id"), nullable=False)
    change_date = Column(Date, nullable=False)
    price = Column(Float, nullable=False)

"""Pydantic schemas for the REST API — request / response models.

These mirror the domain dataclasses but add validation, serialisation,
and OpenAPI doc generation via Pydantic v2.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request payloads
# ---------------------------------------------------------------------------

class GeoLocationIn(BaseModel):
    latitude: float
    longitude: float


class PhotoIn(BaseModel):
    photo_id: str
    url: str
    photo_type: str = ""
    ai_quality_score: float = 0.0
    is_ai_generated: bool = False
    has_watermark: bool = False
    has_people: bool = False
    width: int = 0
    height: int = 0


class PropertyDataIn(BaseModel):
    living_area_sqft: float | None = None
    lot_size_sqft: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    year_built: int | None = None
    tax_assessed_value: float | None = None
    hoa_fees: float | None = None
    stories: int | None = None
    garage_spaces: int | None = None
    pool: bool | None = None
    fireplace: bool | None = None


class PriceHistoryIn(BaseModel):
    date: date
    price: float


class ViewStatsIn(BaseModel):
    date: date
    mls_views: int = 0
    portal_views: int = 0
    shares: int = 0
    saves: int = 0
    inquiries: int = 0


class CompSetIn(BaseModel):
    comp_group_id: str = ""
    listing_ids: list[str] = Field(default_factory=list)
    average_price: float = 0.0
    median_price: float = 0.0
    median_price_per_sqft: float = 0.0
    median_dom: int = 0
    comp_radius_miles: float = 1.0


class ListingIn(BaseModel):
    listing_id: str
    address: str
    status: str = "active"

    list_price: float | None = None
    original_list_price: float | None = None
    geolocation: GeoLocationIn | None = None

    property_data: PropertyDataIn = Field(default_factory=PropertyDataIn)

    public_remarks: str = ""
    private_remarks: str = ""
    amenities: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)

    photos: list[PhotoIn] = Field(default_factory=list)
    virtual_tour_url: str = ""

    agent_id: str = ""
    brokerage: str = ""
    mls_number: str = ""

    list_date: date | None = None
    sold_date: date | None = None
    sold_price: float | None = None

    price_history: list[PriceHistoryIn] = Field(default_factory=list)
    view_stats: list[ViewStatsIn] = Field(default_factory=list)

    extra: dict[str, Any] = Field(default_factory=dict)


class ScoreRequest(BaseModel):
    listing: ListingIn
    comps: CompSetIn | None = None


class ComplianceRequest(BaseModel):
    listing: ListingIn


class RecommendRequest(BaseModel):
    listing: ListingIn
    comps: CompSetIn | None = None


class AlertRequest(BaseModel):
    listing: ListingIn
    comps: CompSetIn | None = None


class TextCheckRequest(BaseModel):
    text: str
    field_name: str = "text"


# ---------------------------------------------------------------------------
# Response payloads
# ---------------------------------------------------------------------------

class SubScoreOut(BaseModel):
    name: str
    score: float
    max_score: float
    weight: float
    details: str


class ListingScoreOut(BaseModel):
    listing_id: str
    total_score: float
    category: str
    sub_scores: list[SubScoreOut]
    top_issues: list[str]
    computed_at: datetime


class ViolationOut(BaseModel):
    rule_id: str
    severity: str
    field: str
    message: str
    suggestion: str
    matched_text: str


class ComplianceReportOut(BaseModel):
    listing_id: str
    passed: bool
    violations: list[ViolationOut]
    checked_at: datetime


class RecommendationOut(BaseModel):
    listing_id: str
    action_type: str
    priority: str
    title: str
    message: str
    data: dict[str, Any]


class AlertOut(BaseModel):
    alert_id: str
    listing_id: str
    alert_type: str
    severity: str
    message: str
    triggered_at: datetime
    acknowledged: bool
    resolved: bool

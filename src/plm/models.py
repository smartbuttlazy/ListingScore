"""Domain models — pure Python dataclasses used across all PLM sub-systems.

These are *not* ORM models; they are lightweight transport objects that make it
easy to integrate PLM into any stack (Django, Flask, FastAPI, plain scripts).
An optional SQLAlchemy mapping layer lives in ``plm.db``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ListingStatus(str, enum.Enum):
    COMING_SOON = "coming_soon"
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, enum.Enum):
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    MARKET = "market"
    SYSTEM = "system"


class ScoreCategory(str, enum.Enum):
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"            # 75-89
    FAIR = "fair"            # 50-74
    POOR = "poor"            # < 50


class RecommendationPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Listing & Related
# ---------------------------------------------------------------------------

@dataclass
class GeoLocation:
    latitude: float
    longitude: float


@dataclass
class Photo:
    photo_id: str
    url: str
    photo_type: str = ""          # "exterior_front", "interior", "aerial", etc.
    ai_quality_score: float = 0.0  # 0-1
    is_ai_generated: bool = False
    has_watermark: bool = False
    has_people: bool = False
    width: int = 0
    height: int = 0


@dataclass
class PriceHistoryEntry:
    date: date
    price: float


@dataclass
class ViewStats:
    date: date
    mls_views: int = 0
    portal_views: int = 0
    shares: int = 0
    saves: int = 0
    inquiries: int = 0


@dataclass
class ShowingStats:
    date: date
    appointment_count: int = 0
    open_house_count: int = 0


@dataclass
class PropertyData:
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


@dataclass
class Listing:
    """Core listing representation consumed by every PLM sub-system."""

    listing_id: str
    address: str
    status: ListingStatus = ListingStatus.ACTIVE

    list_price: float | None = None
    original_list_price: float | None = None
    geolocation: GeoLocation | None = None

    property_data: PropertyData = field(default_factory=PropertyData)

    # Text
    public_remarks: str = ""
    private_remarks: str = ""
    amenities: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)

    # Media
    photos: list[Photo] = field(default_factory=list)
    virtual_tour_url: str = ""

    # Agent / ownership
    agent_id: str = ""
    brokerage: str = ""
    mls_number: str = ""

    # Dates
    list_date: date | None = None
    last_updated: datetime | None = None
    sold_date: date | None = None
    sold_price: float | None = None

    # Analytics
    price_history: list[PriceHistoryEntry] = field(default_factory=list)
    view_stats: list[ViewStats] = field(default_factory=list)
    showing_stats: list[ShowingStats] = field(default_factory=list)

    # Extra fields an MLS may provide (catch-all)
    extra: dict[str, Any] = field(default_factory=dict)

    # Computed
    @property
    def days_on_market(self) -> int:
        if self.list_date is None:
            return 0
        end = self.sold_date or date.today()
        return max(0, (end - self.list_date).days)

    @property
    def photo_count(self) -> int:
        return len(self.photos)

    @property
    def has_front_exterior_photo(self) -> bool:
        return any(p.photo_type == "exterior_front" for p in self.photos)

    @property
    def recent_weekly_views(self) -> int:
        if not self.view_stats:
            return 0
        latest = sorted(self.view_stats, key=lambda v: v.date, reverse=True)[:7]
        return sum(v.mls_views + v.portal_views for v in latest)

    @property
    def recent_weekly_leads(self) -> int:
        if not self.view_stats:
            return 0
        latest = sorted(self.view_stats, key=lambda v: v.date, reverse=True)[:7]
        return sum(v.inquiries for v in latest)


# ---------------------------------------------------------------------------
# Comp Data
# ---------------------------------------------------------------------------

@dataclass
class CompSet:
    """Comparable sales / active listings for a neighbourhood."""

    comp_group_id: str = ""
    listing_ids: list[str] = field(default_factory=list)
    average_price: float = 0.0
    median_price: float = 0.0
    median_price_per_sqft: float = 0.0
    median_dom: int = 0
    comp_radius_miles: float = 1.0


# ---------------------------------------------------------------------------
# Scoring results
# ---------------------------------------------------------------------------

@dataclass
class SubScore:
    name: str
    score: float          # 0-100 normalised within its own weight
    max_score: float
    weight: float         # 0-1, contribution to total
    details: str = ""     # human-readable explanation


@dataclass
class ListingScore:
    listing_id: str
    total_score: float
    category: ScoreCategory
    sub_scores: list[SubScore] = field(default_factory=list)
    top_issues: list[str] = field(default_factory=list)  # top 3 downgrades
    computed_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Compliance results
# ---------------------------------------------------------------------------

@dataclass
class ComplianceViolation:
    rule_id: str
    severity: AlertSeverity
    field: str            # which listing field triggered it
    message: str
    suggestion: str = ""
    matched_text: str = ""


@dataclass
class ComplianceReport:
    listing_id: str
    passed: bool
    violations: list[ComplianceViolation] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    listing_id: str
    action_type: str       # e.g. "add_photo", "edit_remarks", "adjust_price"
    priority: RecommendationPriority
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    alert_id: str
    listing_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    resolved: bool = False

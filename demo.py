"""PLM Demo — exercises all subsystems with realistic listing data."""

from datetime import date, timedelta
from plm.models import (
    Listing, ListingStatus, Photo, PropertyData,
    CompSet, ViewStats, PriceHistoryEntry, GeoLocation,
)
from plm.compliance import ComplianceChecker
from plm.scoring import ScoringEngine
from plm.recommendations import RecommendationEngine
from plm.monitoring import AlertManager
from plm.config import PLMConfig

# ── Helpers ──────────────────────────────────────────────────────────
def header(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def sub(title: str) -> None:
    print(f"\n--- {title} ---")

today = date.today()
config = PLMConfig()

# ── Listing A: Well-optimised listing ────────────────────────────────
listing_a = Listing(
    listing_id="LST-2024-001",
    address="742 Evergreen Terrace, Springfield, IL 62704",
    status=ListingStatus.ACTIVE,
    list_price=525_000,
    original_list_price=525_000,
    geolocation=GeoLocation(39.7817, -89.6501),
    property_data=PropertyData(
        living_area_sqft=2400, lot_size_sqft=8000,
        bedrooms=4, bathrooms=3.0, year_built=2015,
        tax_assessed_value=510_000, garage_spaces=2,
        pool=True, fireplace=True,
    ),
    public_remarks=(
        "Stunning 4-bedroom home with luxurious upgrades throughout. "
        "Gourmet kitchen featuring granite countertops, stainless steel "
        "appliances, and a large island. Hardwood floors on the main level. "
        "Spa-like primary bath with soaking tub and walk-in shower. "
        "Beautifully landscaped backyard with sparkling pool and covered "
        "patio — perfect for entertaining. Newer HVAC, upgraded electrical, "
        "and energy-efficient windows. Two-car garage with epoxy floors."
    ),
    amenities=["pool", "garage", "fireplace", "central_air", "central_heat",
               "hardwood_floors", "patio", "fenced_yard", "sprinkler", "security_system"],
    features=["granite countertops", "stainless appliances", "soaking tub",
              "walk-in shower", "energy-efficient windows"],
    photos=[
        Photo(photo_id=f"a-{i}", url=f"https://photos.example.com/lst001/{i}.jpg",
              photo_type="exterior_front" if i == 0 else ("interior" if i < 20 else "exterior"),
              ai_quality_score=0.88)
        for i in range(25)
    ],
    agent_id="AGT-SMITH-42",
    mls_number="MLS-SPR-12345",
    list_date=today - timedelta(days=12),
    view_stats=[
        ViewStats(date=today - timedelta(days=d), mls_views=35, portal_views=60, shares=5, saves=8, inquiries=4)
        for d in range(7)
    ],
)

# ── Listing B: Problematic listing ───────────────────────────────────
listing_b = Listing(
    listing_id="LST-2024-002",
    address="1600 Pennsylvania Ave NW, Washington, DC 20500",
    status=ListingStatus.ACTIVE,
    list_price=750_000,
    original_list_price=800_000,
    property_data=PropertyData(
        bedrooms=3, bathrooms=2.0, living_area_sqft=1800,
    ),
    public_remarks=(
        "Cozy home in a family-friendly neighborhood near church. "
        "Great for young couples! Features a master bedroom suite. "
        "Call me at 202-555-0199 for a private showing. "
        "Check out www.myagentsite.com/listing for virtual tour."
    ),
    amenities=[],
    features=[],
    photos=[
        Photo(photo_id="b-0", url="https://photos.example.com/lst002/0.jpg",
              photo_type="interior", ai_quality_score=0.3),
        Photo(photo_id="b-1", url="https://photos.example.com/lst002/1.jpg",
              photo_type="interior", has_watermark=True, ai_quality_score=0.5),
    ],
    agent_id="AGT-DOE-99",
    mls_number="MLS-DC-67890",
    list_date=today - timedelta(days=75),
    price_history=[
        PriceHistoryEntry(date=today - timedelta(days=75), price=800_000),
        PriceHistoryEntry(date=today - timedelta(days=40), price=750_000),
    ],
    view_stats=[
        ViewStats(date=today - timedelta(days=d), mls_views=2, portal_views=3, inquiries=0)
        for d in range(7)
    ],
)

# ── Comps ────────────────────────────────────────────────────────────
comps_a = CompSet(
    comp_group_id="COMP-SPR", median_price=520_000,
    average_price=530_000, median_price_per_sqft=220, median_dom=22,
)
comps_b = CompSet(
    comp_group_id="COMP-DC", median_price=550_000,
    average_price=560_000, median_price_per_sqft=305, median_dom=18,
)

# ── Instantiate engines ─────────────────────────────────────────────
compliance = ComplianceChecker(config)
scorer = ScoringEngine(config)
recommender = RecommendationEngine(config)
alerts = AlertManager(config)

# =====================================================================
#  DEMO: LISTING A — the good one
# =====================================================================
header("LISTING A: 742 Evergreen Terrace (well-optimised)")

sub("Compliance Check")
report_a = compliance.check(listing_a)
print(f"  Passed: {report_a.passed}")
print(f"  Violations: {len(report_a.violations)}")

sub("Quality Score")
score_a = scorer.score(listing_a, comps_a)
print(f"  Total Score:  {score_a.total_score}/100  [{score_a.category.value.upper()}]")
print(f"  Sub-scores:")
for s in score_a.sub_scores:
    bar = "█" * int(s.score / 5) + "░" * (20 - int(s.score / 5))
    print(f"    {s.name:<18} {bar} {s.score:5.1f}/100 (w={s.weight:.0%})  {s.details}")
if score_a.top_issues:
    print(f"  Top issues:")
    for issue in score_a.top_issues:
        print(f"    ⚠ {issue}")
else:
    print(f"  No significant issues detected.")

sub("Recommendations")
recs_a = recommender.recommend(listing_a, comps_a)
if recs_a:
    for r in recs_a:
        print(f"  [{r.priority.value.upper():6}] {r.title}")
        print(f"          {r.message[:100]}...")
else:
    print("  No action items — listing is well optimised!")

sub("Alerts")
alerts_a = alerts.evaluate(listing_a, comps_a)
if alerts_a:
    for a in alerts_a:
        print(f"  [{a.severity.value.upper():8}] {a.message}")
else:
    print("  No alerts triggered.")

# =====================================================================
#  DEMO: LISTING B — the problematic one
# =====================================================================
header("LISTING B: 1600 Pennsylvania Ave (needs work)")

sub("Compliance Check")
report_b = compliance.check(listing_b)
print(f"  Passed: {report_b.passed}")
print(f"  Violations: {len(report_b.violations)}")
for v in report_b.violations:
    icon = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🔵"}.get(v.severity.value, "⚪")
    print(f"    {icon} [{v.severity.value.upper():8}] {v.rule_id}")
    print(f"       {v.message}")
    if v.suggestion:
        print(f"       → {v.suggestion}")

sub("Quality Score")
score_b = scorer.score(listing_b, comps_b)
print(f"  Total Score:  {score_b.total_score}/100  [{score_b.category.value.upper()}]")
print(f"  Sub-scores:")
for s in score_b.sub_scores:
    bar = "█" * int(s.score / 5) + "░" * (20 - int(s.score / 5))
    print(f"    {s.name:<18} {bar} {s.score:5.1f}/100 (w={s.weight:.0%})  {s.details}")
print(f"  Top issues:")
for issue in score_b.top_issues:
    print(f"    ⚠ {issue}")

sub("Recommendations")
recs_b = recommender.recommend(listing_b, comps_b)
for i, r in enumerate(recs_b, 1):
    print(f"  {i}. [{r.priority.value.upper():6}] {r.title}")
    print(f"     {r.message}")
    print()

sub("Alerts")
alerts_b = alerts.evaluate(listing_b, comps_b)
for a in alerts_b:
    icon = {"critical": "🚨", "high": "🔴", "medium": "🟡"}.get(a.severity.value, "⚪")
    print(f"  {icon} [{a.alert_type.value.upper():12}] {a.message}")

# =====================================================================
#  DEMO: Quick text check (no full listing needed)
# =====================================================================
header("QUICK TEXT CHECK — Fair Housing scanner")
from plm.compliance.fair_housing import FairHousingChecker
fh = FairHousingChecker.default()

samples = [
    "Charming 3-bed home with updated kitchen and large backyard.",
    "Perfect for young couple, walking distance to church.",
    "Beautiful master bedroom suite in an adult-only community.",
    "Spacious primary suite with soaking tub and walk-in closet.",
]

for text in samples:
    violations = fh.scan_text(text)
    status = "PASS ✅" if not violations else f"FAIL ❌ ({len(violations)} issue(s))"
    print(f"\n  \"{text}\"")
    print(f"  → {status}")
    for v in violations:
        print(f"    • {v.matched_text} — {v.suggestion}")

print(f"\n{'='*70}")
print("  Demo complete.")
print(f"{'='*70}\n")

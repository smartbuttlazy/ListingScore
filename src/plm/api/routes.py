"""FastAPI route definitions.

All endpoints are stateless: they accept a listing payload, run the
relevant engine, and return results.  This makes integration trivial —
you can call these endpoints from any CRM, MLS frontend, or script.
"""

from __future__ import annotations

from fastapi import APIRouter

from plm.compliance import ComplianceChecker, FairHousingChecker
from plm.config import PLMConfig
from plm.monitoring import AlertManager
from plm.recommendations import RecommendationEngine
from plm.scoring import ScoringEngine

from .converters import compset_from_api, listing_from_api
from .schemas import (
    AlertOut,
    AlertRequest,
    ComplianceReportOut,
    ComplianceRequest,
    ListingScoreOut,
    RecommendRequest,
    RecommendationOut,
    ScoreRequest,
    SubScoreOut,
    TextCheckRequest,
    ViolationOut,
)

router = APIRouter()

# Singletons (stateless, safe to share)
_config = PLMConfig()
_scorer = ScoringEngine(_config)
_compliance = ComplianceChecker(_config)
_recommender = RecommendationEngine(_config)
_alerts = AlertManager(_config)
_fair_housing = FairHousingChecker.default()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

@router.post("/score", response_model=ListingScoreOut)
def score_listing(body: ScoreRequest) -> ListingScoreOut:
    listing = listing_from_api(body.listing)
    comps = compset_from_api(body.comps)
    result = _scorer.score(listing, comps)
    return ListingScoreOut(
        listing_id=result.listing_id,
        total_score=result.total_score,
        category=result.category.value,
        sub_scores=[
            SubScoreOut(
                name=s.name, score=round(s.score, 2),
                max_score=s.max_score, weight=s.weight, details=s.details,
            )
            for s in result.sub_scores
        ],
        top_issues=result.top_issues,
        computed_at=result.computed_at,
    )


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

@router.post("/compliance", response_model=ComplianceReportOut)
def check_compliance(body: ComplianceRequest) -> ComplianceReportOut:
    listing = listing_from_api(body.listing)
    report = _compliance.check(listing)
    return ComplianceReportOut(
        listing_id=report.listing_id,
        passed=report.passed,
        violations=[
            ViolationOut(
                rule_id=v.rule_id, severity=v.severity.value,
                field=v.field, message=v.message,
                suggestion=v.suggestion, matched_text=v.matched_text,
            )
            for v in report.violations
        ],
        checked_at=report.checked_at,
    )


# ---------------------------------------------------------------------------
# Text check (lightweight — no full listing needed)
# ---------------------------------------------------------------------------

@router.post("/compliance/text", response_model=list[ViolationOut])
def check_text(body: TextCheckRequest) -> list[ViolationOut]:
    violations = _fair_housing.scan_text(body.text, body.field_name)
    return [
        ViolationOut(
            rule_id=v.rule_id, severity=v.severity.value,
            field=v.field, message=v.message,
            suggestion=v.suggestion, matched_text=v.matched_text,
        )
        for v in violations
    ]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.post("/recommend", response_model=list[RecommendationOut])
def get_recommendations(body: RecommendRequest) -> list[RecommendationOut]:
    listing = listing_from_api(body.listing)
    comps = compset_from_api(body.comps)
    recs = _recommender.recommend(listing, comps)
    return [
        RecommendationOut(
            listing_id=r.listing_id, action_type=r.action_type,
            priority=r.priority.value, title=r.title,
            message=r.message, data=r.data,
        )
        for r in recs
    ]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.post("/alerts", response_model=list[AlertOut])
def evaluate_alerts(body: AlertRequest) -> list[AlertOut]:
    listing = listing_from_api(body.listing)
    comps = compset_from_api(body.comps)
    alerts = _alerts.evaluate(listing, comps)
    return [
        AlertOut(
            alert_id=a.alert_id, listing_id=a.listing_id,
            alert_type=a.alert_type.value, severity=a.severity.value,
            message=a.message, triggered_at=a.triggered_at,
            acknowledged=a.acknowledged, resolved=a.resolved,
        )
        for a in alerts
    ]

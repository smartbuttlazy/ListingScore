"""Recommendation engine — turns score diagnostics and compliance results
into prioritised, actionable suggestions with templated messages.

Each rule is a small function that inspects the listing, its score, comps,
and compliance report, then yields zero or more ``Recommendation`` objects.
"""

from __future__ import annotations

from typing import Callable, Sequence

from plm.compliance.checker import ComplianceChecker
from plm.config import PLMConfig
from plm.models import (
    AlertSeverity,
    ComplianceReport,
    CompSet,
    Listing,
    ListingScore,
    Recommendation,
    RecommendationPriority,
)
from plm.scoring.engine import ScoringEngine


# Type alias for a rule function
RuleFn = Callable[
    [Listing, ListingScore, ComplianceReport, CompSet | None, PLMConfig],
    list[Recommendation],
]


# ---------------------------------------------------------------------------
# Built-in recommendation rules
# ---------------------------------------------------------------------------

def _rule_missing_front_photo(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    if not listing.has_front_exterior_photo:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="add_photo",
            priority=RecommendationPriority.HIGH,
            title="Add front exterior photo",
            message=(
                "Add a high-quality front exterior photo (required by MLS) "
                "within 24h to meet compliance and attract views."
            ),
        )]
    return []


def _rule_too_few_photos(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    if listing.photo_count < 9:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="add_photos",
            priority=RecommendationPriority.HIGH,
            title="Add more property photos",
            message=(
                f"This listing has only {listing.photo_count} photo(s). "
                "Homes with fewer than 9 images sell ~20% slower. "
                "Aim for 20-25 quality photos to maximise buyer interest."
            ),
            data={"current_count": listing.photo_count, "target": 20},
        )]
    if listing.photo_count < 20:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="add_photos",
            priority=RecommendationPriority.MEDIUM,
            title="Consider additional photos",
            message=(
                f"You have {listing.photo_count} photos — good, but studies show "
                "22-27 photos is optimal. Adding more can boost engagement."
            ),
            data={"current_count": listing.photo_count, "target": 25},
        )]
    return []


def _rule_overpriced(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    if listing.list_price is None or comps is None or comps.median_price <= 0:
        return []
    deviation = (listing.list_price - comps.median_price) / comps.median_price
    if deviation > 0.10:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="adjust_price",
            priority=RecommendationPriority.HIGH,
            title="Consider price adjustment",
            message=(
                f"Your listing is priced ~{deviation:.0%} above recent comps "
                f"(median ${comps.median_price:,.0f}). Consider a reduction or "
                "highlighting unique value. Overpriced homes stay longer on market."
            ),
            data={"deviation_pct": round(deviation * 100, 1), "comp_median": comps.median_price},
        )]
    return []


def _rule_price_drop_no_recovery(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    if len(listing.price_history) >= 2 and listing.recent_weekly_views < 20:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="refresh_marketing",
            priority=RecommendationPriority.MEDIUM,
            title="Re-evaluate marketing after price drop",
            message=(
                "After the last price drop, views did not pick up significantly. "
                "Consider a new open house, fresh photos, or expanded ads to re-engage buyers."
            ),
        )]
    return []


def _rule_stale_listing(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    threshold = config.alert_thresholds
    market_median = comps.median_dom if comps else 30
    if listing.days_on_market > market_median * threshold.high_dom_multiplier:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="refresh_strategy",
            priority=RecommendationPriority.HIGH,
            title="Listing is stale — refresh strategy",
            message=(
                f"This listing has been active {listing.days_on_market} days with "
                "below-average engagement. Consider a virtual tour, new staging photos, "
                "or expanded ads to reignite interest."
            ),
            data={"dom": listing.days_on_market, "market_median_dom": market_median},
        )]
    return []


def _rule_no_description(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    words = len(listing.public_remarks.split()) if listing.public_remarks else 0
    if words < config.description_thresholds.min_word_count:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="edit_remarks",
            priority=RecommendationPriority.HIGH,
            title="Write a compelling property description",
            message=(
                f"Your listing description is only {words} words. "
                f"Aim for at least {config.description_thresholds.optimal_word_count} words "
                "with specific details about upgrades, layout, and neighbourhood highlights."
            ),
            data={"word_count": words},
        )]
    return []


def _rule_missing_amenity(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    pd = listing.property_data
    tags_lower = set(a.lower().replace(" ", "_") for a in listing.amenities + listing.features)

    # Check pool from property data vs tags
    if pd.pool and "pool" not in tags_lower:
        recs.append(Recommendation(
            listing_id=listing.listing_id,
            action_type="add_amenity",
            priority=RecommendationPriority.MEDIUM,
            title="Add pool to amenities",
            message=(
                "This property appears to have a pool (per property data) but it's "
                "not listed as an amenity. Add it to improve search visibility."
            ),
        ))
    if pd.garage_spaces and pd.garage_spaces > 0 and "garage" not in tags_lower:
        recs.append(Recommendation(
            listing_id=listing.listing_id,
            action_type="add_amenity",
            priority=RecommendationPriority.MEDIUM,
            title="Add garage to amenities",
            message=(
                f"This property has {pd.garage_spaces} garage space(s) per records but "
                "garage isn't listed in amenities. Add it to match buyer search filters."
            ),
        ))
    return recs


def _rule_fair_housing_fix(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for v in report.violations:
        if v.rule_id.startswith("FH_"):
            recs.append(Recommendation(
                listing_id=listing.listing_id,
                action_type="edit_remarks",
                priority=RecommendationPriority.HIGH,
                title="Fix Fair Housing violation",
                message=f"{v.message}. {v.suggestion}",
                data={"violation_rule": v.rule_id, "matched": v.matched_text},
            ))
    return recs


def _rule_compliance_fix(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for v in report.violations:
        if v.rule_id.startswith("FH_"):
            continue  # handled by fair housing rule above
        if v.severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
            recs.append(Recommendation(
                listing_id=listing.listing_id,
                action_type="fix_compliance",
                priority=RecommendationPriority.HIGH,
                title=f"Fix: {v.message[:60]}",
                message=f"{v.message} {v.suggestion}",
                data={"violation_rule": v.rule_id, "field": v.field},
            ))
    return recs


def _rule_high_engagement(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    if listing.recent_weekly_leads >= 5:
        return [Recommendation(
            listing_id=listing.listing_id,
            action_type="capitalize_engagement",
            priority=RecommendationPriority.LOW,
            title="Strong interest — follow up promptly",
            message=(
                f"Great news — you've received {listing.recent_weekly_leads} inquiries "
                "this week. Follow up promptly to set showings; consider sending "
                "sellers a positive performance report."
            ),
        )]
    return []


def _rule_ai_photo_label(
    listing: Listing, score: ListingScore, report: ComplianceReport,
    comps: CompSet | None, config: PLMConfig,
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for v in report.violations:
        if v.rule_id == "PHOTO_AI_LABEL":
            recs.append(Recommendation(
                listing_id=listing.listing_id,
                action_type="label_ai_photo",
                priority=RecommendationPriority.HIGH,
                title="Label AI-altered image",
                message=(
                    "You've used an AI-altered image. Per applicable law, mark it "
                    "'Digitally Altered' and include the original photo to comply."
                ),
            ))
    return recs


# ---------------------------------------------------------------------------
# All built-in rules
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[RuleFn] = [
    _rule_missing_front_photo,
    _rule_too_few_photos,
    _rule_overpriced,
    _rule_price_drop_no_recovery,
    _rule_stale_listing,
    _rule_no_description,
    _rule_missing_amenity,
    _rule_fair_housing_fix,
    _rule_compliance_fix,
    _rule_high_engagement,
    _rule_ai_photo_label,
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """Generate prioritised recommendations for a listing.

    Usage::

        engine = RecommendationEngine()
        recs = engine.recommend(listing, comps=comp_set)
    """

    def __init__(
        self,
        config: PLMConfig | None = None,
        rules: list[RuleFn] | None = None,
    ) -> None:
        self.config = config or PLMConfig()
        self.rules = rules if rules is not None else list(DEFAULT_RULES)
        self._scorer = ScoringEngine(self.config)
        self._compliance = ComplianceChecker(self.config)

    def recommend(
        self,
        listing: Listing,
        comps: CompSet | None = None,
    ) -> list[Recommendation]:
        score = self._scorer.score(listing, comps)
        report = self._compliance.check(listing)

        all_recs: list[Recommendation] = []
        for rule in self.rules:
            all_recs.extend(rule(listing, score, report, comps, self.config))

        # De-duplicate by (action_type, title)
        seen: set[tuple[str, str]] = set()
        unique: list[Recommendation] = []
        for r in all_recs:
            key = (r.action_type, r.title)
            if key not in seen:
                seen.add(key)
                unique.append(r)

        # Sort: HIGH > MEDIUM > LOW
        priority_order = {
            RecommendationPriority.HIGH: 0,
            RecommendationPriority.MEDIUM: 1,
            RecommendationPriority.LOW: 2,
        }
        unique.sort(key=lambda r: priority_order.get(r.priority, 9))
        return unique

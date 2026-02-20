"""Scoring engine — orchestrates factor computation and produces a ListingScore."""

from __future__ import annotations

from plm.config import PLMConfig
from plm.models import CompSet, Listing, ListingScore, ScoreCategory

from .factors import (
    AmenityFactor,
    ComplianceFactor,
    DescriptionFactor,
    EngagementFactor,
    MarketContextFactor,
    PhotoFactor,
    PriceFactor,
    ScoringFactor,
    TimelinessFactor,
)

_DEFAULT_FACTORS: list[type[ScoringFactor]] = [
    ComplianceFactor,
    PhotoFactor,
    DescriptionFactor,
    AmenityFactor,
    PriceFactor,
    EngagementFactor,
    MarketContextFactor,
    TimelinessFactor,
]


def _category_from_score(total: float) -> ScoreCategory:
    if total >= 90:
        return ScoreCategory.EXCELLENT
    if total >= 75:
        return ScoreCategory.GOOD
    if total >= 50:
        return ScoreCategory.FAIR
    return ScoreCategory.POOR


class ScoringEngine:
    """Compute a multi-factor ListingScore.

    Usage::

        engine = ScoringEngine()             # default config
        result = engine.score(listing, comps) # returns ListingScore
    """

    def __init__(
        self,
        config: PLMConfig | None = None,
        factors: list[ScoringFactor] | None = None,
    ) -> None:
        self.config = config or PLMConfig()
        self.factors = factors or [cls() for cls in _DEFAULT_FACTORS]

    def score(self, listing: Listing, comps: CompSet | None = None) -> ListingScore:
        sub_scores = []
        for factor in self.factors:
            sub = factor.compute(listing, comps, self.config)
            sub_scores.append(sub)

        # Weighted total (each sub_score.score is 0-100; weight is 0-1)
        total = sum(s.score * s.weight for s in sub_scores)
        # Normalise: weights should sum to ~1.0 but guard against drift
        weight_sum = sum(s.weight for s in sub_scores)
        if weight_sum > 0:
            total = total / weight_sum

        total = max(0.0, min(total, 100.0))
        category = _category_from_score(total)

        # Top 3 weakest factors for actionable feedback
        sorted_subs = sorted(sub_scores, key=lambda s: s.score)
        top_issues = [
            f"{s.name}: {s.details}" for s in sorted_subs[:3] if s.score < 80
        ]

        return ListingScore(
            listing_id=listing.listing_id,
            total_score=round(total, 1),
            category=category,
            sub_scores=sub_scores,
            top_issues=top_issues,
        )

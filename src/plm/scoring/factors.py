"""Individual scoring factors — each computes a normalised 0-100 sub-score.

Every factor is a callable ``(Listing, CompSet | None, PLMConfig) -> SubScore``.
The ``ScoringEngine`` multiplies each sub-score by its configured weight.
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod

from plm.compliance.checker import ComplianceChecker
from plm.config import PLMConfig
from plm.models import CompSet, Listing, SubScore


class ScoringFactor(ABC):
    """Base class for a scoring factor."""

    name: str = "base"

    @abstractmethod
    def compute(
        self,
        listing: Listing,
        comps: CompSet | None,
        config: PLMConfig,
    ) -> SubScore:
        ...


# ---------------------------------------------------------------------------
# 1. Compliance (20%)
# ---------------------------------------------------------------------------

class ComplianceFactor(ScoringFactor):
    name = "compliance"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        checker = ComplianceChecker(config)
        report = checker.check(listing)
        critical = sum(1 for v in report.violations if v.severity.value == "critical")
        high = sum(1 for v in report.violations if v.severity.value == "high")
        other = len(report.violations) - critical - high

        # Any critical → 0; high → heavy penalty; others → moderate
        if critical > 0:
            score = 0.0
        else:
            score = max(0.0, 100 - high * 25 - other * 10)

        weight = config.scoring_weights.compliance
        details = f"{len(report.violations)} violations ({critical} critical, {high} high)"
        return SubScore(name=self.name, score=score, max_score=100, weight=weight, details=details)


# ---------------------------------------------------------------------------
# 2. Photo Quality (15%)
# ---------------------------------------------------------------------------

class PhotoFactor(ScoringFactor):
    name = "photos"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        pt = config.photo_thresholds
        weight = config.scoring_weights.photos

        if listing.photo_count == 0:
            return SubScore(self.name, 0, 100, weight, "No photos uploaded.")

        # Count component (0-70 of sub-score)
        count_ratio = min(listing.photo_count / pt.optimal_count, 1.0)
        count_score = count_ratio * 70

        # Front exterior bonus (0-15)
        front_bonus = 15.0 if listing.has_front_exterior_photo else 0.0

        # Average quality bonus (0-15)
        quality_scores = [p.ai_quality_score for p in listing.photos if p.ai_quality_score > 0]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            quality_bonus = avg_quality * 15
        else:
            quality_bonus = 7.5  # neutral if no AI scores available

        score = min(count_score + front_bonus + quality_bonus, 100.0)
        details = (
            f"{listing.photo_count} photos (optimal {pt.optimal_count}), "
            f"front exterior: {'yes' if listing.has_front_exterior_photo else 'no'}"
        )
        return SubScore(self.name, score, 100, weight, details)


# ---------------------------------------------------------------------------
# 3. Description Quality (10%)
# ---------------------------------------------------------------------------

# Power words associated with higher sale prices (Zillow research)
_POWER_WORDS = {
    "luxurious", "captivating", "impeccable", "stunning", "stainless",
    "granite", "remodel", "landscaped", "upgraded", "gourmet",
    "pergola", "quartz", "porcelain", "hardwood", "spa",
}

# Negative words that may hurt perception
_NEGATIVE_WORDS = {
    "cozy", "quaint", "charming", "fixer", "tlc", "potential",
    "investor", "as-is", "as is", "needs work", "handyman",
}


class DescriptionFactor(ScoringFactor):
    name = "description"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.description
        text = listing.public_remarks.strip()
        if not text:
            return SubScore(self.name, 0, 100, weight, "No public remarks provided.")

        words = text.split()
        word_count = len(words)
        optimal = config.description_thresholds.optimal_word_count
        min_wc = config.description_thresholds.min_word_count

        # Length component (0-60)
        if word_count >= optimal:
            length_score = 60.0
        elif word_count >= min_wc:
            length_score = 60.0 * (word_count - min_wc) / max(optimal - min_wc, 1)
        else:
            length_score = 0.0

        # Power words (0-20)
        lower_words = set(w.lower().strip(".,!?;:") for w in words)
        power_hits = lower_words & _POWER_WORDS
        power_score = min(len(power_hits) / 5, 1.0) * 20

        # Negative word penalty (0 to -15)
        negative_hits = lower_words & _NEGATIVE_WORDS
        negative_penalty = min(len(negative_hits) * 5, 15)

        # Grammar / readability proxy: sentences (0-20)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_score = min(len(sentences) / 5, 1.0) * 20

        score = max(0.0, min(length_score + power_score + sentence_score - negative_penalty, 100.0))
        details = (
            f"{word_count} words, {len(power_hits)} power words, "
            f"{len(negative_hits)} negative terms"
        )
        return SubScore(self.name, score, 100, weight, details)


# ---------------------------------------------------------------------------
# 4. Amenity Completeness (10%)
# ---------------------------------------------------------------------------

_COMMON_AMENITIES = {
    "pool", "garage", "fireplace", "central_air", "central_heat",
    "dishwasher", "washer_dryer", "hardwood_floors", "patio",
    "deck", "fenced_yard", "sprinkler", "security_system",
}


class AmenityFactor(ScoringFactor):
    name = "amenities"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.amenities

        if not listing.amenities and not listing.features:
            return SubScore(self.name, 10, 100, weight, "No amenities or features listed.")

        all_tags = set(a.lower().replace(" ", "_") for a in listing.amenities + listing.features)
        matched = all_tags & _COMMON_AMENITIES
        total_listed = len(all_tags)

        # Reward both breadth (total) and standard tags matched
        breadth_score = min(total_listed / 10, 1.0) * 50
        standard_score = min(len(matched) / 6, 1.0) * 50

        score = min(breadth_score + standard_score, 100.0)
        details = f"{total_listed} tags listed, {len(matched)} standard amenities matched"
        return SubScore(self.name, score, 100, weight, details)


# ---------------------------------------------------------------------------
# 5. Price Competitiveness (15%)
# ---------------------------------------------------------------------------

class PriceFactor(ScoringFactor):
    name = "price"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.price

        if listing.list_price is None or comps is None or comps.median_price <= 0:
            return SubScore(self.name, 50, 100, weight, "Insufficient pricing data for comparison.")

        deviation = (listing.list_price - comps.median_price) / comps.median_price
        pt = config.price_thresholds

        if deviation <= 0:
            # At or below comps — full score (slight boost for good value)
            score = 100.0
        elif deviation <= pt.overpriced_penalty_start_pct:
            score = 100.0
        elif deviation >= pt.overpriced_max_penalty_pct:
            score = 0.0
        else:
            # Linear interpolation
            range_pct = pt.overpriced_max_penalty_pct - pt.overpriced_penalty_start_pct
            score = 100.0 * (1 - (deviation - pt.overpriced_penalty_start_pct) / range_pct)

        details = f"List ${listing.list_price:,.0f} vs comp median ${comps.median_price:,.0f} ({deviation:+.1%})"
        return SubScore(self.name, max(score, 0), 100, weight, details)


# ---------------------------------------------------------------------------
# 6. Engagement Signals (15%)
# ---------------------------------------------------------------------------

class EngagementFactor(ScoringFactor):
    name = "engagement"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.engagement

        views = listing.recent_weekly_views
        leads = listing.recent_weekly_leads

        if views == 0 and leads == 0:
            if listing.days_on_market < 3:
                return SubScore(self.name, 50, 100, weight, "New listing — no engagement data yet.")
            return SubScore(self.name, 10, 100, weight, "No views or leads recorded.")

        # Log-scaled to avoid outlier dominance
        view_component = min(math.log1p(views) / math.log1p(500), 1.0) * 50
        lead_component = min(math.log1p(leads) / math.log1p(20), 1.0) * 50

        score = min(view_component + lead_component, 100.0)
        details = f"{views} weekly views, {leads} weekly leads"
        return SubScore(self.name, score, 100, weight, details)


# ---------------------------------------------------------------------------
# 7. Agent / Market Context (5%)
# ---------------------------------------------------------------------------

class MarketContextFactor(ScoringFactor):
    name = "market_context"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.market_context

        if comps is None or comps.median_dom <= 0:
            return SubScore(self.name, 50, 100, weight, "No market context available.")

        dom_ratio = listing.days_on_market / comps.median_dom if comps.median_dom else 1.0

        if dom_ratio <= 1.0:
            score = 100.0
        elif dom_ratio >= 3.0:
            score = 0.0
        else:
            score = 100.0 * (1 - (dom_ratio - 1.0) / 2.0)

        details = f"DOM {listing.days_on_market} vs market median {comps.median_dom}"
        return SubScore(self.name, max(score, 0), 100, weight, details)


# ---------------------------------------------------------------------------
# 8. Timeliness (5%)
# ---------------------------------------------------------------------------

class TimelinessFactor(ScoringFactor):
    name = "timeliness"

    def compute(self, listing: Listing, comps: CompSet | None, config: PLMConfig) -> SubScore:
        weight = config.scoring_weights.timeliness
        dt = config.dom_thresholds

        dom = listing.days_on_market
        if dom <= dt.penalty_start_days:
            score = 100.0
        elif dom >= dt.max_penalty_days:
            score = 0.0
        else:
            score = 100.0 * (1 - (dom - dt.penalty_start_days) / (dt.max_penalty_days - dt.penalty_start_days))

        details = f"DOM {dom} (penalty starts at {dt.penalty_start_days} days)"
        return SubScore(self.name, max(score, 0), 100, weight, details)

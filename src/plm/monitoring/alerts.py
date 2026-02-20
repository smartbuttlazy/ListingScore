"""Alert manager — threshold-based monitoring that produces Alert objects.

Designed to run periodically (batch) or on-demand after edits (real-time).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from plm.compliance.checker import ComplianceChecker
from plm.config import PLMConfig
from plm.models import (
    Alert,
    AlertSeverity,
    AlertType,
    ComplianceReport,
    CompSet,
    Listing,
    ListingScore,
)
from plm.scoring.engine import ScoringEngine


class AlertManager:
    """Evaluate listings and emit alerts when thresholds are breached.

    Usage::

        mgr = AlertManager()
        alerts = mgr.evaluate(listing, comps=comp_set)
        # or batch:
        all_alerts = mgr.evaluate_batch(listings, comps_map)
    """

    def __init__(self, config: PLMConfig | None = None) -> None:
        self.config = config or PLMConfig()
        self._scorer = ScoringEngine(self.config)
        self._compliance = ComplianceChecker(self.config)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def evaluate(
        self,
        listing: Listing,
        comps: CompSet | None = None,
    ) -> list[Alert]:
        score = self._scorer.score(listing, comps)
        report = self._compliance.check(listing)

        alerts: list[Alert] = []
        alerts.extend(self._compliance_alerts(listing, report))
        alerts.extend(self._score_alerts(listing, score))
        alerts.extend(self._engagement_alerts(listing, comps))
        alerts.extend(self._dom_alerts(listing, comps))
        return alerts

    def evaluate_batch(
        self,
        listings: Sequence[Listing],
        comps_map: dict[str, CompSet] | None = None,
    ) -> dict[str, list[Alert]]:
        comps_map = comps_map or {}
        return {
            l.listing_id: self.evaluate(l, comps_map.get(l.listing_id))
            for l in listings
        }

    # ------------------------------------------------------------------
    # Alert generators
    # ------------------------------------------------------------------

    def _compliance_alerts(
        self, listing: Listing, report: ComplianceReport
    ) -> list[Alert]:
        alerts: list[Alert] = []
        for v in report.violations:
            if v.severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
                alerts.append(Alert(
                    alert_id=_uid(),
                    listing_id=listing.listing_id,
                    alert_type=AlertType.COMPLIANCE,
                    severity=v.severity,
                    message=f"[{v.rule_id}] {v.message}",
                ))
        return alerts

    def _score_alerts(self, listing: Listing, score: ListingScore) -> list[Alert]:
        alerts: list[Alert] = []
        threshold = self.config.alert_thresholds.score_poor_threshold
        if score.total_score < threshold:
            alerts.append(Alert(
                alert_id=_uid(),
                listing_id=listing.listing_id,
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                message=(
                    f"Listing quality score is {score.total_score:.0f} "
                    f"({score.category.value}) — below threshold of {threshold:.0f}. "
                    f"Top issues: {'; '.join(score.top_issues[:3])}"
                ),
            ))
        return alerts

    def _engagement_alerts(
        self, listing: Listing, comps: CompSet | None
    ) -> list[Alert]:
        alerts: list[Alert] = []
        th = self.config.alert_thresholds

        if listing.days_on_market >= th.low_views_days and listing.recent_weekly_views == 0:
            alerts.append(Alert(
                alert_id=_uid(),
                listing_id=listing.listing_id,
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                message=(
                    f"Zero views recorded in the past week (listing active "
                    f"{listing.days_on_market} days). Check syndication and marketing."
                ),
            ))

        if listing.days_on_market >= th.no_leads_days and listing.recent_weekly_leads == 0:
            alerts.append(Alert(
                alert_id=_uid(),
                listing_id=listing.listing_id,
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                message=(
                    f"No leads/inquiries in the past week after "
                    f"{listing.days_on_market} days on market."
                ),
            ))
        return alerts

    def _dom_alerts(self, listing: Listing, comps: CompSet | None) -> list[Alert]:
        alerts: list[Alert] = []
        th = self.config.alert_thresholds
        market_median = comps.median_dom if comps else 30

        if listing.days_on_market > market_median * th.high_dom_multiplier:
            alerts.append(Alert(
                alert_id=_uid(),
                listing_id=listing.listing_id,
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                message=(
                    f"Days on market ({listing.days_on_market}) exceeds "
                    f"{th.high_dom_multiplier:.1f}x the market median ({market_median}). "
                    "Consider strategy refresh."
                ),
            ))
        return alerts


def _uid() -> str:
    return uuid.uuid4().hex[:12]

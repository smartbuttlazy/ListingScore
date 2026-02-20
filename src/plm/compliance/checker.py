"""Orchestrator — runs all compliance sub-checkers and returns a unified report."""

from __future__ import annotations

from plm.config import PLMConfig
from plm.models import ComplianceReport, ComplianceViolation, Listing

from .fair_housing import FairHousingChecker
from .mls_rules import MLSRuleChecker
from .photos import PhotoComplianceChecker
from .remarks import RemarksChecker


class ComplianceChecker:
    """Facade that runs every compliance sub-system and returns a single report."""

    def __init__(self, config: PLMConfig | None = None) -> None:
        self.config = config or PLMConfig()
        self.mls = MLSRuleChecker(self.config)
        self.fair_housing = FairHousingChecker.default()
        self.remarks = RemarksChecker()
        self.photos = PhotoComplianceChecker(self.config)

    def check(self, listing: Listing) -> ComplianceReport:
        violations: list[ComplianceViolation] = []
        violations.extend(self.mls.check(listing))
        violations.extend(self.fair_housing.check(listing))
        violations.extend(self.remarks.check(listing))
        violations.extend(self.photos.check(listing))
        return ComplianceReport(
            listing_id=listing.listing_id,
            passed=len(violations) == 0,
            violations=violations,
        )

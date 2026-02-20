"""MLS rule compliance — required fields, status transitions, timing rules.

Rules are driven by ``PLMConfig.required_fields`` and the jurisdiction
configuration so each MLS can customise what's mandatory.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from plm.config import PLMConfig
from plm.models import (
    AlertSeverity,
    ComplianceViolation,
    Listing,
    ListingStatus,
)


class MLSRuleChecker:
    """Check a listing against MLS-specific rules."""

    def __init__(self, config: PLMConfig | None = None) -> None:
        self.config = config or PLMConfig()

    def check(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        violations.extend(self._check_required_fields(listing))
        violations.extend(self._check_photo_requirements(listing))
        violations.extend(self._check_status_timing(listing))
        violations.extend(self._check_price_validity(listing))
        return violations

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------

    def _check_required_fields(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        for field_name in self.config.required_fields:
            value = self._resolve_field(listing, field_name)
            if value is None or value == "" or value == 0:
                violations.append(ComplianceViolation(
                    rule_id="MLS_REQUIRED_FIELD",
                    severity=AlertSeverity.CRITICAL,
                    field=field_name,
                    message=f"Required field '{field_name}' is missing or empty.",
                    suggestion=f"Fill in the '{field_name}' field to comply with MLS rules.",
                ))
        return violations

    # ------------------------------------------------------------------
    # Photo requirements
    # ------------------------------------------------------------------

    def _check_photo_requirements(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        pt = self.config.photo_thresholds

        if listing.photo_count < pt.minimum_count:
            violations.append(ComplianceViolation(
                rule_id="MLS_MIN_PHOTOS",
                severity=AlertSeverity.CRITICAL,
                field="photos",
                message=f"Listing has {listing.photo_count} photo(s); minimum is {pt.minimum_count}.",
                suggestion="Upload at least one property photo.",
            ))

        if pt.require_front_exterior and not listing.has_front_exterior_photo:
            violations.append(ComplianceViolation(
                rule_id="MLS_FRONT_PHOTO",
                severity=AlertSeverity.HIGH,
                field="photos",
                message="No front exterior photo found.",
                suggestion="Add a high-quality front exterior photo (required by MLS) within 24h.",
            ))

        # Watermark / people / AI checks
        for photo in listing.photos:
            if photo.has_watermark:
                violations.append(ComplianceViolation(
                    rule_id="MLS_PHOTO_WATERMARK",
                    severity=AlertSeverity.MEDIUM,
                    field=f"photo:{photo.photo_id}",
                    message=f"Photo {photo.photo_id} contains a watermark, which many MLSs prohibit.",
                    suggestion="Remove or crop the watermark from this image.",
                ))
            if photo.has_people:
                violations.append(ComplianceViolation(
                    rule_id="MLS_PHOTO_PEOPLE",
                    severity=AlertSeverity.MEDIUM,
                    field=f"photo:{photo.photo_id}",
                    message=f"Photo {photo.photo_id} appears to contain people.",
                    suggestion="Remove images with identifiable people to comply with MLS photo rules.",
                ))

        return violations

    # ------------------------------------------------------------------
    # Status & timing
    # ------------------------------------------------------------------

    def _check_status_timing(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        if listing.status == ListingStatus.COMING_SOON and listing.list_date:
            days_coming_soon = (date.today() - listing.list_date).days
            max_coming_soon = self.config.extra.get("max_coming_soon_days", 21)
            if days_coming_soon > max_coming_soon:
                violations.append(ComplianceViolation(
                    rule_id="MLS_COMING_SOON_EXPIRED",
                    severity=AlertSeverity.HIGH,
                    field="status",
                    message=f"'Coming Soon' status has exceeded {max_coming_soon} days.",
                    suggestion="Transition listing to 'Active' or 'Withdrawn'.",
                ))

        if listing.status == ListingStatus.SOLD and not listing.sold_date:
            violations.append(ComplianceViolation(
                rule_id="MLS_SOLD_NO_DATE",
                severity=AlertSeverity.HIGH,
                field="sold_date",
                message="Listing marked as Sold but no sold date recorded.",
                suggestion="Enter the closing/sold date.",
            ))

        if listing.status == ListingStatus.SOLD and not listing.sold_price:
            violations.append(ComplianceViolation(
                rule_id="MLS_SOLD_NO_PRICE",
                severity=AlertSeverity.HIGH,
                field="sold_price",
                message="Listing marked as Sold but no sold price recorded.",
                suggestion="Enter the final sold price.",
            ))

        return violations

    # ------------------------------------------------------------------
    # Price validity
    # ------------------------------------------------------------------

    def _check_price_validity(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        if listing.list_price is not None and listing.list_price <= 0:
            violations.append(ComplianceViolation(
                rule_id="MLS_INVALID_PRICE",
                severity=AlertSeverity.CRITICAL,
                field="list_price",
                message="List price must be greater than zero.",
                suggestion="Enter a valid list price.",
            ))
        return violations

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_field(listing: Listing, field_name: str) -> Any:
        """Resolve a dotted-ish field name to a value on the Listing."""
        if hasattr(listing, field_name):
            return getattr(listing, field_name)
        if hasattr(listing.property_data, field_name):
            return getattr(listing.property_data, field_name)
        return listing.extra.get(field_name)

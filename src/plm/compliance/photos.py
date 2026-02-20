"""Photo-specific compliance — AI-altered images, copyright, jurisdiction rules."""

from __future__ import annotations

from plm.config import PLMConfig
from plm.models import AlertSeverity, ComplianceViolation, Listing


class PhotoComplianceChecker:
    """Check photo-level compliance rules (watermarks, AI, quality)."""

    def __init__(self, config: PLMConfig | None = None) -> None:
        self.config = config or PLMConfig()

    def check(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        violations.extend(self._check_ai_images(listing))
        violations.extend(self._check_quality(listing))
        return violations

    def _check_ai_images(self, listing: Listing) -> list[ComplianceViolation]:
        """CA AB-723 and similar: AI-altered images must be labelled."""
        violations: list[ComplianceViolation] = []
        # Only enforce AI labelling in jurisdictions that require it
        ai_label_jurisdictions = self.config.extra.get(
            "ai_label_jurisdictions", ["CA"]
        )
        if self.config.jurisdiction not in ai_label_jurisdictions:
            return violations

        for photo in listing.photos:
            if photo.is_ai_generated:
                violations.append(ComplianceViolation(
                    rule_id="PHOTO_AI_LABEL",
                    severity=AlertSeverity.HIGH,
                    field=f"photo:{photo.photo_id}",
                    message=(
                        f"Photo {photo.photo_id} is flagged as AI-generated/altered. "
                        f"Jurisdiction '{self.config.jurisdiction}' requires labelling."
                    ),
                    suggestion=(
                        "Add a 'Digitally Altered' watermark to this image and upload "
                        "the original unaltered photo alongside it."
                    ),
                ))
        return violations

    def _check_quality(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        min_quality = self.config.photo_thresholds.min_quality_score
        for photo in listing.photos:
            if 0 < photo.ai_quality_score < min_quality:
                violations.append(ComplianceViolation(
                    rule_id="PHOTO_LOW_QUALITY",
                    severity=AlertSeverity.LOW,
                    field=f"photo:{photo.photo_id}",
                    message=(
                        f"Photo {photo.photo_id} quality score "
                        f"({photo.ai_quality_score:.2f}) is below threshold ({min_quality})."
                    ),
                    suggestion="Consider replacing this photo with a higher quality image.",
                ))
        return violations

"""Remarks / description compliance — contact info, agent-only notes, banned terms."""

from __future__ import annotations

import re

from plm.models import AlertSeverity, ComplianceViolation, Listing


# Pre-compiled patterns
_PHONE_RE = re.compile(
    r"(?<!\d)"  # no digit before
    r"(?:\+?1[-.\s]?)?"
    r"(?:\(?\d{3}\)?[-.\s]?)"
    r"\d{3}[-.\s]?\d{4}"
    r"(?!\d)",  # no digit after
)

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

_URL_RE = re.compile(
    r"https?://[^\s]+|www\.[^\s]+",
    re.IGNORECASE,
)

_AGENT_BRANDED_RE = re.compile(
    r"\b(call|text|contact|email)\s+(me|us|agent|listing\s+agent)\b",
    re.IGNORECASE,
)

_LOCKBOX_RE = re.compile(
    r"\b(lockbox|lock\s*box|supra|combo|code\s*is|access\s*code)\b",
    re.IGNORECASE,
)


class RemarksChecker:
    """Scan public / private remarks for prohibited content."""

    def check(self, listing: Listing) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        violations.extend(self._check_public_remarks(listing))
        return violations

    def _check_public_remarks(self, listing: Listing) -> list[ComplianceViolation]:
        text = listing.public_remarks
        if not text:
            return []
        violations: list[ComplianceViolation] = []

        # Phone numbers
        for m in _PHONE_RE.finditer(text):
            violations.append(ComplianceViolation(
                rule_id="REMARKS_PHONE",
                severity=AlertSeverity.HIGH,
                field="public_remarks",
                message=f"Phone number detected in public remarks: '{m.group()}'",
                suggestion="Remove phone numbers from public remarks; contact info is not permitted.",
                matched_text=m.group(),
            ))

        # Emails
        for m in _EMAIL_RE.finditer(text):
            violations.append(ComplianceViolation(
                rule_id="REMARKS_EMAIL",
                severity=AlertSeverity.HIGH,
                field="public_remarks",
                message=f"Email address detected in public remarks: '{m.group()}'",
                suggestion="Remove email addresses from public remarks.",
                matched_text=m.group(),
            ))

        # URLs / branded sites
        for m in _URL_RE.finditer(text):
            violations.append(ComplianceViolation(
                rule_id="REMARKS_URL",
                severity=AlertSeverity.MEDIUM,
                field="public_remarks",
                message=f"URL detected in public remarks: '{m.group()}'",
                suggestion="Remove URLs from public remarks unless the MLS allows virtual tour links in a designated field.",
                matched_text=m.group(),
            ))

        # Agent self-promotion
        for m in _AGENT_BRANDED_RE.finditer(text):
            violations.append(ComplianceViolation(
                rule_id="REMARKS_AGENT_PROMO",
                severity=AlertSeverity.MEDIUM,
                field="public_remarks",
                message=f"Agent promotional language detected: '{m.group()}'",
                suggestion="Remove agent contact calls-to-action from public remarks.",
                matched_text=m.group(),
            ))

        # Lockbox / access info in public
        for m in _LOCKBOX_RE.finditer(text):
            violations.append(ComplianceViolation(
                rule_id="REMARKS_LOCKBOX",
                severity=AlertSeverity.CRITICAL,
                field="public_remarks",
                message=f"Lockbox/access code info detected in PUBLIC remarks: '{m.group()}'",
                suggestion="Move lockbox and access code info to private/agent remarks ONLY.",
                matched_text=m.group(),
            ))

        return violations

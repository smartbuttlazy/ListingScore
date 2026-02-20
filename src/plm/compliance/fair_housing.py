"""Fair Housing compliance checker.

Scans listing text for terms/phrases that may violate federal or state
Fair Housing laws (protected classes: race, color, religion, national origin,
sex, familial status, disability, and applicable state classes).

The dictionary of flagged terms is loaded from YAML so MLS admins can
customise it without touching code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import yaml

from plm.models import AlertSeverity, ComplianceViolation, Listing

# ---------------------------------------------------------------------------
# Default flagged terms (embedded fallback; YAML file overrides these)
# ---------------------------------------------------------------------------

_DEFAULT_TERMS: dict[str, list[dict[str, str]]] = {
    "race_color": [
        {"pattern": r"\b(white|black|african[- ]american|hispanic|latino|asian|caucasian)\s+(neighborhood|community|area)\b", "suggestion": "Describe property features, not demographics."},
        {"pattern": r"\bhistoric\s+(black|white|asian|latino)\b", "suggestion": "Remove demographic references; describe the historic architecture instead."},
    ],
    "religion": [
        {"pattern": r"\bnear\s+(church|mosque|synagogue|temple)\b", "suggestion": "Remove proximity to religious institutions; use 'near community amenities' if needed."},
        {"pattern": r"\b(christian|jewish|muslim|catholic|hindu)\s+(community|neighborhood)\b", "suggestion": "Describe the property, not the religious makeup of the area."},
    ],
    "familial_status": [
        {"pattern": r"\b(family[- ]friendly|great\s+for\s+(families|kids|children|couples))\b", "suggestion": "Replace with objective features, e.g. 'spacious backyard' or 'near parks'."},
        {"pattern": r"\b(no\s+children|adults?\s+only|senior\s+(community|living))\b", "suggestion": "Remove age/familial restriction unless legally exempt (e.g. 55+ community)."},
        {"pattern": r"\b(perfect\s+for\s+(young|growing)\s+(couple|family))\b", "suggestion": "Describe property attributes, not ideal occupants."},
        {"pattern": r"\b(bachelor\s+pad|empty[- ]nester)\b", "suggestion": "Describe the property, not the intended occupant type."},
    ],
    "disability": [
        {"pattern": r"\b(walking\s+distance)\b", "suggestion": "Use 'close proximity to' or specific distances instead."},
        {"pattern": r"\b(handicapped|crippled|disabled\s+person)\b", "suggestion": "Use 'accessible' or describe specific ADA features."},
    ],
    "sex_gender": [
        {"pattern": r"\b(man\s+cave|she[- ]shed|mother[- ]in[- ]law)\b", "suggestion": "Use 'bonus room', 'accessory dwelling unit', or 'guest suite'."},
        {"pattern": r"\bmaster\s+(bed\s*room|suite|bath)\b", "suggestion": "Use 'primary bedroom/suite/bath' per current industry guidance."},
    ],
    "national_origin": [
        {"pattern": r"\b(speaks?\s+english|english[- ]speaking)\b", "suggestion": "Remove language preference; it implies national origin discrimination."},
    ],
    "age": [
        {"pattern": r"\b(young\s+professionals?|millennials?|retirees?)\b", "suggestion": "Describe property features, not target demographics."},
    ],
}


@dataclass
class FairHousingChecker:
    """Checks listing text fields against a dictionary of flagged terms/phrases."""

    terms: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    _compiled: dict[str, list[tuple[re.Pattern[str], str]]] = field(
        default_factory=dict, repr=False
    )

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> "FairHousingChecker":
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls(terms=raw)

    @classmethod
    def default(cls) -> "FairHousingChecker":
        return cls(terms=_DEFAULT_TERMS)

    def __post_init__(self) -> None:
        if not self.terms:
            self.terms = dict(_DEFAULT_TERMS)
        self._compile()

    def _compile(self) -> None:
        self._compiled = {}
        for category, entries in self.terms.items():
            compiled = []
            for entry in entries:
                try:
                    compiled.append((
                        re.compile(entry["pattern"], re.IGNORECASE),
                        entry.get("suggestion", "Review this term for Fair Housing compliance."),
                    ))
                except re.error:
                    continue
            self._compiled[category] = compiled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, listing: Listing) -> list[ComplianceViolation]:
        """Return violations found in listing text fields."""
        violations: list[ComplianceViolation] = []
        text_fields = [
            ("public_remarks", listing.public_remarks),
            ("private_remarks", listing.private_remarks),
        ]
        for field_name, text in text_fields:
            if not text:
                continue
            violations.extend(self._scan_text(listing.listing_id, field_name, text))
        return violations

    def scan_text(self, text: str, field_name: str = "text") -> list[ComplianceViolation]:
        """Scan arbitrary text (useful outside of a full Listing context)."""
        return self._scan_text("", field_name, text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scan_text(
        self, listing_id: str, field_name: str, text: str
    ) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        for category, patterns in self._compiled.items():
            for regex, suggestion in patterns:
                for match in regex.finditer(text):
                    violations.append(ComplianceViolation(
                        rule_id=f"FH_{category}",
                        severity=AlertSeverity.HIGH,
                        field=field_name,
                        message=f"Potential Fair Housing violation ({category}): '{match.group()}'",
                        suggestion=suggestion,
                        matched_text=match.group(),
                    ))
        return violations

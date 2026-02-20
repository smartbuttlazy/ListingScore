"""Configuration loader — reads YAML rule definitions and app settings.

Designed so that every MLS / region / brokerage can supply its own rule overrides
via config files while sensible defaults always apply.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


# ---------------------------------------------------------------------------
# Structured settings
# ---------------------------------------------------------------------------

@dataclass
class ScoringWeights:
    compliance: float = 0.20
    photos: float = 0.15
    description: float = 0.10
    amenities: float = 0.10
    price: float = 0.15
    engagement: float = 0.15
    market_context: float = 0.05
    timeliness: float = 0.05
    fair_housing: float = 0.05


@dataclass
class PhotoThresholds:
    optimal_count: int = 25
    minimum_count: int = 1
    require_front_exterior: bool = True
    min_quality_score: float = 0.4


@dataclass
class DescriptionThresholds:
    optimal_word_count: int = 150
    min_word_count: int = 30


@dataclass
class PriceThresholds:
    overpriced_penalty_start_pct: float = 0.05   # 5% above comps
    overpriced_max_penalty_pct: float = 0.50     # 50% above → score 0


@dataclass
class DOMThresholds:
    penalty_start_days: int = 30
    max_penalty_days: int = 120


@dataclass
class AlertThresholds:
    low_views_days: int = 7
    no_leads_days: int = 14
    high_dom_multiplier: float = 1.5  # relative to market median
    score_poor_threshold: float = 50.0


@dataclass
class PLMConfig:
    """Top-level PLM configuration."""

    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    photo_thresholds: PhotoThresholds = field(default_factory=PhotoThresholds)
    description_thresholds: DescriptionThresholds = field(default_factory=DescriptionThresholds)
    price_thresholds: PriceThresholds = field(default_factory=PriceThresholds)
    dom_thresholds: DOMThresholds = field(default_factory=DOMThresholds)
    alert_thresholds: AlertThresholds = field(default_factory=AlertThresholds)

    # MLS-specific
    required_fields: list[str] = field(default_factory=lambda: [
        "list_price", "address", "bedrooms", "bathrooms",
        "living_area_sqft", "mls_number", "agent_id",
    ])

    # Region / jurisdiction
    jurisdiction: str = "default"

    # Fair Housing
    fair_housing_terms_file: str = "fair_housing_terms.yaml"

    # Extra raw config (for custom rules)
    extra: dict[str, Any] = field(default_factory=dict)


def load_config(
    config_dir: str | Path | None = None,
    override_file: str | None = None,
) -> PLMConfig:
    """Load PLM configuration from YAML files.

    Resolution order (later wins):
    1. Built-in defaults (the dataclass defaults above)
    2. ``config/plm_defaults.yaml``
    3. ``config/<override_file>``  (e.g. ``mls_crmls.yaml``)
    4. Environment variables prefixed with ``PLM_``
    """
    config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
    cfg = PLMConfig()

    # 1. defaults yaml
    defaults_path = config_dir / "plm_defaults.yaml"
    if defaults_path.exists():
        _apply_yaml(cfg, defaults_path)

    # 2. override yaml
    if override_file:
        override_path = config_dir / override_file
        if override_path.exists():
            _apply_yaml(cfg, override_path)

    # 3. env vars
    _apply_env(cfg)

    return cfg


def _apply_yaml(cfg: PLMConfig, path: Path) -> None:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    if "scoring_weights" in raw:
        for k, v in raw["scoring_weights"].items():
            if hasattr(cfg.scoring_weights, k):
                setattr(cfg.scoring_weights, k, float(v))

    if "photo_thresholds" in raw:
        for k, v in raw["photo_thresholds"].items():
            if hasattr(cfg.photo_thresholds, k):
                setattr(cfg.photo_thresholds, k, type(getattr(cfg.photo_thresholds, k))(v))

    if "description_thresholds" in raw:
        for k, v in raw["description_thresholds"].items():
            if hasattr(cfg.description_thresholds, k):
                setattr(cfg.description_thresholds, k, type(getattr(cfg.description_thresholds, k))(v))

    if "required_fields" in raw:
        cfg.required_fields = raw["required_fields"]

    if "jurisdiction" in raw:
        cfg.jurisdiction = raw["jurisdiction"]

    if "fair_housing_terms_file" in raw:
        cfg.fair_housing_terms_file = raw["fair_housing_terms_file"]

    cfg.extra.update({k: v for k, v in raw.items() if k not in {
        "scoring_weights", "photo_thresholds", "description_thresholds",
        "required_fields", "jurisdiction", "fair_housing_terms_file",
    }})


def _apply_env(cfg: PLMConfig) -> None:
    jurisdiction = os.environ.get("PLM_JURISDICTION")
    if jurisdiction:
        cfg.jurisdiction = jurisdiction

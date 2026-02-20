"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from plm.config import PLMConfig, load_config


class TestConfig:
    def test_default_config(self):
        cfg = PLMConfig()
        assert cfg.scoring_weights.compliance == 0.20
        assert cfg.scoring_weights.photos == 0.15
        assert len(cfg.required_fields) > 0

    def test_load_from_config_dir(self):
        config_dir = Path(__file__).parent.parent / "config"
        if config_dir.exists():
            cfg = load_config(config_dir)
            assert cfg.jurisdiction == "default"

    def test_load_with_override(self):
        config_dir = Path(__file__).parent.parent / "config"
        if (config_dir / "mls_example.yaml").exists():
            cfg = load_config(config_dir, override_file="mls_example.yaml")
            assert cfg.jurisdiction == "CA"
            assert "lot_size_sqft" in cfg.required_fields

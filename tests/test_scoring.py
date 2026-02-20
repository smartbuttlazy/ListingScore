"""Tests for the scoring engine."""

from __future__ import annotations

from plm.models import CompSet, ScoreCategory
from plm.scoring import ScoringEngine


class TestScoringEngine:
    def test_good_listing_scores_high(self, good_listing, comp_set, config):
        engine = ScoringEngine(config)
        result = engine.score(good_listing, comp_set)
        assert result.total_score >= 70
        assert result.category in (ScoreCategory.EXCELLENT, ScoreCategory.GOOD)

    def test_poor_listing_scores_low(self, poor_listing, config):
        engine = ScoringEngine(config)
        result = engine.score(poor_listing)
        assert result.total_score < 50
        assert result.category == ScoreCategory.POOR

    def test_sub_scores_present(self, good_listing, comp_set, config):
        engine = ScoringEngine(config)
        result = engine.score(good_listing, comp_set)
        names = {s.name for s in result.sub_scores}
        assert "compliance" in names
        assert "photos" in names
        assert "description" in names
        assert "price" in names

    def test_overpriced_listing_penalised(self, good_listing, overpriced_comp_set, config):
        engine = ScoringEngine(config)
        good_listing.list_price = 600_000  # 50% above 400k median
        result = engine.score(good_listing, overpriced_comp_set)
        price_sub = next(s for s in result.sub_scores if s.name == "price")
        assert price_sub.score < 50  # heavily penalised

    def test_score_has_top_issues(self, poor_listing, config):
        engine = ScoringEngine(config)
        result = engine.score(poor_listing)
        assert len(result.top_issues) > 0

    def test_score_normalised_0_100(self, good_listing, comp_set, config):
        engine = ScoringEngine(config)
        result = engine.score(good_listing, comp_set)
        assert 0 <= result.total_score <= 100

    def test_no_comps_still_works(self, good_listing, config):
        engine = ScoringEngine(config)
        result = engine.score(good_listing, None)
        assert 0 <= result.total_score <= 100

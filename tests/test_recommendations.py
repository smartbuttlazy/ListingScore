"""Tests for the recommendation engine."""

from __future__ import annotations

from plm.models import RecommendationPriority
from plm.recommendations import RecommendationEngine


class TestRecommendations:
    def test_poor_listing_gets_recommendations(self, poor_listing, config):
        engine = RecommendationEngine(config)
        recs = engine.recommend(poor_listing)
        assert len(recs) > 0
        # Should include photo and description fixes
        action_types = [r.action_type for r in recs]
        assert "add_photo" in action_types or "add_photos" in action_types

    def test_good_listing_gets_fewer_recommendations(self, good_listing, comp_set, config):
        engine = RecommendationEngine(config)
        recs = engine.recommend(good_listing, comp_set)
        # Good listing may still get low-priority tips but fewer high ones
        high_recs = [r for r in recs if r.priority == RecommendationPriority.HIGH]
        assert len(high_recs) <= 2

    def test_overpriced_listing_gets_price_recommendation(
        self, good_listing, overpriced_comp_set, config
    ):
        engine = RecommendationEngine(config)
        good_listing.list_price = 600_000
        recs = engine.recommend(good_listing, overpriced_comp_set)
        assert any(r.action_type == "adjust_price" for r in recs)

    def test_fair_housing_fix_recommended(self, poor_listing, config):
        engine = RecommendationEngine(config)
        recs = engine.recommend(poor_listing)
        assert any(r.action_type == "edit_remarks" for r in recs)

    def test_recommendations_sorted_by_priority(self, poor_listing, config):
        engine = RecommendationEngine(config)
        recs = engine.recommend(poor_listing)
        if len(recs) >= 2:
            priorities = [r.priority for r in recs]
            order = {RecommendationPriority.HIGH: 0, RecommendationPriority.MEDIUM: 1, RecommendationPriority.LOW: 2}
            indices = [order[p] for p in priorities]
            assert indices == sorted(indices)

    def test_no_duplicate_recommendations(self, poor_listing, config):
        engine = RecommendationEngine(config)
        recs = engine.recommend(poor_listing)
        keys = [(r.action_type, r.title) for r in recs]
        assert len(keys) == len(set(keys))

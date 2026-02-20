"""Tests for the monitoring / alert system."""

from __future__ import annotations

from datetime import date, timedelta

from plm.models import AlertType, Listing, ListingStatus, PropertyData, ViewStats
from plm.monitoring import AlertManager


class TestAlerts:
    def test_poor_listing_triggers_alerts(self, poor_listing, config):
        mgr = AlertManager(config)
        alerts = mgr.evaluate(poor_listing)
        assert len(alerts) > 0

    def test_good_listing_few_alerts(self, good_listing, comp_set, config):
        mgr = AlertManager(config)
        alerts = mgr.evaluate(good_listing, comp_set)
        compliance_alerts = [a for a in alerts if a.alert_type == AlertType.COMPLIANCE]
        assert len(compliance_alerts) == 0

    def test_stale_listing_dom_alert(self, config):
        today = date.today()
        listing = Listing(
            listing_id="STALE-1",
            address="999 Old Rd",
            list_price=300_000,
            property_data=PropertyData(bedrooms=3, bathrooms=2, living_area_sqft=1500),
            agent_id="A1",
            mls_number="M1",
            list_date=today - timedelta(days=100),
            photos=[],
        )
        mgr = AlertManager(config)
        alerts = mgr.evaluate(listing)
        performance_alerts = [a for a in alerts if a.alert_type == AlertType.PERFORMANCE]
        assert len(performance_alerts) > 0

    def test_no_views_alert(self, config):
        today = date.today()
        listing = Listing(
            listing_id="NOVIEW-1",
            address="1 Empty Blvd",
            list_price=250_000,
            property_data=PropertyData(bedrooms=2, bathrooms=1, living_area_sqft=1000),
            agent_id="A1",
            mls_number="M1",
            list_date=today - timedelta(days=10),
            view_stats=[
                ViewStats(date=today - timedelta(days=d), mls_views=0, portal_views=0, inquiries=0)
                for d in range(7)
            ],
            photos=[],
        )
        mgr = AlertManager(config)
        alerts = mgr.evaluate(listing)
        messages = [a.message for a in alerts]
        assert any("zero views" in m.lower() or "no leads" in m.lower() for m in messages)

    def test_batch_evaluate(self, good_listing, poor_listing, config):
        mgr = AlertManager(config)
        results = mgr.evaluate_batch([good_listing, poor_listing])
        assert good_listing.listing_id in results
        assert poor_listing.listing_id in results

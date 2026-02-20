"""Tests for the compliance checking sub-system."""

from __future__ import annotations

from plm.compliance import (
    ComplianceChecker,
    FairHousingChecker,
    MLSRuleChecker,
    RemarksChecker,
)
from plm.config import PLMConfig
from plm.models import Listing, ListingStatus, Photo, PropertyData


class TestFairHousing:
    def test_detects_familial_status(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text("This home is great for families with kids!")
        rule_ids = [v.rule_id for v in violations]
        assert any("familial_status" in r for r in rule_ids)

    def test_detects_master_bedroom(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text("Large master bedroom with ensuite.")
        assert len(violations) > 0
        assert any("sex_gender" in v.rule_id for v in violations)

    def test_detects_religious_reference(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text("Located near church and great schools.")
        assert any("religion" in v.rule_id for v in violations)

    def test_clean_text_passes(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text(
            "Beautiful 3-bedroom home with updated kitchen and hardwood floors."
        )
        assert len(violations) == 0

    def test_detects_disability_reference(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text("Walking distance to shops and restaurants.")
        assert any("disability" in v.rule_id for v in violations)

    def test_suggestions_provided(self):
        checker = FairHousingChecker.default()
        violations = checker.scan_text("Perfect for young couple.")
        for v in violations:
            assert v.suggestion != ""


class TestMLSRules:
    def test_missing_required_fields(self, config):
        checker = MLSRuleChecker(config)
        listing = Listing(
            listing_id="T1",
            address="123 Main St",
            list_price=None,  # missing
            property_data=PropertyData(bedrooms=None, bathrooms=None),
            agent_id="",
            mls_number="",
        )
        violations = checker.check(listing)
        missing_fields = [v.field for v in violations if v.rule_id == "MLS_REQUIRED_FIELD"]
        assert "list_price" in missing_fields
        assert "bedrooms" in missing_fields
        assert "agent_id" in missing_fields

    def test_no_photos(self, config):
        checker = MLSRuleChecker(config)
        listing = Listing(
            listing_id="T2", address="456 Elm", photos=[],
            list_price=100_000, agent_id="A1", mls_number="M1",
            property_data=PropertyData(bedrooms=3, bathrooms=2, living_area_sqft=1500),
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "MLS_MIN_PHOTOS" for v in violations)

    def test_no_front_exterior_photo(self, config):
        checker = MLSRuleChecker(config)
        listing = Listing(
            listing_id="T3", address="789 Oak",
            list_price=200_000, agent_id="A1", mls_number="M1",
            property_data=PropertyData(bedrooms=2, bathrooms=1, living_area_sqft=1000),
            photos=[Photo(photo_id="1", url="http://img/1.jpg", photo_type="interior")],
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "MLS_FRONT_PHOTO" for v in violations)

    def test_sold_missing_date(self, config):
        checker = MLSRuleChecker(config)
        listing = Listing(
            listing_id="T4", address="100 Sold St",
            status=ListingStatus.SOLD,
            list_price=300_000, agent_id="A1", mls_number="M1",
            property_data=PropertyData(bedrooms=3, bathrooms=2, living_area_sqft=1800),
            photos=[Photo(photo_id="1", url="u", photo_type="exterior_front")],
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "MLS_SOLD_NO_DATE" for v in violations)

    def test_good_listing_passes(self, good_listing, config):
        checker = MLSRuleChecker(config)
        violations = checker.check(good_listing)
        critical = [v for v in violations if v.severity.value == "critical"]
        assert len(critical) == 0


class TestRemarks:
    def test_phone_number(self):
        checker = RemarksChecker()
        listing = Listing(
            listing_id="R1", address="x",
            public_remarks="Call 555-123-4567 for showing.",
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "REMARKS_PHONE" for v in violations)

    def test_email(self):
        checker = RemarksChecker()
        listing = Listing(
            listing_id="R2", address="x",
            public_remarks="Email agent@brokerage.com for info.",
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "REMARKS_EMAIL" for v in violations)

    def test_lockbox_in_public(self):
        checker = RemarksChecker()
        listing = Listing(
            listing_id="R3", address="x",
            public_remarks="Lockbox code is 1234.",
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "REMARKS_LOCKBOX" for v in violations)
        assert any(v.severity.value == "critical" for v in violations)

    def test_url_detection(self):
        checker = RemarksChecker()
        listing = Listing(
            listing_id="R4", address="x",
            public_remarks="See more at https://mybrokerage.com/listing123",
        )
        violations = checker.check(listing)
        assert any(v.rule_id == "REMARKS_URL" for v in violations)

    def test_clean_remarks_pass(self):
        checker = RemarksChecker()
        listing = Listing(
            listing_id="R5", address="x",
            public_remarks="Beautiful home with 3 bedrooms and a large backyard.",
        )
        violations = checker.check(listing)
        assert len(violations) == 0


class TestComplianceOrchestrator:
    def test_good_listing_passes(self, good_listing, config):
        checker = ComplianceChecker(config)
        report = checker.check(good_listing)
        assert report.passed

    def test_poor_listing_fails(self, poor_listing, config):
        checker = ComplianceChecker(config)
        report = checker.check(poor_listing)
        assert not report.passed
        assert len(report.violations) > 0

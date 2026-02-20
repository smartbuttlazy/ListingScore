"""Shared fixtures for PLM tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from plm.config import PLMConfig
from plm.models import (
    CompSet,
    Listing,
    ListingStatus,
    Photo,
    PriceHistoryEntry,
    PropertyData,
    ViewStats,
)


@pytest.fixture
def config() -> PLMConfig:
    return PLMConfig()


@pytest.fixture
def good_listing() -> Listing:
    """A well-formed listing that should score high."""
    today = date.today()
    return Listing(
        listing_id="GOOD-001",
        address="123 Main St, Anytown, CA 90210",
        status=ListingStatus.ACTIVE,
        list_price=500_000,
        original_list_price=500_000,
        property_data=PropertyData(
            living_area_sqft=2000,
            lot_size_sqft=6000,
            bedrooms=3,
            bathrooms=2.5,
            year_built=2010,
            tax_assessed_value=480_000,
            garage_spaces=2,
            pool=True,
            fireplace=True,
        ),
        public_remarks=(
            "Stunning 3-bedroom home with luxurious upgrades throughout. "
            "Gourmet kitchen with granite countertops and stainless steel appliances. "
            "Hardwood floors, spa-like primary bath, landscaped backyard with "
            "sparkling pool. Move-in ready with upgraded HVAC and newer roof. "
            "This impeccable property is located near excellent schools and parks."
        ),
        amenities=["pool", "garage", "fireplace", "central_air", "hardwood_floors",
                    "patio", "fenced_yard", "sprinkler"],
        features=["granite countertops", "stainless appliances", "newer roof"],
        photos=[
            Photo(photo_id=f"p{i}", url=f"https://img.example.com/{i}.jpg",
                   photo_type="exterior_front" if i == 0 else "interior",
                   ai_quality_score=0.85)
            for i in range(25)
        ],
        agent_id="AGT-100",
        mls_number="MLS-12345",
        list_date=today - timedelta(days=10),
        view_stats=[
            ViewStats(date=today - timedelta(days=d), mls_views=30, portal_views=50, inquiries=3)
            for d in range(7)
        ],
    )


@pytest.fixture
def poor_listing() -> Listing:
    """A listing with many issues that should score low."""
    today = date.today()
    return Listing(
        listing_id="POOR-001",
        address="456 Elm Ave",
        status=ListingStatus.ACTIVE,
        list_price=None,  # missing price
        property_data=PropertyData(
            bedrooms=None,
            bathrooms=None,
        ),
        public_remarks="Cozy home. Call me at 555-123-4567 for details. Great for families!",
        photos=[],
        agent_id="",
        mls_number="",
        list_date=today - timedelta(days=90),
    )


@pytest.fixture
def comp_set() -> CompSet:
    return CompSet(
        comp_group_id="COMP-1",
        median_price=500_000,
        average_price=510_000,
        median_price_per_sqft=250,
        median_dom=25,
    )


@pytest.fixture
def overpriced_comp_set() -> CompSet:
    return CompSet(
        comp_group_id="COMP-2",
        median_price=400_000,
        average_price=405_000,
        median_price_per_sqft=200,
        median_dom=20,
    )

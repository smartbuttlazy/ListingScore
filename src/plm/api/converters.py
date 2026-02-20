"""Convert between Pydantic API schemas and domain dataclasses."""

from __future__ import annotations

from plm.models import (
    CompSet,
    GeoLocation,
    Listing,
    ListingStatus,
    Photo,
    PriceHistoryEntry,
    PropertyData,
    ViewStats,
)

from .schemas import CompSetIn, ListingIn


def listing_from_api(data: ListingIn) -> Listing:
    """Convert API ListingIn to domain Listing."""
    geo = None
    if data.geolocation:
        geo = GeoLocation(data.geolocation.latitude, data.geolocation.longitude)

    pd = PropertyData(
        living_area_sqft=data.property_data.living_area_sqft,
        lot_size_sqft=data.property_data.lot_size_sqft,
        bedrooms=data.property_data.bedrooms,
        bathrooms=data.property_data.bathrooms,
        year_built=data.property_data.year_built,
        tax_assessed_value=data.property_data.tax_assessed_value,
        hoa_fees=data.property_data.hoa_fees,
        stories=data.property_data.stories,
        garage_spaces=data.property_data.garage_spaces,
        pool=data.property_data.pool,
        fireplace=data.property_data.fireplace,
    )

    photos = [
        Photo(
            photo_id=p.photo_id,
            url=p.url,
            photo_type=p.photo_type,
            ai_quality_score=p.ai_quality_score,
            is_ai_generated=p.is_ai_generated,
            has_watermark=p.has_watermark,
            has_people=p.has_people,
            width=p.width,
            height=p.height,
        )
        for p in data.photos
    ]

    price_history = [
        PriceHistoryEntry(date=ph.date, price=ph.price) for ph in data.price_history
    ]

    view_stats = [
        ViewStats(
            date=vs.date,
            mls_views=vs.mls_views,
            portal_views=vs.portal_views,
            shares=vs.shares,
            saves=vs.saves,
            inquiries=vs.inquiries,
        )
        for vs in data.view_stats
    ]

    try:
        status = ListingStatus(data.status)
    except ValueError:
        status = ListingStatus.ACTIVE

    return Listing(
        listing_id=data.listing_id,
        address=data.address,
        status=status,
        list_price=data.list_price,
        original_list_price=data.original_list_price,
        geolocation=geo,
        property_data=pd,
        public_remarks=data.public_remarks,
        private_remarks=data.private_remarks,
        amenities=data.amenities,
        features=data.features,
        photos=photos,
        virtual_tour_url=data.virtual_tour_url,
        agent_id=data.agent_id,
        brokerage=data.brokerage,
        mls_number=data.mls_number,
        list_date=data.list_date,
        sold_date=data.sold_date,
        sold_price=data.sold_price,
        price_history=price_history,
        view_stats=view_stats,
        extra=data.extra,
    )


def compset_from_api(data: CompSetIn | None) -> CompSet | None:
    if data is None:
        return None
    return CompSet(
        comp_group_id=data.comp_group_id,
        listing_ids=data.listing_ids,
        average_price=data.average_price,
        median_price=data.median_price,
        median_price_per_sqft=data.median_price_per_sqft,
        median_dom=data.median_dom,
        comp_radius_miles=data.comp_radius_miles,
    )

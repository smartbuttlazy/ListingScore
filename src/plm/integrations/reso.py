"""RESO Web API / RETS adapter stub.

Provides an interface for syncing listing data from an MLS feed.
Actual HTTP calls depend on the MLS vendor; this module defines the
contract and a reference implementation you can subclass.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from plm.models import Listing, ListingStatus, Photo, PropertyData


class RESOAdapter(ABC):
    """Abstract base for MLS data adapters."""

    @abstractmethod
    def fetch_listings(self, **filters: Any) -> list[Listing]:
        """Fetch listings matching the given filters."""
        ...

    @abstractmethod
    def fetch_listing(self, listing_id: str) -> Listing | None:
        """Fetch a single listing by ID."""
        ...


class RESOWebAPIAdapter(RESOAdapter):
    """Reference RESO Web API v2 adapter.

    Subclass and override ``_base_url`` / ``_headers`` for your MLS.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30,
        )

    def fetch_listings(self, **filters: Any) -> list[Listing]:
        params: dict[str, str] = {}
        if "status" in filters:
            params["$filter"] = f"StandardStatus eq '{filters['status']}'"
        if "top" in filters:
            params["$top"] = str(filters["top"])

        resp = self._client.get("/Property", params=params)
        resp.raise_for_status()
        data = resp.json()
        return [self._map(item) for item in data.get("value", [])]

    def fetch_listing(self, listing_id: str) -> Listing | None:
        resp = self._client.get(f"/Property('{listing_id}')")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._map(resp.json())

    @staticmethod
    def _map(raw: dict[str, Any]) -> Listing:
        """Map a RESO Property resource to a domain Listing.

        Field names follow the RESO Data Dictionary where possible.
        Override this for MLS-specific field variations.
        """
        status_map = {
            "Active": ListingStatus.ACTIVE,
            "Pending": ListingStatus.PENDING,
            "Closed": ListingStatus.SOLD,
            "Withdrawn": ListingStatus.WITHDRAWN,
            "Expired": ListingStatus.EXPIRED,
            "Coming Soon": ListingStatus.COMING_SOON,
        }
        return Listing(
            listing_id=str(raw.get("ListingKey", raw.get("ListingId", ""))),
            address=raw.get("UnparsedAddress", ""),
            status=status_map.get(raw.get("StandardStatus", ""), ListingStatus.ACTIVE),
            list_price=raw.get("ListPrice"),
            original_list_price=raw.get("OriginalListPrice"),
            property_data=PropertyData(
                living_area_sqft=raw.get("LivingArea"),
                lot_size_sqft=raw.get("LotSizeSquareFeet"),
                bedrooms=raw.get("BedroomsTotal"),
                bathrooms=raw.get("BathroomsTotalDecimal"),
                year_built=raw.get("YearBuilt"),
                tax_assessed_value=raw.get("TaxAssessedValue"),
            ),
            public_remarks=raw.get("PublicRemarks", ""),
            private_remarks=raw.get("PrivateRemarks", ""),
            agent_id=raw.get("ListAgentKey", ""),
            mls_number=raw.get("ListingId", ""),
            photos=[
                Photo(photo_id=str(i), url=m.get("MediaURL", ""), photo_type=m.get("MediaCategory", ""))
                for i, m in enumerate(raw.get("Media", []))
            ],
            extra=raw,
        )

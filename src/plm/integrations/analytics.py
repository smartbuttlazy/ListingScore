"""Analytics / engagement data adapter stub.

Provides an interface for ingesting listing engagement metrics from
sources like ListTrac, portal APIs, or internal CRM/MLS analytics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from plm.models import ViewStats


class AnalyticsAdapter(ABC):
    """Abstract base for listing analytics data sources."""

    @abstractmethod
    def fetch_stats(self, listing_id: str, start: date, end: date) -> list[ViewStats]:
        ...


class ListTracAdapter(AnalyticsAdapter):
    """Placeholder for ListTrac-style API integration.

    ListTrac provides listing views, leads, shares, and favorites data.
    Subclass and implement HTTP calls for your specific ListTrac account.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.listtrac.com") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def fetch_stats(self, listing_id: str, start: date, end: date) -> list[ViewStats]:
        # Placeholder — real implementation would call the ListTrac API
        # and map the response to ViewStats objects
        return []


class InMemoryAnalyticsAdapter(AnalyticsAdapter):
    """Simple in-memory adapter for testing and demos."""

    def __init__(self) -> None:
        self._data: dict[str, list[ViewStats]] = {}

    def add_stats(self, listing_id: str, stats: list[ViewStats]) -> None:
        self._data.setdefault(listing_id, []).extend(stats)

    def fetch_stats(self, listing_id: str, start: date, end: date) -> list[ViewStats]:
        return [
            s for s in self._data.get(listing_id, [])
            if start <= s.date <= end
        ]

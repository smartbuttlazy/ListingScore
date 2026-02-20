"""Tests for the FastAPI REST endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from plm.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


_GOOD_PAYLOAD = {
    "listing": {
        "listing_id": "API-001",
        "address": "123 API St, Test Town, CA 90000",
        "status": "active",
        "list_price": 500000,
        "property_data": {
            "bedrooms": 3,
            "bathrooms": 2.0,
            "living_area_sqft": 1800,
        },
        "public_remarks": (
            "Stunning home with luxurious upgrades. Granite countertops, "
            "hardwood floors, and a landscaped backyard. Stainless steel "
            "appliances in the gourmet kitchen. Move-in ready."
        ),
        "amenities": ["pool", "garage", "fireplace", "central_air"],
        "photos": [
            {"photo_id": f"p{i}", "url": f"https://img/{i}.jpg",
             "photo_type": "exterior_front" if i == 0 else "interior",
             "ai_quality_score": 0.8}
            for i in range(20)
        ],
        "agent_id": "AGT-1",
        "mls_number": "MLS-001",
        "list_date": "2026-02-10",
    },
    "comps": {
        "median_price": 500000,
        "median_dom": 25,
    },
}

_POOR_PAYLOAD = {
    "listing": {
        "listing_id": "API-002",
        "address": "456 Bad Ln",
        "public_remarks": "Call 555-111-2222. Great for families!",
        "photos": [],
        "list_date": "2025-11-01",
    },
}


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestScoreEndpoint:
    def test_score_good_listing(self, client):
        resp = client.post("/api/v1/score", json=_GOOD_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] >= 60
        assert data["category"] in ("excellent", "good", "fair")
        assert len(data["sub_scores"]) > 0

    def test_score_poor_listing(self, client):
        resp = client.post("/api/v1/score", json=_POOR_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] < 50


class TestComplianceEndpoint:
    def test_compliance_good(self, client):
        resp = client.post("/api/v1/compliance", json={"listing": _GOOD_PAYLOAD["listing"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is True

    def test_compliance_poor(self, client):
        resp = client.post("/api/v1/compliance", json={"listing": _POOR_PAYLOAD["listing"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is False
        assert len(data["violations"]) > 0


class TestTextCheckEndpoint:
    def test_fair_housing_text(self, client):
        resp = client.post("/api/v1/compliance/text", json={
            "text": "Perfect for young couple near the church.",
            "field_name": "remarks",
        })
        assert resp.status_code == 200
        violations = resp.json()
        assert len(violations) > 0

    def test_clean_text(self, client):
        resp = client.post("/api/v1/compliance/text", json={
            "text": "3-bedroom home with large backyard and updated kitchen.",
        })
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestRecommendEndpoint:
    def test_recommend_poor(self, client):
        resp = client.post("/api/v1/recommend", json=_POOR_PAYLOAD)
        assert resp.status_code == 200
        recs = resp.json()
        assert len(recs) > 0
        assert recs[0]["priority"] == "high"


class TestAlertsEndpoint:
    def test_alerts_poor(self, client):
        resp = client.post("/api/v1/alerts", json=_POOR_PAYLOAD)
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) > 0

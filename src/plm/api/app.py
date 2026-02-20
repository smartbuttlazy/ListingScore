"""FastAPI application factory.

Import ``create_app`` and mount it in your ASGI server, or run this file
directly with ``uvicorn plm.api.app:app``.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PLM — Property Listing Manager",
        description=(
            "Compliance checking, multi-factor quality scoring, "
            "recommendations, and alerting for real-estate listings."
        ),
        version="0.1.0",
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()

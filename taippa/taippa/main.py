"""Entry point for the FastAPI application."""

from __future__ import annotations

import asyncio
from typing import Coroutine

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from .database import Base, engine
from .routers import auth as auth_router
from .routers import brands as brands_router
from .routers import campaigns as campaigns_router
from .routers import influencers as influencers_router


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(title="TAIPPA Influencer Marketing Platform")

    # Enable CORS for development and production front‑end.  In production you may restrict origins.
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] ,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Include routers
    app.include_router(auth_router.router)
    app.include_router(brands_router.router)
    app.include_router(campaigns_router.router)
    app.include_router(influencers_router.router)
    # Newly added routers for subscriptions and leads
    from .routers import subscriptions as subscriptions_router
    from .routers import leads as leads_router
    from .routers import tenants as tenants_router
    from .routers import match as match_router
    from .routers import analytics as analytics_router
    app.include_router(subscriptions_router.router)
    app.include_router(leads_router.router)
    app.include_router(tenants_router.router)
    app.include_router(match_router.router)
    app.include_router(analytics_router.router)

    # Startup event to create tables
    @app.on_event("startup")
    async def on_startup() -> None:
        # Create database tables.  In production use migrations instead.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Return a simple health status.

        Cloud platforms can use this endpoint to verify the service is
        running.  It does not perform any database operations and
        returns immediately with a static response.
        """
        return {"status": "ok"}

    return app


app = create_application()
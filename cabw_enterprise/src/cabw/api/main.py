"""FastAPI application for the CABW simulation service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from cabw.api.routers import simulation as simulation_router

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application startup / shutdown logic."""
        # Startup: initialise shared resources here if needed
        yield
        # Shutdown: clean up resources here if needed

    app = FastAPI(
        title="CABW Simulation API",
        description=(
            "REST API for the Cognitive Agent Behavior World (CABW) simulation platform. "
            "Manage simulation runs, agents, and retrieve real-time state snapshots."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # ---------------------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------------------
    # Routers
    # ---------------------------------------------------------------------------
    app.include_router(simulation_router.router, prefix="/api/v1/simulations", tags=["simulations"])

    # ---------------------------------------------------------------------------
    # Health check
    # ---------------------------------------------------------------------------
    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        return {"status": "ok", "service": "cabw-api"}

except ImportError:
    # FastAPI not installed – expose a minimal placeholder so the module is importable
    app = None  # type: ignore[assignment]

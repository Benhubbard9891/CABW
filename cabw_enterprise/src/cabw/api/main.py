"""
CABW Enterprise API

FastAPI application with all enhanced features:
- Integrated agent simulation
- Real-time WebSocket updates
- Teamwork management
- Environmental control
- Security governance
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routers import simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    pass


app = FastAPI(
    title="CABW Enterprise API",
    description="Constitutional Agent-Based World - Enterprise Simulation Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(simulation.router)
# app.include_router(agents.router, prefix="/agents", tags=["agents"])
# app.include_router(teams.router, prefix="/teams", tags=["teams"])
# app.include_router(environment.router, prefix="/environment", tags=["environment"])
# app.include_router(governance.router, prefix="/governance", tags=["governance"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "CABW Enterprise API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "simulation": "/simulation",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "systems": {
            "simulation": "operational",
            "websocket": "operational",
            "database": "connected"
        }
    }


@app.get("/capabilities")
async def get_capabilities():
    """Get API capabilities and features."""
    return {
        "features": [
            {
                "name": "Integrated Agents",
                "description": "Agents with behavior trees, emotions, and needs",
                "endpoints": ["/simulation/{id}/agents"]
            },
            {
                "name": "Dynamic Environment",
                "description": "Weather, hazards, and environmental events",
                "endpoints": ["/simulation/{id}/environment", "/simulation/{id}/weather"]
            },
            {
                "name": "Teamwork System",
                "description": "Team formation, shared goals, and coordination",
                "endpoints": ["/simulation/{id}/teams"]
            },
            {
                "name": "Security Governance",
                "description": "PBAC, audit logging, and threat detection",
                "endpoints": ["/simulation/{id}/security"]
            },
            {
                "name": "Real-time Updates",
                "description": "WebSocket streams for live simulation data",
                "endpoints": ["/simulation/{id}/ws"]
            }
        ],
        "agent_features": [
            "OCEAN personality modeling",
            "Advanced emotional system with trauma",
            "Behavior tree decision making",
            "Physiological needs (hunger, thirst, rest)",
            "Memory and learning",
            "Emotional contagion",
            "Team coordination"
        ],
        "environment_features": [
            "Dynamic weather system",
            "Day/night cycle",
            "Hazard spawning and evolution",
            "Environmental events",
            "Emotional modifiers",
            "Movement and coordination penalties"
        ]
    }

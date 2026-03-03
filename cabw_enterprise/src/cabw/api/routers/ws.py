"""WebSocket router for real-time simulation updates."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cabw.config import settings
from cabw.db.base import db_manager
from cabw.db.models import Simulation, User
from cabw.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Active WebSocket connections
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        # simulation_id -> set of websockets
        self.simulation_connections: dict[UUID, set[WebSocket]] = {}
        # websocket -> user_id
        self.user_connections: dict[WebSocket, UUID] = {}

    async def connect(
        self,
        websocket: WebSocket,
        simulation_id: UUID,
        user_id: UUID
    ) -> None:
        """Accept and store connection."""
        await websocket.accept()

        if simulation_id not in self.simulation_connections:
            self.simulation_connections[simulation_id] = set()

        self.simulation_connections[simulation_id].add(websocket)
        self.user_connections[websocket] = user_id

        logger.info(f"WebSocket connected: {user_id} -> {simulation_id}")

    def disconnect(self, websocket: WebSocket, simulation_id: UUID) -> None:
        """Remove connection."""
        if simulation_id in self.simulation_connections:
            self.simulation_connections[simulation_id].discard(websocket)

            if not self.simulation_connections[simulation_id]:
                del self.simulation_connections[simulation_id]

        self.user_connections.pop(websocket, None)

        logger.info(f"WebSocket disconnected from {simulation_id}")

    async def broadcast_to_simulation(
        self,
        simulation_id: UUID,
        message: dict
    ) -> None:
        """Broadcast message to all connections for a simulation."""
        if simulation_id not in self.simulation_connections:
            return

        disconnected = []
        for websocket in self.simulation_connections[simulation_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket, simulation_id)

    async def send_to_user(
        self,
        websocket: WebSocket,
        message: dict
    ) -> None:
        """Send message to specific user."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket(
    websocket: WebSocket,
    session: AsyncSession
) -> User | None:
    """Authenticate WebSocket connection."""
    # Get token from query params or headers
    token = websocket.query_params.get("token")

    if not token:
        # Try to get from headers
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    except JWTError:
        return None


@router.websocket("/simulations/{simulation_id}")
async def simulation_websocket(
    websocket: WebSocket,
    simulation_id: UUID,
    session: AsyncSession = Depends(db_manager.get_session)
) -> None:
    """WebSocket endpoint for simulation updates."""
    # Authenticate
    user = await authenticate_websocket(websocket, session)

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify simulation exists and belongs to user
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) &
            (Simulation.owner_id == user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect
    await manager.connect(websocket, simulation_id, user.id)

    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "simulation_id": str(simulation_id),
        "status": simulation.status.value,
        "current_tick": simulation.current_tick,
        "max_ticks": simulation.max_ticks
    })

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe":
                    # Subscribe to specific events
                    event_types = message.get("events", [])
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": event_types
                    })

                elif message_type == "get_state":
                    # Refresh simulation state
                    await session.refresh(simulation)
                    await websocket.send_json({
                        "type": "state",
                        "status": simulation.status.value,
                        "current_tick": simulation.current_tick,
                        "agent_count": len(simulation.agents)
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, simulation_id)

    except Exception as e:
        logger.exception("WebSocket error", exc_info=e)
        manager.disconnect(websocket, simulation_id)


# Event broadcaster for simulation events
async def broadcast_simulation_event(
    simulation_id: UUID,
    event_type: str,
    data: dict
) -> None:
    """Broadcast simulation event to all connected clients."""
    await manager.broadcast_to_simulation(simulation_id, {
        "type": event_type,
        "simulation_id": str(simulation_id),
        "data": data
    })


async def broadcast_tick_update(
    simulation_id: UUID,
    tick: int,
    agent_states: list
) -> None:
    """Broadcast tick update."""
    await manager.broadcast_to_simulation(simulation_id, {
        "type": "tick",
        "simulation_id": str(simulation_id),
        "tick": tick,
        "agent_states": agent_states
    })


async def broadcast_agent_action(
    simulation_id: UUID,
    agent_id: UUID,
    action: dict
) -> None:
    """Broadcast agent action."""
    await manager.broadcast_to_simulation(simulation_id, {
        "type": "agent_action",
        "simulation_id": str(simulation_id),
        "agent_id": str(agent_id),
        "action": action
    })


async def broadcast_simulation_status(
    simulation_id: UUID,
    status: str,
    message: str | None = None
) -> None:
    """Broadcast simulation status change."""
    await manager.broadcast_to_simulation(simulation_id, {
        "type": "status_change",
        "simulation_id": str(simulation_id),
        "status": status,
        "message": message
    })

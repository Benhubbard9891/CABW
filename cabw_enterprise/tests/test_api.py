"""
Test suite for CABW Enterprise API Module

Covers:
- Root and health endpoints
- Simulation CRUD endpoints
- Agent listing
- Error handling (404)
"""
import pytest
from httpx import ASGITransport, AsyncClient

from cabw.api.main import app


@pytest.fixture
async def client():
    """Async HTTP test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestRootEndpoints:
    """Tests for root API endpoints."""

    async def test_root_returns_200(self, client):
        response = await client.get("/")
        assert response.status_code == 200

    async def test_root_contains_name(self, client):
        response = await client.get("/")
        data = response.json()
        assert data["name"] == "CABW Enterprise API"

    async def test_root_contains_version(self, client):
        response = await client.get("/")
        data = response.json()
        assert "version" in data

    async def test_root_contains_endpoints(self, client):
        response = await client.get("/")
        data = response.json()
        assert "endpoints" in data

    async def test_health_check_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_check_status_healthy(self, client):
        response = await client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    async def test_health_check_contains_systems(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "systems" in data


class TestSimulationEndpoints:
    """Tests for simulation management endpoints."""

    async def test_create_simulation_returns_201_or_200(self, client):
        payload = {
            "world_size": [10, 10],
            "num_agents": 3,
            "tick_rate": 1.0,
            "max_ticks": 50,
            "security_level": "standard",
            "teamwork_enabled": True,
            "weather_enabled": False,
            "hazards_enabled": False
        }
        response = await client.post("/simulation/create", json=payload)
        assert response.status_code in (200, 201)

    async def test_create_simulation_returns_sim_id(self, client):
        payload = {
            "world_size": [5, 5],
            "num_agents": 2,
            "tick_rate": 1.0,
            "max_ticks": 10,
            "security_level": "standard",
            "teamwork_enabled": False,
            "weather_enabled": False,
            "hazards_enabled": False
        }
        response = await client.post("/simulation/create", json=payload)
        data = response.json()
        assert "simulation_id" in data

    async def test_get_state_returns_404_for_unknown_sim(self, client):
        response = await client.get("/simulation/nonexistent-sim-id/state")
        assert response.status_code == 404

    async def test_list_agents_returns_404_for_unknown_sim(self, client):
        response = await client.get("/simulation/nonexistent-sim-id/agents")
        assert response.status_code == 404

    async def test_stop_returns_404_for_unknown_sim(self, client):
        response = await client.post("/simulation/nonexistent-sim-id/stop")
        assert response.status_code == 404

    async def test_pause_returns_404_for_unknown_sim(self, client):
        response = await client.post("/simulation/nonexistent-sim-id/pause")
        assert response.status_code == 404

    async def test_create_and_get_state(self, client):
        """End-to-end: create simulation then get its state."""
        payload = {
            "world_size": [5, 5],
            "num_agents": 2,
            "tick_rate": 1.0,
            "max_ticks": 10,
            "security_level": "standard",
            "teamwork_enabled": False,
            "weather_enabled": False,
            "hazards_enabled": False
        }
        create_response = await client.post("/simulation/create", json=payload)
        sim_id = create_response.json()["simulation_id"]

        state_response = await client.get(f"/simulation/{sim_id}/state")
        assert state_response.status_code == 200

    async def test_create_and_list_agents(self, client):
        """End-to-end: create simulation then list agents."""
        payload = {
            "world_size": [5, 5],
            "num_agents": 3,
            "tick_rate": 1.0,
            "max_ticks": 10,
            "security_level": "standard",
            "teamwork_enabled": False,
            "weather_enabled": False,
            "hazards_enabled": False
        }
        create_response = await client.post("/simulation/create", json=payload)
        sim_id = create_response.json()["simulation_id"]

        agents_response = await client.get(f"/simulation/{sim_id}/agents")
        assert agents_response.status_code == 200
        agents_data = agents_response.json()
        assert "agents" in agents_data
        assert len(agents_data["agents"]) == 3

    async def test_create_and_stop_simulation(self, client):
        """End-to-end: create and then stop a simulation."""
        payload = {
            "world_size": [5, 5],
            "num_agents": 2,
            "tick_rate": 1.0,
            "max_ticks": 10,
            "security_level": "standard",
            "teamwork_enabled": False,
            "weather_enabled": False,
            "hazards_enabled": False
        }
        create_response = await client.post("/simulation/create", json=payload)
        sim_id = create_response.json()["simulation_id"]

        stop_response = await client.post(f"/simulation/{sim_id}/stop")
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stopped"

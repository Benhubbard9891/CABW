"""
Real-time Dashboard Server for Simulation Metrics
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricSnapshot:
    """Snapshot of simulation metrics at a point in time."""
    timestamp: str
    tick: int
    agent_count: int
    alive_count: int
    team_count: int
    hazard_count: int
    emotional_climate: str
    avg_health: float
    avg_energy: float
    actions_per_tick: int
    events: list[str] = field(default_factory=list)


class MetricsCollector:
    """
    Collect and aggregate simulation metrics.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.history: list[MetricSnapshot] = []
        self.current_metrics: dict[str, Any] = {}

        # Counters
        self.total_actions = 0
        self.total_events = 0
        self.start_time = datetime.now()

    def collect(self, simulation: Any) -> MetricSnapshot:
        """Collect metrics from simulation."""
        state = simulation.get_state()

        # Calculate averages
        agents = state.get('agents', {})
        if agents:
            avg_health = sum(a.get('health', 0) for a in agents.values()) / len(agents)
            avg_energy = sum(a.get('energy', 0) for a in agents.values()) / len(agents)
            alive = sum(1 for a in agents.values() if a.get('alive', False))
        else:
            avg_health = 0
            avg_energy = 0
            alive = 0

        snapshot = MetricSnapshot(
            timestamp=datetime.now().isoformat(),
            tick=state.get('tick', 0),
            agent_count=len(agents),
            alive_count=alive,
            team_count=len(state.get('teams', {})),
            hazard_count=state.get('environment', {}).get('active_hazards', 0),
            emotional_climate=state.get('emotional_climate', {}).get('dominant', 'neutral'),
            avg_health=avg_health,
            avg_energy=avg_energy,
            actions_per_tick=simulation.statistics.get('total_actions', 0) - self.total_actions
        )

        self.total_actions = simulation.statistics.get('total_actions', 0)

        # Store history
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        self.current_metrics = {
            'tick': snapshot.tick,
            'agent_count': snapshot.agent_count,
            'alive_count': snapshot.alive_count,
            'avg_health': snapshot.avg_health,
            'avg_energy': snapshot.avg_energy,
            'emotional_climate': snapshot.emotional_climate
        }

        return snapshot

    def get_time_series(
        self,
        metric_name: str,
        window: int = 100
    ) -> list[tuple]:
        """Get time series data for a metric."""
        data = []
        for snapshot in self.history[-window:]:
            value = getattr(snapshot, metric_name, None)
            if value is not None:
                data.append((snapshot.tick, value))
        return data

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        if not self.history:
            return {}

        recent = self.history[-100:]

        return {
            'simulation_duration': (datetime.now() - self.start_time).total_seconds(),
            'total_ticks': self.history[-1].tick if self.history else 0,
            'avg_agent_count': sum(s.agent_count for s in recent) / len(recent),
            'avg_health': sum(s.avg_health for s in recent) / len(recent),
            'avg_energy': sum(s.avg_energy for s in recent) / len(recent),
            'peak_agents': max(s.agent_count for s in self.history),
            'events_processed': self.total_events
        }


class DashboardServer:
    """
    WebSocket-based dashboard server for real-time metrics.
    """

    def __init__(
        self,
        simulation: Any,
        metrics_collector: MetricsCollector,
        update_interval: float = 1.0
    ):
        self.simulation = simulation
        self.metrics = metrics_collector
        self.update_interval = update_interval

        self.clients: list[Any] = []
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self):
        """Start dashboard server."""
        self.running = True
        self.task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        """Stop dashboard server."""
        self.running = False
        if self.task:
            self.task.cancel()

    async def _broadcast_loop(self):
        """Broadcast metrics to all connected clients."""
        while self.running:
            try:
                # Collect metrics
                snapshot = self.metrics.collect(self.simulation)

                # Broadcast to clients
                message = {
                    'type': 'metrics_update',
                    'timestamp': snapshot.timestamp,
                    'data': {
                        'tick': snapshot.tick,
                        'agent_count': snapshot.agent_count,
                        'alive_count': snapshot.alive_count,
                        'avg_health': snapshot.avg_health,
                        'avg_energy': snapshot.avg_energy,
                        'emotional_climate': snapshot.emotional_climate,
                        'hazard_count': snapshot.hazard_count,
                        'team_count': snapshot.team_count
                    }
                }

                await self._broadcast(message)

                await asyncio.sleep(self.update_interval)

            except Exception as e:
                print(f"Dashboard broadcast error: {e}")
                await asyncio.sleep(self.update_interval)

    async def _broadcast(self, message: dict[str, Any]):
        """Send message to all connected clients."""
        disconnected = []

        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            self.clients.remove(client)

    def add_client(self, client):
        """Add WebSocket client."""
        self.clients.append(client)

        # Send initial state
        asyncio.create_task(self._send_initial_state(client))

    async def _send_initial_state(self, client):
        """Send initial state to new client."""
        try:
            await client.send_json({
                'type': 'initial_state',
                'data': {
                    'simulation': self.simulation.get_state(),
                    'metrics_summary': self.metrics.get_summary()
                }
            })
        except Exception as e:
            print(f"Error sending initial state: {e}")

    def remove_client(self, client):
        """Remove WebSocket client."""
        if client in self.clients:
            self.clients.remove(client)

    def get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CABW Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card h3 {
            margin-top: 0;
            color: #4CAF50;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #333;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-value {
            font-weight: bold;
            color: #FFD700;
        }
        #chart-container {
            height: 200px;
            background: #0f0f23;
            border-radius: 4px;
            margin-top: 10px;
        }
        canvas {
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <h1>CABW Simulation Dashboard</h1>
    <div class="grid">
        <div class="card">
            <h3>Simulation Status</h3>
            <div class="metric">
                <span>Tick:</span>
                <span class="metric-value" id="tick">-</span>
            </div>
            <div class="metric">
                <span>Agents:</span>
                <span class="metric-value" id="agent-count">-</span>
            </div>
            <div class="metric">
                <span>Alive:</span>
                <span class="metric-value" id="alive-count">-</span>
            </div>
            <div class="metric">
                <span>Teams:</span>
                <span class="metric-value" id="team-count">-</span>
            </div>
        </div>

        <div class="card">
            <h3>Agent Health</h3>
            <div class="metric">
                <span>Average Health:</span>
                <span class="metric-value" id="avg-health">-</span>
            </div>
            <div class="metric">
                <span>Average Energy:</span>
                <span class="metric-value" id="avg-energy">-</span>
            </div>
            <div id="health-chart-container">
                <canvas id="health-chart"></canvas>
            </div>
        </div>

        <div class="card">
            <h3>Environment</h3>
            <div class="metric">
                <span>Weather:</span>
                <span class="metric-value" id="weather">-</span>
            </div>
            <div class="metric">
                <span>Active Hazards:</span>
                <span class="metric-value" id="hazard-count">-</span>
            </div>
            <div class="metric">
                <span>Emotional Climate:</span>
                <span class="metric-value" id="climate">-</span>
            </div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/dashboard/ws`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'metrics_update') {
                updateMetrics(data.data);
            } else if (data.type === 'initial_state') {
                updateMetrics(data.data.simulation);
            }
        };

        function updateMetrics(data) {
            document.getElementById('tick').textContent = data.tick || '-';
            document.getElementById('agent-count').textContent = data.agent_count || '-';
            document.getElementById('alive-count').textContent = data.alive_count || '-';
            document.getElementById('team-count').textContent = data.team_count || '-';
            document.getElementById('avg-health').textContent =
                data.avg_health ? data.avg_health.toFixed(1) : '-';
            document.getElementById('avg-energy').textContent =
                data.avg_energy ? data.avg_energy.toFixed(1) : '-';
            document.getElementById('weather').textContent = data.weather || '-';
            document.getElementById('hazard-count').textContent = data.hazard_count || '-';
            document.getElementById('climate').textContent = data.emotional_climate || '-';
        }

        // Simple chart drawing
        const canvas = document.getElementById('health-chart');
        const ctx = canvas.getContext('2d');
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;

        const healthHistory = [];

        function drawChart() {
            ctx.fillStyle = '#0f0f23';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            if (healthHistory.length < 2) return;

            ctx.strokeStyle = '#4CAF50';
            ctx.lineWidth = 2;
            ctx.beginPath();

            const stepX = canvas.width / (healthHistory.length - 1);

            healthHistory.forEach((value, i) => {
                const x = i * stepX;
                const y = canvas.height - (value / 100) * canvas.height;

                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });

            ctx.stroke();
        }

        setInterval(drawChart, 100);
    </script>
</body>
</html>"""

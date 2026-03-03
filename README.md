# CABW Enterprise - Enhanced Agent Simulation Platform

A production-ready, enterprise-grade multi-agent simulation system with advanced AI capabilities, security-first governance, and emergent behavior architecture.

## Overview

CABW (Constitutional Agent-Based World) Enterprise extends the base simulation framework with sophisticated agent behaviors, dynamic environments, teamwork systems, and comprehensive security governance.

### Key Features

| Feature | Description |
|---------|-------------|
| **Integrated Agents** | Full-featured agents with behavior trees, emotions, needs, and memory |
| **Advanced Emotions** | PAD-based emotional system with trauma, regulation, and contagion |
| **Complex Actions** | Actions with preconditions, effects, costs, and composition |
| **Behavior Trees** | Hierarchical decision-making with emergent behavior patterns |
| **Teamwork System** | Dynamic team formation, shared goals, and coordination |
| **Dynamic Environment** | Weather, day/night cycle, hazards, and environmental events |
| **Security Governance** | PBAC (Policy-Based Access Control) with audit logging |
| **Real-time API** | FastAPI with WebSocket support for live updates |
| **Persistence** | Async SQLAlchemy ORM with full state tracking |

## Architecture

```
cabw_enterprise/
├── src/cabw/
│   ├── core/               # Core agent systems
│   │   ├── emotions.py         # Emotional system with contagion
│   │   ├── actions.py          # Complex action framework
│   │   ├── teamwork.py         # Team formation and goals
│   │   ├── behavior_tree.py    # BT nodes and library
│   │   ├── world_features.py   # Environment dynamics
│   │   ├── deliberation.py     # Action deliberation engine (memory→score wire)
│   │   └── integrated_agent.py # Unified agent class
│   ├── simulation/
│   │   ├── engine.py           # Enhanced simulation engine
│   │   └── deterministic.py    # Event-queue deterministic replay engine
│   ├── governance/
│   │   ├── security.py         # Security-first governance (PBAC, audit chain)
│   │   └── enforcement.py      # Execution tokens and constitutional layer
│   ├── ml/
│   │   ├── rl_agents.py        # PPO-style RL for agent policy learning
│   │   ├── behavior_optimization.py # Evolutionary deliberation-weight tuning
│   │   └── nlp_interface.py    # Natural-language command interface
│   ├── economy/
│   │   └── resources.py        # Resource types, pools, and scarcity mechanics
│   ├── api/
│   │   ├── main.py             # FastAPI application
│   │   └── routers/
│   │       └── simulation.py   # API endpoints
│   └── db/
│       └── models.py           # Database models
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── demo_enhanced.py        # Comprehensive demo
```

## Quick Start

### Installation

```bash
# Clone repository
cd cabw_enterprise

# Install dependencies
pip install -e ".[dev]"

# Or with Poetry
poetry install
```

### Run Demo

```bash
# Run comprehensive demo
python demo_enhanced.py

# Run specific demo
python -c "
import asyncio
from demo_enhanced import demo_teamwork
asyncio.run(demo_teamwork())
"
```

### Start API Server

```bash
# Development
uvicorn src.cabw.api.main:app --reload

# Production
uvicorn src.cabw.api.main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build and run
docker-compose up --build

# Scale workers
docker-compose up --scale worker=4
```

## API Endpoints

### Simulation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/simulation/create` | Create new simulation |
| POST | `/simulation/{id}/start` | Start simulation |
| POST | `/simulation/{id}/pause` | Pause simulation |
| POST | `/simulation/{id}/resume` | Resume simulation |
| POST | `/simulation/{id}/stop` | Stop simulation |
| GET | `/simulation/{id}/state` | Get current state |

### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/simulation/{id}/agents` | List all agents |
| POST | `/simulation/{id}/agents` | Add new agent |
| GET | `/simulation/{id}/agents/{agent_id}` | Get agent details |

### Teamwork

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/simulation/{id}/teams` | List teams |
| POST | `/simulation/{id}/teams` | Create team |
| POST | `/simulation/{id}/teams/goal` | Assign goal |

### Environment Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/simulation/{id}/environment` | Environment state |
| POST | `/simulation/{id}/weather` | Control weather |
| POST | `/simulation/{id}/events` | Trigger event |
| GET | `/simulation/{id}/hazards` | List hazards |

### WebSocket Streams

| Endpoint | Description |
|----------|-------------|
| `/simulation/{id}/ws` | Real-time simulation updates |
| `/simulation/{id}/agents/{agent_id}/ws` | Individual agent stream |

## Agent Architecture

### Integrated Agent Components

```python
from src.cabw.core.integrated_agent import IntegratedAgent

# Create agent with personality
agent = IntegratedAgent(
    name="Explorer_1",
    ocean_traits={
        'openness': 0.8,
        'conscientiousness': 0.6,
        'extraversion': 0.7,
        'agreeableness': 0.5,
        'neuroticism': 0.3
    },
    initial_location=(5, 5)
)

# Set behavior tree
agent.set_behavior_tree('agent_ai')

# Agent automatically handles:
# - Emotional responses to environment
# - Physiological needs (hunger, thirst, rest)
# - Memory formation and recall
# - Team coordination
# - Security policy compliance
```

### Behavior Trees

```python
from src.cabw.core.behavior_tree import BehaviorTreeLibrary

# Available behavior trees
library = BehaviorTreeLibrary()
trees = library.list_trees()
# ['combat', 'exploration', 'social', 'agent_ai']

# Create tree with blackboard
tree = library.create_tree('agent_ai', blackboard)

# Tick the tree
status = tree.tick()  # SUCCESS, FAILURE, or RUNNING
```

### Emotional System

```python
from src.cabw.core.emotions import EmotionalState, EmotionType

# Create emotional state
emotions = EmotionalState()

# Apply stimulus
emotions.apply_stimulus(EmotionType.FEAR, 0.6)
emotions.apply_stimulus(EmotionType.JOY, 0.4)

# Get dominant emotion
dominant = emotions.get_dominant_emotion()
valence = emotions.get_valence()
arousal = emotions.get_arousal()

# Trauma tracking
if emotions.trauma_level > 0.7:
    # Agent may develop PTSD triggers
    pass
```

## Teamwork System

### Team Formation

```python
from src.cabw.simulation.engine import EnhancedSimulation

# Teams form automatically when:
# - Hazards require coordination
# - Goals need multiple agents
# - Agents are in proximity

# Or manually create teams
team = simulation.team_manager.create_team(
    name="Rescue_Squad",
    description="Emergency response team"
)

# Add members
from src.cabw.core.teamwork import TeamMember, TeamRole

member = TeamMember(
    agent_id=agent.agent_id,
    role=TeamRole.LEADER,
    coordination_skill=0.8
)
team.add_member(member)
```

### Shared Goals

```python
from src.cabw.core.teamwork import GoalTemplates

# Create goal from template
goal = GoalTemplates.emergency_response(
    description="Contain chemical spill",
    urgency=0.9
)

# Assign to team
simulation.team_manager.assign_goal_to_team(goal, team.team_id)

# Track progress
progress = goal.get_progress()
rewards = goal.calculate_rewards()
```

## Environment System

### Weather Control

```python
from src.cabw.core.world_features import WeatherType

# Set weather
simulation.environment.weather.weather_type = WeatherType.STORM
simulation.environment.weather.intensity = 0.8

# Weather affects:
# - Agent emotions (fear, anxiety)
# - Movement speed
# - Team coordination
# - Visibility
```

### Hazard Management

```python
# Hazards spawn dynamically
hazard = simulation.environment._spawn_hazard()

# Properties
hazard.hazard_type  # FIRE, FLOOD, COLLAPSE, etc.
hazard.severity     # MINOR to CATASTROPHIC
hazard.spread_rate  # How fast it grows

# Containment requires teamwork
if hazard.get_requires_teamwork():
    # Form response team automatically
    pass
```

## Security Governance

### Policy-Based Access Control

```python
from src.cabw.governance.security import (
    SecurityGovernor, SecurityPolicy, Capability, SecurityLevel
)

# Create governor
governor = SecurityGovernor()

# Define policy
policy = SecurityPolicy(
    name='Restricted Actions',
    subject_type='agent',
    resource_type='action',
    capabilities={Capability.ACTION_EXECUTE},
    effect='allow',
    min_security_level=SecurityLevel.CONFIDENTIAL,
)

governor.add_policy(policy)

# Evaluate access — returns AccessDecision (not a tuple)
decision = governor.evaluate_access(
    subject={'id': agent.agent_id, 'type': 'agent'},
    resource={'id': target_id, 'type': 'action'},
    capability=Capability.ACTION_EXECUTE,
    context={'action': 'execute'},
)

if decision.granted:
    print("Access allowed")
else:
    print(f"Access denied: {decision.reason}")
```

### Audit Logging

```python
# All actions are audited
audit_record = governor.audit_log[-1]

# Properties
audit_record.timestamp        # datetime of the event
audit_record.subject_id       # who made the request
audit_record.action           # 'access', 'modify', 'delete', 'create', …
audit_record.decision         # 'allow' or 'deny'
audit_record.decision_reason  # human-readable explanation

# Hash chain — tamper-evident linkage between consecutive records
audit_record.previous_hash    # compute_hash() of the preceding record
audit_record.record_hash      # compute_hash() of this record
audit_record.compute_hash()   # recompute on-demand for verification
```

## Configuration

### Simulation Config

```python
from src.cabw.simulation.engine import SimulationConfig

config = SimulationConfig(
    world_size=(50, 50),
    num_agents=50,
    tick_rate=2.0,
    max_ticks=10000,
    
    # Feature toggles
    teamwork_enabled=True,
    weather_enabled=True,
    hazards_enabled=True,
    
    # Security
    security_level='high',  # low, standard, high, maximum
    audit_all_actions=True,
    
    # Teamwork
    auto_form_teams=True,
    min_team_size=2,
    max_team_size=5
)
```

## WebSocket Example

```javascript
// Connect to simulation stream
const ws = new WebSocket('ws://localhost:8000/simulation/sim_001/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'initial_state':
            console.log('Initial state:', data.data);
            break;
        case 'tick_update':
            updateVisualization(data.data);
            break;
    }
};

// Send commands
ws.send(JSON.stringify({
    command: 'trigger_event',
    event_type: 'earthquake',
    params: { intensity: 0.7 }
}));
```

## Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| Agents | 100+ per simulation |
| Tick Rate | 10+ ticks/second |
| WebSocket Latency | <50ms |
| Database Writes | 1000+ ops/second |
| Memory Usage | ~100MB per 100 agents |

### Scaling

```bash
# Horizontal scaling with Redis
docker-compose -f docker-compose.scale.yml up --scale worker=10

# Database read replicas
# Configure in config.py
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Coverage
pytest --cov=src --cov-report=html

# Load testing
locust -f tests/load/locustfile.py
```

## Monitoring

### Prometheus Metrics

```python
# Available metrics
simulation_agents_total
simulation_ticks_total
agent_actions_total
emotional_contagion_events_total
team_formations_total
hazards_resolved_total
security_violations_total
```

### Grafana Dashboard

Import `monitoring/grafana-dashboard.json` for pre-configured dashboards.

## Development

### Project Structure

```
cabw_enterprise/
├── src/cabw/           # Source code
├── tests/              # Test suite
├── docs/               # Documentation
├── docker/             # Container configs
├── monitoring/         # Observability
└── scripts/            # Utility scripts
```

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

MIT License - See LICENSE file

## Known Constraints

- Simulation is single-threaded; tick performance degrades beyond ~200 agents
- Relationship decay assumes uniform time — no support for subjective time dilation
- Constitutional constraints evaluate sequentially; constraint interaction effects are not modeled
- Memory rehearsal strengthening is capped at `Memory.MAX_REHEARSAL_STRENGTH` (default `5.0`); adjust for your use case

## Acknowledgments

- PAD emotional model: Mehrabian & Russell
- OCEAN personality: Costa & McCrae
- Behavior Trees: Colledanchise & Ögren
- Emergent behavior research community

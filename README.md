<div align="center">

# CABW Enterprise

### Constitutional Agent-Based World - Enterprise Edition

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/Benhubbard9891/CABW)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)]()

**A production-ready, enterprise-grade multi-agent simulation platform with advanced AI capabilities, security-first governance, and emergent behavior architecture.**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [API Reference](#api-reference) • [Contributing](#contributing)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
  - [Core Agent Systems](#core-agent-systems)
  - [Governance & Security](#governance--security)
  - [Simulation Engine](#simulation-engine)
  - [Machine Learning](#machine-learning)
  - [Visualization](#visualization)
  - [Distributed Computing](#distributed-computing)
  - [Economy System](#economy-system)
  - [World Generation](#world-generation)
  - [REST API & WebSocket](#rest-api--websocket)
- [Quick Start](#quick-start)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Running the Demo](#running-the-demo)
  - [Starting the API Server](#starting-the-api-server)
  - [Docker Deployment](#docker-deployment)
- [Documentation](#documentation)
  - [Architecture](#architecture)
  - [Agent Architecture](#agent-architecture)
  - [Behavior Trees](#behavior-trees)
  - [Emotional System](#emotional-system)
  - [Teamwork System](#teamwork-system)
  - [Environment System](#environment-system)
  - [Security Governance](#security-governance)
  - [Configuration](#configuration)
- [API Reference](#api-reference)
- [Performance](#performance)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Known Constraints](#known-constraints)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

CABW (Constitutional Agent-Based World) Enterprise is a comprehensive multi-agent simulation framework designed for research, development, and production deployments. It combines sophisticated agent behaviors, dynamic environments, teamwork systems, and security-first governance into a unified, extensible platform.

The platform is built around a **constitutional governance model** where security and policy enforcement are structurally unavoidable—not optional advisory functions that agents can bypass.

---

## Features

### Core Agent Systems

| Feature | Description |
|---------|-------------|
| **Integrated Agents** | Full-featured agents with behavior trees, emotions, needs, and memory |
| **Advanced Emotions** | PAD-based emotional system with 20 emotions, trauma tracking, and contagion |
| **Complex Actions** | Actions with preconditions, effects, costs, and composition |
| **Behavior Trees** | 10+ node types for hierarchical decision-making with emergent patterns |
| **Teamwork System** | Dynamic team formation, 5 roles, shared goals, and coordination bonuses |
| **Physiological Needs** | Hunger, thirst, rest, safety, social, and achievement drives |
| **OCEAN Personality** | Big Five personality traits influencing all agent behaviors |
| **Dynamic Environment** | Weather (8 types), day/night cycle, seasons, and hazards (8 types) |

### Governance & Security

| Feature | Description |
|---------|-------------|
| **Constitutional Layer** | Structural enforcement—no action executes without authorization |
| **PBAC** | Policy-Based Access Control with 4 security levels and 10 capabilities |
| **Execution Tokens** | Single-use, immutable authorization for every action |
| **Tamper-Evident Audit** | Hash-chained audit logs for complete traceability |
| **JWT Authentication** | Secure API access with role-based permissions (VIEWER, OPERATOR, ADMIN, SYSTEM) |
| **Rate Limiting** | Per-subject rate limiting with automatic blocking |

### Simulation Engine

| Feature | Description |
|---------|-------------|
| **Deterministic Replay** | Seeded RNG + event-queue architecture for reproducible simulations |
| **Event Queue** | Serial event processing eliminates race conditions |
| **State Snapshots** | Export and restore complete simulation state |
| **Configurable Tick Rate** | Adjustable simulation speed (default: 2.0 ticks/second) |

### Machine Learning

| Feature | Description |
|---------|-------------|
| **Reinforcement Learning** | PPO-style RL with adaptive OCEAN traits |
| **Behavior Optimization** | Evolutionary algorithm for deliberation weight tuning |
| **NLP Interface** | Natural language command processing and agent dialogue |
| **Deliberation Engine** | 7-factor action scoring (personality, emotion, memory, relationship, need, environment, social) |

### Visualization

| Feature | Description |
|---------|-------------|
| **3D Renderer** | Three.js-based visualization with real-time updates |
| **Dashboard** | WebSocket-powered metrics dashboard |
| **Emotion Indicators** | Color-coded emotional state visualization |
| **Path Visualization** | Agent movement tracking |

### Distributed Computing

| Feature | Description |
|---------|-------------|
| **Redis Messaging** | Pub/sub messaging for multi-node deployments |
| **Agent Migration** | Transfer agents between simulation nodes |
| **Synchronization** | Cross-node state synchronization |
| **Heartbeat Monitoring** | Node health tracking |

### Economy System

| Feature | Description |
|---------|-------------|
| **8 Resource Types** | Food, water, medicine, fuel, materials, tools, information, currency |
| **Resource Pools** | Location-based deposits with extraction and regeneration |
| **Scarcity Mechanics** | Global and local scarcity tracking affects agent behavior |
| **Quality & Durability** | Resources have quality levels and degradation |

### World Generation

| Feature | Description |
|---------|-------------|
| **Procedural Terrain** | Perlin noise-based terrain generation |
| **10 Terrain Types** | Deep water, shallow water, beach, plains, forest, hills, mountains, snow, desert, swamp |
| **Biome System** | Temperature and moisture-based biome generation |
| **Spawn Location Finding** | Intelligent agent spawn point selection |

### REST API & WebSocket

| Feature | Description |
|---------|-------------|
| **FastAPI Backend** | High-performance async API |
| **Real-time Updates** | WebSocket streams for live simulation data |
| **Full CRUD** | Complete simulation, agent, and team management |
| **Async SQLAlchemy** | Database persistence with PostgreSQL/SQLite support |

---

## Quick Start

### Requirements

- **Python**: 3.10, 3.11, or 3.12
- **Database**: PostgreSQL (recommended) or SQLite
- **Cache**: Redis (optional, for distributed mode)
- **OS**: Linux, macOS, or Windows

### Installation

```bash
# Clone the repository
git clone https://github.com/Benhubbard9891/CABW.git
cd CABW

# Install with pip
pip install -e ".[dev]"

# Or with Poetry
poetry install

# Install all optional dependencies
pip install -e ".[all]"
```

### Running the Demo

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

### Starting the API Server

```bash
# Development (with auto-reload)
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

# Horizontal scaling with Redis
docker-compose -f docker-compose.scale.yml up --scale worker=10
```

---

## Documentation

### Architecture

```
cabw_enterprise/
├── src/cabw/
│   ├── core/                   # Core agent systems
│   │   ├── emotions.py             # PAD emotional system with contagion
│   │   ├── actions.py              # Complex action framework
│   │   ├── teamwork.py             # Team formation and goals
│   │   ├── behavior_tree.py        # BT nodes and library
│   │   ├── world_features.py       # Environment dynamics
│   │   ├── deliberation.py         # Action deliberation engine
│   │   └── integrated_agent.py     # Unified agent class
│   ├── simulation/
│   │   ├── engine.py               # Enhanced simulation engine
│   │   └── deterministic.py        # Deterministic replay engine
│   ├── governance/
│   │   ├── security.py             # PBAC and audit chain
│   │   └── enforcement.py          # Constitutional layer
│   ├── ml/
│   │   ├── rl_agents.py            # Reinforcement learning
│   │   ├── behavior_optimization.py # Evolutionary optimization
│   │   └── nlp_interface.py        # Natural language interface
│   ├── viz/
│   │   ├── renderer.py             # Three.js 3D visualization
│   │   └── dashboard.py            # Real-time dashboard
│   ├── distributed/
│   │   └── messenger.py            # Redis pub/sub messaging
│   ├── economy/
│   │   └── resources.py            # Economic system
│   ├── worldgen/
│   │   └── terrain.py              # Procedural generation
│   ├── api/
│   │   ├── main.py                 # FastAPI application
│   │   ├── auth.py                 # JWT authentication
│   │   └── routers/
│   │       ├── simulation.py       # API endpoints
│   │       └── simulation_secure.py # Authenticated endpoints
│   └── db/
│       └── models.py               # Database models
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                      # Test suite
└── demo_enhanced.py            # Comprehensive demo
```

#### Integrated Agent Components

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

### Teamwork System

#### Team Formation

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

#### Shared Goals

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

### Environment System

#### Weather Control

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

#### Hazard Management

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

### Security Governance

#### Policy-Based Access Control

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

#### Audit Logging

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

### Configuration

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

### WebSocket Example

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

---

## API Reference

### Authentication

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/simulation/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### Simulation Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/simulation/create` | Create new simulation | Yes (CREATE) |
| POST | `/simulation/{id}/start` | Start simulation | Yes (EXECUTE) |
| POST | `/simulation/{id}/pause` | Pause simulation | Yes (EXECUTE) |
| POST | `/simulation/{id}/resume` | Resume simulation | Yes (EXECUTE) |
| POST | `/simulation/{id}/stop` | Stop simulation | Yes (EXECUTE) |
| GET | `/simulation/{id}/state` | Get current state | Yes (READ) |
| POST | `/simulation/{id}/export` | Export simulation state | Yes (READ) |
| POST | `/simulation/{id}/replay` | Replay from event log | Yes (EXECUTE) |
| GET | `/simulation/{id}/audit` | Get audit trail | Yes (ADMIN) |

### Agent Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/simulation/{id}/agents` | List all agents | Yes (READ) |
| POST | `/simulation/{id}/agents` | Add new agent | Yes (CREATE) |
| GET | `/simulation/{id}/agents/{agent_id}` | Get agent details | Yes (READ) |
| POST | `/simulation/{id}/agents/{agent_id}/action` | Execute agent action | Yes (EXECUTE) |

### Team Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/simulation/{id}/teams` | List teams | Yes (READ) |
| POST | `/simulation/{id}/teams` | Create team | Yes (CREATE) |
| POST | `/simulation/{id}/teams/goal` | Assign goal | Yes (EXECUTE) |

### Environment Control

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/simulation/{id}/environment` | Environment state | Yes (READ) |
| POST | `/simulation/{id}/weather` | Control weather | Yes (EXECUTE) |
| POST | `/simulation/{id}/events` | Trigger event | Yes (EXECUTE) |
| GET | `/simulation/{id}/hazards` | List hazards | Yes (READ) |

### WebSocket Streams

| Endpoint | Description |
|----------|-------------|
| `/simulation/{id}/ws` | Real-time simulation updates |
| `/simulation/{id}/agents/{agent_id}/ws` | Individual agent stream |

---

## Performance

### Benchmarks

> Tested on: AMD Ryzen 9 5900X, 32GB RAM, Ubuntu 22.04, Python 3.11

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

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/ -v -m unit
pytest tests/ -v -m integration
pytest tests/ -v -m e2e

# Load testing
locust -f tests/load/locustfile.py
```

---

## Monitoring

### Prometheus Metrics

```
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

---

## Known Constraints

| Constraint | Details |
|------------|---------|
| **Single-threaded Simulation** | Tick performance degrades beyond ~200 agents |
| **Uniform Time** | Relationship decay assumes uniform time — no subjective time dilation |
| **Sequential Constraints** | Constitutional constraints evaluate sequentially; interaction effects not modeled |
| **Memory Cap** | Rehearsal strengthening capped at `Memory.MAX_REHEARSAL_STRENGTH` (default `5.0`) |

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **PAD Emotional Model**: Mehrabian & Russell
- **OCEAN Personality**: Costa & McCrae
- **Behavior Trees**: Colledanchise & Ögren
- **Emergent Behavior Research Community**

---

<div align="center">

**[Back to Top](#cabw-enterprise)**

Made with ❤️ by the CABW Development Team

</div>

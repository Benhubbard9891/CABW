# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CABW (Constitutional Agent-Based World) Enterprise — a multi-agent simulation platform with a FastAPI backend, async SQLAlchemy persistence, and a PBAC security governance layer. Python 3.10–3.12, source in `src/cabw/`.

## Commands

```bash
# Create venv (system Python is externally managed on this machine)
python3 -m venv .venv

# Install (dev)
.venv/bin/pip install -e ".[dev]"

# Run API server
.venv/bin/uvicorn src.cabw.api.main:app --reload

# Run all tests
.venv/bin/pytest tests/ -v

# Run a single test file
.venv/bin/pytest tests/test_core.py -v

# Run tests by marker
.venv/bin/pytest tests/ -v -m unit
.venv/bin/pytest tests/ -v -m integration

# With coverage
.venv/bin/pytest tests/ -v --cov=src --cov-report=html

# Lint / format check
.venv/bin/ruff check src tests
.venv/bin/black --check src tests

# Type check
.venv/bin/mypy src

# Security scan
.venv/bin/bandit -r src -f json
```

**Code style**: Black with 100-char line length. Strict mypy (`disallow_untyped_defs=true`). Ruff rules: E, F, I, N, W, UP, B, C4, SIM. Google-style docstrings.

## Architecture

### Agent Model (`src/cabw/core/`)

`integrated_agent.py` is the unified agent class that composes all subsystems:
- **Personality**: OCEAN 5-factor model
- **Emotions**: PAD system (Pleasure/Arousal/Dominance) with trauma tracking and emotional contagion between nearby agents (`emotions.py`)
- **Needs**: Physiological/social/achievement needs that decay over time
- **Memory**: Short/long-term with importance scoring and relevance recall
- **Decision-making**: Behavior trees (`behavior_tree.py`) with a library of pre-built trees; `deliberation.py` handles higher-level goal selection
- **Actions**: Composable actions with preconditions, effects, and resource costs (`actions.py`)
- **Teamwork**: Dynamic team formation, leader/supporter/specialist/scout roles, shared goals (`teamwork.py`)

### Environment (`src/cabw/core/world_features.py`)

Tick-based world with a spatial grid: weather (affects agent emotions/movement), day/night cycle, dynamically spreading hazards (fire, flood, collapse), and random environmental events that trigger agent responses.

### Simulation Engine (`src/cabw/simulation/engine.py`)

Drives the tick loop, manages agent lifecycle, fires event callbacks (on-tick, agent-action, environmental-event). `deterministic.py` provides seeded, reproducible mode. Supports 100+ agents with async batch processing.

### API Layer (`src/cabw/api/`)

FastAPI app (`main.py`) with lifespan startup/shutdown, CORS, and health checks. JWT auth (`auth.py`). Pydantic schemas (`schemas.py`). Routers:
- `simulation.py` / `simulations.py` — simulation CRUD
- `simulation_secure.py` — security-enforced simulation operations
- `auth.py` — token endpoints
- `ws.py` — WebSocket for real-time simulation state

### Security & Governance (`src/cabw/governance/`)

PBAC (Policy-Based Access Control) in `security.py`: capabilities (EXECUTE/READ/WRITE/DELETE), policy rule evaluation, tamper-evident audit log with hash chains, anomaly detection. `enforcement.py` wraps simulation operations with policy checks.

### Configuration (`src/cabw/config.py`)

Pydantic Settings modules prefixed by domain (`DB_`, `API_`, `SIM_`, `AUTH_`, etc.). Copy `.env.example` to `.env` to configure locally.

### Infrastructure

Full Docker Compose stack (`docker/docker-compose.yml`): PostgreSQL 16, Redis 7, RabbitMQ 3, API service, Celery worker. Async SQLAlchemy with asyncpg for PostgreSQL and aiosqlite for tests/lightweight use.

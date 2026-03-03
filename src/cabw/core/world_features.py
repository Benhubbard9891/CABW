"""
Dynamic World Features Module

Environmental systems that affect agent emotions, actions, and teamwork:
- Weather system with emotional and physical effects
- Day/night cycle affecting visibility and behavior patterns
- Dynamic hazard spawning and evolution
- Environmental events that require team coordination
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any


class WeatherType(Enum):
    """Weather conditions with varying intensity."""
    CLEAR = auto()
    CLOUDY = auto()
    RAIN = auto()
    STORM = auto()
    SNOW = auto()
    FOG = auto()
    HEAT_WAVE = auto()
    BLIZZARD = auto()


class TimeOfDay(Enum):
    """Time periods affecting agent behavior."""
    DAWN = auto()      # 5:00 - 8:00
    MORNING = auto()   # 8:00 - 12:00
    AFTERNOON = auto() # 12:00 - 17:00
    DUSK = auto()      # 17:00 - 20:00
    NIGHT = auto()     # 20:00 - 5:00


class Season(Enum):
    """Seasons affecting environmental conditions."""
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()


class HazardType(Enum):
    """Types of dynamic hazards."""
    FIRE = auto()
    FLOOD = auto()
    COLLAPSE = auto()
    CONTAMINATION = auto()
    ELECTRICAL = auto()
    BIOHAZARD = auto()
    STRUCTURAL = auto()
    WILDLIFE = auto()


class HazardSeverity(Enum):
    """Hazard severity levels."""
    MINOR = 1
    MODERATE = 2
    MAJOR = 3
    CRITICAL = 4
    CATASTROPHIC = 5


@dataclass
class WeatherState:
    """Current weather conditions with effects."""
    weather_type: WeatherType = WeatherType.CLEAR
    intensity: float = 0.5  # 0.0 to 1.0
    temperature: float = 20.0  # Celsius
    humidity: float = 0.5
    wind_speed: float = 0.0  # km/h
    visibility: float = 1.0  # 0.0 to 1.0

    # Emotional effects on agents
    emotional_modifiers: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self._calculate_emotional_modifiers()

    def _calculate_emotional_modifiers(self):
        """Calculate emotional modifiers based on weather."""
        modifiers = {
            'joy': 0.0, 'sadness': 0.0, 'anger': 0.0,
            'fear': 0.0, 'anxiety': 0.0, 'energy': 0.0
        }

        if self.weather_type == WeatherType.CLEAR:
            modifiers['joy'] = 0.2 * self.intensity
            modifiers['energy'] = 0.15
        elif self.weather_type == WeatherType.RAIN:
            modifiers['sadness'] = 0.15 * self.intensity
            modifiers['energy'] = -0.1
        elif self.weather_type == WeatherType.STORM:
            modifiers['fear'] = 0.2 * self.intensity
            modifiers['anxiety'] = 0.25 * self.intensity
            modifiers['energy'] = -0.15
        elif self.weather_type == WeatherType.FOG:
            modifiers['anxiety'] = 0.1 * self.intensity
            modifiers['fear'] = 0.05 * self.intensity
        elif self.weather_type == WeatherType.HEAT_WAVE:
            modifiers['anger'] = 0.15 * self.intensity
            modifiers['energy'] = -0.2
        elif self.weather_type == WeatherType.SNOW:
            modifiers['sadness'] = 0.1 * self.intensity
            modifiers['energy'] = -0.15
        elif self.weather_type == WeatherType.BLIZZARD:
            modifiers['fear'] = 0.3 * self.intensity
            modifiers['anxiety'] = 0.2 * self.intensity
            modifiers['energy'] = -0.25

        self.emotional_modifiers = modifiers

    def get_movement_penalty(self) -> float:
        """Get movement speed penalty (0.0 to 1.0)."""
        penalties = {
            WeatherType.CLEAR: 0.0,
            WeatherType.CLOUDY: 0.0,
            WeatherType.RAIN: 0.1 * self.intensity,
            WeatherType.STORM: 0.25 * self.intensity,
            WeatherType.SNOW: 0.15 * self.intensity,
            WeatherType.FOG: 0.1 * self.intensity,
            WeatherType.HEAT_WAVE: 0.05 * self.intensity,
            WeatherType.BLIZZARD: 0.4 * self.intensity
        }
        return penalties.get(self.weather_type, 0.0)

    def get_coordination_penalty(self) -> float:
        """Get teamwork coordination penalty."""
        penalties = {
            WeatherType.CLEAR: 0.0,
            WeatherType.CLOUDY: 0.0,
            WeatherType.RAIN: 0.05,
            WeatherType.STORM: 0.2,
            WeatherType.SNOW: 0.1,
            WeatherType.FOG: 0.15,
            WeatherType.HEAT_WAVE: 0.05,
            WeatherType.BLIZZARD: 0.3
        }
        return penalties.get(self.weather_type, 0.0) * self.intensity


@dataclass
class Hazard:
    """Dynamic hazard in the world."""
    hazard_id: str
    hazard_type: HazardType
    severity: HazardSeverity
    location: tuple[int, int]
    radius: float  # Affected radius

    # Dynamic properties
    spread_rate: float = 0.0  # How fast it grows
    decay_rate: float = 0.0   # How fast it resolves

    # Effects
    health_damage: float = 0.0
    emotional_impact: dict[str, float] = field(default_factory=dict)

    # State
    active: bool = True
    age_ticks: int = 0
    contained: bool = False
    containment_progress: float = 0.0

    def tick(self) -> list[str]:
        """Advance hazard state, return events."""
        events = []
        self.age_ticks += 1

        if self.contained:
            self.containment_progress += 0.1
            if self.containment_progress >= 1.0:
                self.active = False
                events.append(f"hazard_resolved:{self.hazard_id}")
        elif self.spread_rate > 0:
            # Hazard spreads
            if random.random() < self.spread_rate:
                self.radius += 0.5
                events.append(f"hazard_spread:{self.hazard_id}")

        # Natural decay
        if self.decay_rate > 0 and random.random() < self.decay_rate:
            self.severity = HazardSeverity(max(1, self.severity.value - 1))
            if self.severity == HazardSeverity.MINOR:
                self.active = False
                events.append(f"hazard_dissipated:{self.hazard_id}")

        return events

    def attempt_containment(self, effort: float, team_coordination: float) -> bool:
        """Attempt to contain the hazard."""
        base_chance = effort * (1 + team_coordination)
        severity_modifier = 1.0 / self.severity.value

        if random.random() < base_chance * severity_modifier:
            self.contained = True
            return True
        return False

    def get_requires_teamwork(self) -> bool:
        """Check if hazard requires team coordination."""
        return self.severity.value >= HazardSeverity.MAJOR.value


@dataclass
class EnvironmentalEvent:
    """Special environmental events requiring response."""
    event_id: str
    name: str
    description: str
    affected_zones: list[tuple[int, int]]

    # Effects
    emotional_effects: dict[str, float] = field(default_factory=dict)
    action_restrictions: list[str] = field(default_factory=list)

    # Teamwork requirements
    requires_teamwork: bool = False
    min_team_size: int = 1
    optimal_team_size: int = 1

    # Duration
    duration_ticks: int = 10
    elapsed_ticks: int = 0

    # State
    active: bool = True
    resolved: bool = False

    def tick(self) -> dict[str, Any]:
        """Advance event state."""
        self.elapsed_ticks += 1

        if self.elapsed_ticks >= self.duration_ticks:
            self.active = False
            return {'event': 'expired', 'event_id': self.event_id}

        return {'event': 'continuing', 'event_id': self.event_id}

    def resolve(self, team_effectiveness: float) -> dict[str, Any]:
        """Attempt to resolve the event through teamwork."""
        if not self.requires_teamwork:
            self.resolved = True
            self.active = False
            return {'success': True, 'reward': 1.0}

        # Teamwork required
        if team_effectiveness >= 0.6:
            self.resolved = True
            self.active = False
            return {
                'success': True,
                'reward': team_effectiveness,
                'team_bonus': team_effectiveness - 0.5
            }

        return {'success': False, 'reward': 0.0}


class WorldEnvironment:
    """Manages all environmental conditions and events."""

    def __init__(self, world_size: tuple[int, int] = (10, 10)):
        self.world_size = world_size

        # Time tracking
        self.current_time = datetime(2024, 1, 1, 8, 0)
        self.time_scale = 60  # 1 real second = 1 game minute
        self.tick_count = 0

        # Weather
        self.weather = WeatherState()
        self.weather_history: list[WeatherState] = []
        self.weather_transition_probability = 0.05

        # Season
        self.season = Season.SPRING

        # Hazards
        self.hazards: dict[str, Hazard] = {}
        self.hazard_spawn_probability = 0.02

        # Events
        self.events: dict[str, EnvironmentalEvent] = {}
        self.event_history: list[str] = []

        # Callbacks
        self.on_weather_change: Callable | None = None
        self.on_hazard_spawn: Callable | None = None
        self.on_event_trigger: Callable | None = None

        # Environmental modifiers cache
        self._modifier_cache: dict[str, float] = {}
        self._cache_valid = False

    def get_time_of_day(self) -> TimeOfDay:
        """Get current time period."""
        hour = self.current_time.hour
        if 5 <= hour < 8:
            return TimeOfDay.DAWN
        elif 8 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 20:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT

    def get_visibility(self) -> float:
        """Get current visibility (0.0 to 1.0)."""
        base_visibility = self.weather.visibility

        time_modifiers = {
            TimeOfDay.DAWN: 0.8,
            TimeOfDay.MORNING: 1.0,
            TimeOfDay.AFTERNOON: 1.0,
            TimeOfDay.DUSK: 0.7,
            TimeOfDay.NIGHT: 0.3
        }

        return base_visibility * time_modifiers.get(self.get_time_of_day(), 0.5)

    def get_emotional_modifiers(self) -> dict[str, float]:
        """Get combined emotional modifiers from environment."""
        modifiers = dict(self.weather.emotional_modifiers)

        # Time of day effects
        time_effects = {
            TimeOfDay.DAWN: {'energy': 0.1},
            TimeOfDay.MORNING: {'energy': 0.2, 'joy': 0.1},
            TimeOfDay.AFTERNOON: {'energy': 0.1},
            TimeOfDay.DUSK: {'anxiety': 0.05},
            TimeOfDay.NIGHT: {'fear': 0.1, 'anxiety': 0.1, 'energy': -0.1}
        }

        for emotion, value in time_effects.get(self.get_time_of_day(), {}).items():
            modifiers[emotion] = modifiers.get(emotion, 0.0) + value

        # Hazard effects
        for hazard in self.hazards.values():
            if hazard.active:
                for emotion, value in hazard.emotional_impact.items():
                    modifiers[emotion] = modifiers.get(emotion, 0.0) + value * hazard.severity.value / 5

        return modifiers

    def tick(self) -> dict[str, Any]:
        """Advance environment state."""
        self.tick_count += 1
        results = {
            'time_advanced': False,
            'weather_changed': False,
            'hazards': [],
            'events': [],
            'new_hazards': [],
            'new_events': []
        }

        # Advance time
        self.current_time += timedelta(minutes=10)
        results['time_advanced'] = True

        # Weather transitions
        if random.random() < self.weather_transition_probability:
            self._transition_weather()
            results['weather_changed'] = True

        # Update hazards
        for hazard in list(self.hazards.values()):
            events = hazard.tick()
            results['hazards'].extend(events)

            if not hazard.active:
                del self.hazards[hazard.hazard_id]

        # Spawn new hazards
        if random.random() < self.hazard_spawn_probability:
            hazard = self._spawn_hazard()
            if hazard:
                results['new_hazards'].append(hazard.hazard_id)

        # Update events
        for event in list(self.events.values()):
            status = event.tick()
            results['events'].append(status)

            if not event.active:
                del self.events[event.event_id]

        # Invalidate cache
        self._cache_valid = False

        return results

    def _transition_weather(self):
        """Transition to new weather state."""
        self.weather_history.append(self.weather)

        # Weather transition matrix
        transitions = {
            WeatherType.CLEAR: [WeatherType.CLOUDY, WeatherType.CLEAR],
            WeatherType.CLOUDY: [WeatherType.CLEAR, WeatherType.RAIN, WeatherType.CLOUDY],
            WeatherType.RAIN: [WeatherType.CLOUDY, WeatherType.STORM, WeatherType.RAIN],
            WeatherType.STORM: [WeatherType.RAIN, WeatherType.STORM, WeatherType.CLEAR],
            WeatherType.FOG: [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.FOG],
            WeatherType.SNOW: [WeatherType.CLOUDY, WeatherType.BLIZZARD, WeatherType.SNOW],
            WeatherType.BLIZZARD: [WeatherType.SNOW, WeatherType.BLIZZARD],
            WeatherType.HEAT_WAVE: [WeatherType.CLEAR, WeatherType.HEAT_WAVE]
        }

        possible = transitions.get(self.weather.weather_type, [WeatherType.CLEAR])
        new_type = random.choice(possible)

        self.weather = WeatherState(
            weather_type=new_type,
            intensity=random.uniform(0.3, 1.0),
            temperature=self._get_seasonal_temperature(new_type),
            humidity=random.uniform(0.2, 0.9),
            wind_speed=random.uniform(0, 50) if new_type in [WeatherType.STORM, WeatherType.BLIZZARD] else random.uniform(0, 20)
        )

        if self.on_weather_change:
            self.on_weather_change(self.weather)

    def _get_seasonal_temperature(self, weather_type: WeatherType) -> float:
        """Get temperature based on season and weather."""
        base_temps = {
            Season.SPRING: 15.0,
            Season.SUMMER: 25.0,
            Season.AUTUMN: 12.0,
            Season.WINTER: 0.0
        }

        base = base_temps.get(self.season, 15.0)

        modifiers = {
            WeatherType.CLEAR: 0.0,
            WeatherType.CLOUDY: -2.0,
            WeatherType.RAIN: -5.0,
            WeatherType.STORM: -8.0,
            WeatherType.SNOW: -10.0,
            WeatherType.FOG: -3.0,
            WeatherType.HEAT_WAVE: 15.0,
            WeatherType.BLIZZARD: -20.0
        }

        return base + modifiers.get(weather_type, 0.0) + random.uniform(-3, 3)

    def _spawn_hazard(self) -> Hazard | None:
        """Spawn a new hazard."""
        hazard_configs = {
            HazardType.FIRE: {
                'radius': 2.0, 'spread_rate': 0.1, 'health_damage': 10.0,
                'emotional_impact': {'fear': 0.3, 'anxiety': 0.2}
            },
            HazardType.FLOOD: {
                'radius': 5.0, 'spread_rate': 0.05, 'health_damage': 5.0,
                'emotional_impact': {'fear': 0.2, 'sadness': 0.1}
            },
            HazardType.COLLAPSE: {
                'radius': 3.0, 'spread_rate': 0.0, 'health_damage': 20.0,
                'emotional_impact': {'fear': 0.4, 'anxiety': 0.3}
            },
            HazardType.ELECTRICAL: {
                'radius': 1.0, 'spread_rate': 0.02, 'health_damage': 15.0,
                'emotional_impact': {'fear': 0.25, 'anxiety': 0.15}
            },
            HazardType.BIOHAZARD: {
                'radius': 4.0, 'spread_rate': 0.03, 'health_damage': 8.0,
                'emotional_impact': {'fear': 0.35, 'disgust': 0.2}
            }
        }

        hazard_type = random.choice(list(hazard_configs.keys()))
        config = hazard_configs[hazard_type]

        hazard = Hazard(
            hazard_id=f"hazard_{self.tick_count}_{random.randint(1000, 9999)}",
            hazard_type=hazard_type,
            severity=random.choice(list(HazardSeverity)),
            location=(random.randint(0, self.world_size[0]-1),
                     random.randint(0, self.world_size[1]-1)),
            **config
        )

        self.hazards[hazard.hazard_id] = hazard

        if self.on_hazard_spawn:
            self.on_hazard_spawn(hazard)

        return hazard

    def create_event(self, event_type: str, **kwargs) -> EnvironmentalEvent:
        """Create a new environmental event."""
        event_templates = {
            'earthquake': {
                'name': 'Earthquake',
                'description': 'Seismic activity detected. Structural damage possible.',
                'emotional_effects': {'fear': 0.5, 'anxiety': 0.4},
                'requires_teamwork': True,
                'min_team_size': 3,
                'optimal_team_size': 5,
                'duration_ticks': 20
            },
            'power_outage': {
                'name': 'Power Outage',
                'description': 'Electrical systems offline. Limited visibility.',
                'emotional_effects': {'anxiety': 0.3, 'fear': 0.2},
                'action_restrictions': ['use_electronics'],
                'requires_teamwork': True,
                'min_team_size': 2,
                'optimal_team_size': 4,
                'duration_ticks': 15
            },
            'contamination': {
                'name': 'Contamination Alert',
                'description': 'Hazardous substance detected. Evacuation may be necessary.',
                'emotional_effects': {'fear': 0.4, 'disgust': 0.3, 'anxiety': 0.3},
                'requires_teamwork': True,
                'min_team_size': 4,
                'optimal_team_size': 6,
                'duration_ticks': 25
            },
            'rescue_needed': {
                'name': 'Rescue Operation',
                'description': 'Agent trapped. Immediate assistance required.',
                'emotional_effects': {'urgency': 0.5, 'anxiety': 0.3},
                'requires_teamwork': True,
                'min_team_size': 2,
                'optimal_team_size': 3,
                'duration_ticks': 10
            }
        }

        template = event_templates.get(event_type, {
            'name': 'Unknown Event',
            'description': 'An event has occurred.',
            'emotional_effects': {},
            'requires_teamwork': False,
            'duration_ticks': 5
        })

        template.update(kwargs)

        event = EnvironmentalEvent(
            event_id=f"event_{self.tick_count}_{random.randint(1000, 9999)}",
            affected_zones=[(random.randint(0, self.world_size[0]-1),
                           random.randint(0, self.world_size[1]-1))],
            **template
        )

        self.events[event.event_id] = event

        if self.on_event_trigger:
            self.on_event_trigger(event)

        return event

    def get_active_threats(self, location: tuple[int, int] | None = None) -> list[Hazard]:
        """Get active hazards, optionally filtered by location."""
        threats = [h for h in self.hazards.values() if h.active]

        if location:
            threats = [
                h for h in threats
                if math.sqrt((h.location[0] - location[0])**2 +
                           (h.location[1] - location[1])**2) <= h.radius
            ]

        return threats

    def get_environmental_summary(self) -> dict[str, Any]:
        """Get summary of current environmental state."""
        return {
            'time': self.current_time.isoformat(),
            'time_of_day': self.get_time_of_day().name,
            'season': self.season.name,
            'weather': {
                'type': self.weather.weather_type.name,
                'intensity': self.weather.intensity,
                'temperature': self.weather.temperature,
                'visibility': self.get_visibility()
            },
            'emotional_modifiers': self.get_emotional_modifiers(),
            'active_hazards': len([h for h in self.hazards.values() if h.active]),
            'active_events': len([e for e in self.events.values() if e.active]),
            'movement_penalty': self.weather.get_movement_penalty(),
            'coordination_penalty': self.weather.get_coordination_penalty()
        }


class EnvironmentEffectSystem:
    """Applies environmental effects to agents and teams."""

    def __init__(self, environment: WorldEnvironment):
        self.environment = environment

    def apply_to_agent(self, agent) -> dict[str, Any]:
        """Apply environmental effects to an agent."""
        effects = {
            'emotional_changes': {},
            'action_modifiers': {},
            'health_effects': 0.0,
            'visibility': self.environment.get_visibility()
        }

        # Apply emotional modifiers
        for emotion, value in self.environment.get_emotional_modifiers().items():
            if hasattr(agent, 'emotional_state'):
                effects['emotional_changes'][emotion] = value

        # Check for hazard exposure
        if hasattr(agent, 'location'):
            location = agent.location
            threats = self.environment.get_active_threats(location)

            for hazard in threats:
                effects['health_effects'] -= hazard.health_damage
                for emotion, value in hazard.emotional_impact.items():
                    effects['emotional_changes'][emotion] = \
                        effects['emotional_changes'].get(emotion, 0.0) + value

        # Apply movement penalty
        effects['action_modifiers']['movement_speed'] = \
            1.0 - self.environment.weather.get_movement_penalty()

        return effects

    def apply_to_team(self, team) -> dict[str, Any]:
        """Apply environmental effects to a team."""
        effects = {
            'coordination_penalty': self.environment.weather.get_coordination_penalty(),
            'communication_penalty': 0.0,
            'morale_modifier': 0.0
        }

        # Weather affects coordination
        if self.environment.weather.weather_type in [WeatherType.STORM, WeatherType.BLIZZARD]:
            effects['communication_penalty'] = 0.3 * self.environment.weather.intensity

        # Time of day effects
        if self.environment.get_time_of_day() == TimeOfDay.NIGHT:
            effects['coordination_penalty'] += 0.1

        # Calculate team morale modifier from environment
        emotional_mods = self.environment.get_emotional_modifiers()
        effects['morale_modifier'] = (
            emotional_mods.get('joy', 0.0) -
            emotional_mods.get('sadness', 0.0) -
            emotional_mods.get('fear', 0.0) * 0.5
        )

        return effects

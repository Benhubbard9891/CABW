"""
CABW Enterprise Enhanced Demo

Demonstrates all advanced features:
- Integrated agents with behavior trees
- Dynamic environment (weather, hazards, events)
- Teamwork and shared goals
- Security governance
- Emotional contagion and group dynamics
"""

import asyncio
import random
from datetime import datetime

from src.cabw.simulation.engine import EnhancedSimulation, SimulationConfig
from src.cabw.core.integrated_agent import IntegratedAgent
from src.cabw.core.world_features import WeatherType, HazardType
from src.cabw.core.teamwork import TeamRole, TeamMember
from src.cabw.core.emotions import EmotionType


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    """Print section header."""
    print(f"\n--- {text} ---")


def print_agent_state(agent, detailed: bool = False):
    """Print agent state in readable format."""
    state = agent.get_state_summary()
    print(f"  {state['name']} ({state['agent_id'][:8]}...)")
    print(f"    Location: {state['location']}")
    print(f"    Health: {state['health']:.1f} | Energy: {state['energy']:.1f}")
    print(f"    Emotion: {state['emotional_state']['dominant']} "
          f"(V:{state['emotional_state']['valence']:.2f}, "
          f"A:{state['emotional_state']['arousal']:.2f})")
    print(f"    Priority Need: {state['needs']['priority']} "
          f"(urgency: {state['needs']['urgency']:.2f})")
    print(f"    Current Action: {state['current_action'] or 'None'}")
    if state['team']:
        print(f"    Team: {state['team'][:8]}... (Role: {state['team_role']})")
    
    if detailed:
        print(f"    OCEAN: O={agent.ocean_traits['openness']:.2f}, "
              f"C={agent.ocean_traits['conscientiousness']:.2f}, "
              f"E={agent.ocean_traits['extraversion']:.2f}, "
              f"A={agent.ocean_traits['agreeableness']:.2f}, "
              f"N={agent.ocean_traits['neuroticism']:.2f}")


async def demo_basic_simulation():
    """Demo 1: Basic simulation with integrated agents."""
    print_header("DEMO 1: Basic Simulation with Integrated Agents")
    
    config = SimulationConfig(
        world_size=(15, 15),
        num_agents=5,
        tick_rate=2.0,
        max_ticks=50,
        security_level='standard',
        teamwork_enabled=True,
        weather_enabled=True,
        hazards_enabled=True
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Initial Agent States")
    for agent in sim.agents.values():
        print_agent_state(agent, detailed=True)
    
    print_section("Running Simulation (20 ticks)")
    for i in range(20):
        await sim.tick()
        
        if i % 5 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            env = sim.environment.get_environmental_summary()
            print(f"    Weather: {env['weather']['type']} "
                  f"(Temp: {env['weather']['temperature']:.1f}°C)")
            print(f"    Time: {env['time_of_day']}")
            print(f"    Active Hazards: {env['active_hazards']}")
    
    print_section("Final Agent States")
    for agent in sim.agents.values():
        print_agent_state(agent)
    
    print(f"\n  Statistics:")
    for key, value in sim.statistics.items():
        print(f"    {key}: {value}")
    
    return sim


async def demo_behavior_trees():
    """Demo 2: Behavior tree-driven agents."""
    print_header("DEMO 2: Behavior Tree-Driven Agents")
    
    config = SimulationConfig(
        world_size=(10, 10),
        num_agents=3,
        tick_rate=1.0,
        max_ticks=30
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Agent Behavior Trees")
    for agent in sim.agents.values():
        print(f"  {agent.name}: {agent.behavior_tree.root.__class__.__name__ if agent.behavior_tree else 'None'}")
    
    print_section("Running with Behavior Trees")
    for i in range(15):
        await sim.tick()
        
        if i % 3 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            for agent in sim.agents.values():
                bt_status = sim.agents[agent.agent_id].blackboard.get('current_action')
                print(f"    {agent.name}: Action={bt_status or 'None'}, "
                      f"Energy={agent.stats.energy:.1f}")


async def demo_emotional_contagion():
    """Demo 3: Emotional contagion between agents."""
    print_header("DEMO 3: Emotional Contagion")
    
    config = SimulationConfig(
        world_size=(5, 5),
        num_agents=4,
        tick_rate=1.0,
        max_ticks=20
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    # Place all agents close together
    positions = [(2, 2), (2, 3), (3, 2), (3, 3)]
    for i, (agent_id, agent) in enumerate(sim.agents.items()):
        agent.location = positions[i]
    
    print_section("Initial Emotional States")
    for agent in sim.agents.values():
        print(f"  {agent.name}: {agent.emotional_state.get_dominant_emotion()}")
    
    # Trigger fear in one agent
    first_agent = list(sim.agents.values())[0]
    print_section(f"Triggering Fear in {first_agent.name}")
    first_agent.emotional_state.apply_stimulus(EmotionType.FEAR, 0.8)
    print(f"  {first_agent.name} emotion: {first_agent.emotional_state.get_dominant_emotion()}")
    
    print_section("Observing Contagion (10 ticks)")
    for i in range(10):
        await sim.tick()
        
        if i % 2 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            for agent in sim.agents.values():
                dom_emotion = agent.emotional_state.get_dominant_emotion()
                fear_level = agent.emotional_state.fear
                print(f"    {agent.name}: {dom_emotion} (fear: {fear_level:.2f})")
    
    print(f"\n  Total contagion events: {sim.statistics['emotional_contagion_events']}")


async def demo_teamwork():
    """Demo 4: Team formation and coordination."""
    print_header("DEMO 4: Team Formation and Coordination")
    
    config = SimulationConfig(
        world_size=(20, 20),
        num_agents=8,
        tick_rate=1.0,
        max_ticks=50,
        teamwork_enabled=True,
        auto_form_teams=True,
        min_team_size=2,
        max_team_size=4
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Initial State (No Teams)")
    print(f"  Teams: {len(sim.team_manager.teams)}")
    print(f"  Agents: {len(sim.agents)}")
    
    # Spawn a hazard to trigger team formation
    print_section("Spawning Hazard to Trigger Team Formation")
    hazard = sim.environment._spawn_hazard()
    hazard.severity = hazard.severity.__class__(3)  # MAJOR severity
    print(f"  Hazard spawned: {hazard.hazard_type.name} at {hazard.location}")
    print(f"  Severity: {hazard.severity.name}")
    print(f"  Requires teamwork: {hazard.get_requires_teamwork()}")
    
    # Move agents near hazard
    for agent in sim.agents.values():
        # Random position near hazard
        agent.location = (
            hazard.location[0] + random.randint(-3, 3),
            hazard.location[1] + random.randint(-3, 3)
        )
    
    print_section("Running Simulation (20 ticks)")
    for i in range(20):
        await sim.tick()
        
        if i % 5 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            print(f"    Teams formed: {len(sim.team_manager.teams)}")
            for team_id, team in sim.team_manager.teams.items():
                print(f"      {team.name}: {len(team.members)} members, "
                      f"cohesion: {team.get_team_cohesion():.2f}")
    
    print_section("Final Team States")
    for team_id, team in sim.team_manager.teams.items():
        print(f"  {team.name}")
        print(f"    Members: {list(team.members.keys())}")
        print(f"    Cohesion: {team.get_team_cohesion():.2f}")
        print(f"    Active Goals: {len(team.active_goals)}")


async def demo_environmental_effects():
    """Demo 5: Weather and environmental effects."""
    print_header("DEMO 5: Weather and Environmental Effects")
    
    config = SimulationConfig(
        world_size=(10, 10),
        num_agents=4,
        tick_rate=1.0,
        max_ticks=30,
        weather_enabled=True,
        hazards_enabled=True
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Initial Weather")
    env = sim.environment.get_environmental_summary()
    print(f"  Weather: {env['weather']['type']}")
    print(f"  Temperature: {env['weather']['temperature']:.1f}°C")
    print(f"  Visibility: {env['weather']['visibility']:.2f}")
    
    print_section("Agent Emotional Modifiers")
    modifiers = sim.environment.get_emotional_modifiers()
    for emotion, value in modifiers.items():
        if value != 0:
            print(f"  {emotion}: {value:+.2f}")
    
    print_section("Changing Weather to Storm")
    sim.environment.weather.weather_type = WeatherType.STORM
    sim.environment.weather.intensity = 0.8
    sim.environment.weather._calculate_emotional_modifiers()
    
    print("\n  New Emotional Modifiers:")
    modifiers = sim.environment.get_emotional_modifiers()
    for emotion, value in modifiers.items():
        if value != 0:
            print(f"  {emotion}: {value:+.2f}")
    
    print(f"\n  Movement Penalty: {sim.environment.weather.get_movement_penalty():.2f}")
    print(f"  Coordination Penalty: {sim.environment.weather.get_coordination_penalty():.2f}")
    
    print_section("Running with Storm (10 ticks)")
    for i in range(10):
        await sim.tick()
        
        if i % 3 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            for agent in sim.agents.values():
                dom = agent.emotional_state.get_dominant_emotion()
                print(f"    {agent.name}: {dom}")


async def demo_security_governance():
    """Demo 6: Security governance and access control."""
    print_header("DEMO 6: Security Governance")
    
    config = SimulationConfig(
        world_size=(10, 10),
        num_agents=3,
        security_level='high',
        tick_rate=1.0,
        max_ticks=20
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Security Configuration")
    print(f"  Security Level: {config.security_level}")
    print(f"  Audit All Actions: {config.audit_all_actions}")
    
    print_section("Agent Security Clearances")
    for agent in sim.agents.values():
        print(f"  {agent.name}: Clearance Level {agent.security_clearance}")
    
    print_section("Security Policies")
    for policy_id, policy in sim.security_governor.policies.items():
        print(f"  {policy_id}: {policy.name}")
        print(f"    Rate Limit: {policy.rate_limit}")
        print(f"    Required Capabilities: {[c.name for c in policy.required_capabilities]}")


async def demo_full_simulation():
    """Demo 7: Full simulation with all features."""
    print_header("DEMO 7: Full Simulation (All Features)")
    
    config = SimulationConfig(
        world_size=(25, 25),
        num_agents=12,
        tick_rate=2.0,
        max_ticks=100,
        security_level='standard',
        teamwork_enabled=True,
        auto_form_teams=True,
        weather_enabled=True,
        hazards_enabled=True,
        events_enabled=True
    )
    
    sim = EnhancedSimulation(config)
    sim.initialize()
    
    print_section("Simulation Configuration")
    print(f"  World Size: {config.world_size}")
    print(f"  Agents: {config.num_agents}")
    print(f"  Tick Rate: {config.tick_rate}/s")
    print(f"  Max Ticks: {config.max_ticks}")
    print(f"  Security Level: {config.security_level}")
    print(f"  Teamwork: {config.teamwork_enabled}")
    print(f"  Weather: {config.weather_enabled}")
    print(f"  Hazards: {config.hazards_enabled}")
    
    print_section("Initial State")
    state = sim.get_state()
    print(f"  Tick: {state['tick']}")
    print(f"  Agents: {len(state['agents'])}")
    print(f"  Weather: {state['environment']['weather']['type']}")
    print(f"  Emotional Climate: {state['emotional_climate']['dominant']}")
    
    print_section("Running Full Simulation (30 ticks)")
    
    # Track interesting events
    events_of_interest = []
    
    for i in range(30):
        tick_results = await sim.tick()
        
        # Check for interesting events
        if tick_results['environment_results'].get('new_hazards'):
            events_of_interest.append((i, "New hazard spawned"))
        
        if tick_results['environment_results'].get('weather_changed'):
            events_of_interest.append((i, "Weather changed"))
        
        if tick_results['team_results']:
            events_of_interest.append((i, "Team activity"))
        
        if i % 10 == 0:
            print(f"\n  Tick {sim.tick_count}:")
            state = sim.get_state()
            print(f"    Weather: {state['environment']['weather']['type']}")
            print(f"    Hazards: {state['environment']['active_hazards']}")
            print(f"    Teams: {len(state['teams'])}")
            print(f"    Emotional Climate: {state['emotional_climate']['dominant']}")
            
            # Sample agent states
            alive_agents = [a for a in sim.agents.values() if a.stats.is_alive()]
            print(f"    Alive Agents: {len(alive_agents)}/{len(sim.agents)}")
    
    print_section("Interesting Events")
    for tick, event in events_of_interest:
        print(f"  Tick {tick}: {event}")
    
    print_section("Final Statistics")
    for key, value in sim.statistics.items():
        print(f"  {key}: {value}")
    
    print_section("Final Agent States (Sample)")
    for agent in list(sim.agents.values())[:3]:
        print_agent_state(agent, detailed=True)
    
    print_section("Final Team States")
    for team_id, team in sim.team_manager.teams.items():
        print(f"  {team.name}")
        print(f"    Members: {len(team.members)}")
        print(f"    Cohesion: {team.get_team_cohesion():.2f}")
        print(f"    Goals Completed: {len([g for g in team.completed_goals])}")
    
    # Export results
    print_section("Exporting Results")
    filepath = sim.export_results(f"/tmp/cabw_demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    print(f"  Results exported to: {filepath}")
    
    return sim


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  CABW ENTERPRISE - ENHANCED FEATURES DEMO")
    print("=" * 60)
    print("\nThis demo showcases all advanced features:")
    print("  - Integrated agents with behavior trees")
    print("  - Advanced emotional system with contagion")
    print("  - Dynamic environment (weather, hazards)")
    print("  - Teamwork and shared goals")
    print("  - Security governance")
    print("  - Real-time statistics and logging")
    
    demos = [
        ("Basic Simulation", demo_basic_simulation),
        ("Behavior Trees", demo_behavior_trees),
        ("Emotional Contagion", demo_emotional_contagion),
        ("Teamwork", demo_teamwork),
        ("Environmental Effects", demo_environmental_effects),
        ("Security Governance", demo_security_governance),
        ("Full Simulation", demo_full_simulation),
    ]
    
    print("\n" + "-" * 60)
    print("Available Demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  8. Run All Demos")
    print("  0. Exit")
    print("-" * 60)
    
    # Auto-run all demos for demonstration
    print("\nAuto-running all demos...\n")
    
    for name, demo_func in demos:
        try:
            await demo_func()
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error in {name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("  ALL DEMOS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

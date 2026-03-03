"""
Natural Language Interface for CABW

Enables natural language interaction with agents and the simulation.
Includes agent dialogue and command processing.
"""

import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DialogueTurn:
    """Single turn in agent dialogue."""
    speaker_id: str
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    emotional_state: dict[str, float] | None = None
    intent: str | None = None


@dataclass
class ParsedCommand:
    """Parsed natural language command."""
    raw_text: str
    action: str
    target: str | None
    parameters: dict[str, Any]
    confidence: float
    alternative_interpretations: list[dict[str, Any]] = field(default_factory=list)


class CommandProcessor:
    """
    Process natural language commands for simulation control.
    """

    # Command patterns
    PATTERNS = {
        'create_simulation': [
            r'create (?:a |new )?simulation',
            r'start (?:a |new )?simulation',
            r'initialize simulation'
        ],
        'add_agent': [
            r'add (?:an )?agent(?: named)? (?P<name>\w+)',
            r'create (?:an )?agent(?: named)? (?P<name>\w+)',
            r'spawn agent (?P<name>\w+)'
        ],
        'start_simulation': [
            r'start (?:the )?simulation',
            r'run (?:the )?simulation',
            r'begin simulation'
        ],
        'pause_simulation': [
            r'pause (?:the )?simulation',
            r'stop (?:the )?simulation',
            r'hold simulation'
        ],
        'set_weather': [
            r'set weather to (?P<weather>\w+)',
            r'change weather to (?P<weather>\w+)',
            r'make it (?P<weather>\w+)'
        ],
        'trigger_event': [
            r'trigger (?P<event>\w+) event',
            r'create (?P<event>\w+) event',
            r'start (?P<event>\w+)'
        ],
        'get_status': [
            r'what is (?:the )?status',
            r'show status',
            r'get simulation state'
        ],
        'export_results': [
            r'export results',
            r'save simulation',
            r'download data'
        ]
    }

    def __init__(self):
        self.command_history: list[ParsedCommand] = []
        self.custom_patterns: dict[str, list[str]] = {}

    def add_custom_pattern(self, command_type: str, patterns: list[str]):
        """Add custom command patterns."""
        self.custom_patterns[command_type] = patterns

    def parse(self, text: str) -> ParsedCommand | None:
        """
        Parse natural language command.
        Returns ParsedCommand or None if no match.
        """
        text_lower = text.lower().strip()

        best_match = None
        best_confidence = 0.0

        # Check built-in patterns
        for command_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    confidence = len(match.group(0)) / len(text_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (command_type, match)

        # Check custom patterns
        for command_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    confidence = len(match.group(0)) / len(text_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (command_type, match)

        if best_match:
            command_type, match = best_match
            params = match.groupdict() if match.groups() else {}

            return ParsedCommand(
                raw_text=text,
                action=command_type,
                target=params.get('name') or params.get('target'),
                parameters=params,
                confidence=best_confidence
            )

        return None

    def execute_command(
        self,
        command: ParsedCommand,
        simulation: Any
    ) -> dict[str, Any]:
        """
        Execute parsed command on simulation.
        """
        result = {
            'success': False,
            'action': command.action,
            'message': ''
        }

        try:
            if command.action == 'create_simulation':
                # This would create a new simulation
                result['success'] = True
                result['message'] = 'Simulation created'

            elif command.action == 'add_agent':
                name = command.parameters.get('name', 'Agent')
                # Add agent to simulation
                result['success'] = True
                result['message'] = f'Agent {name} added'

            elif command.action == 'start_simulation':
                if hasattr(simulation, 'running'):
                    simulation.running = True
                result['success'] = True
                result['message'] = 'Simulation started'

            elif command.action == 'pause_simulation':
                if hasattr(simulation, 'paused'):
                    simulation.paused = True
                result['success'] = True
                result['message'] = 'Simulation paused'

            elif command.action == 'set_weather':
                weather = command.parameters.get('weather', 'clear')
                if hasattr(simulation, 'environment'):
                    # Set weather
                    pass
                result['success'] = True
                result['message'] = f'Weather set to {weather}'

            elif command.action == 'trigger_event':
                event = command.parameters.get('event', 'generic')
                if hasattr(simulation, 'trigger_event'):
                    simulation.trigger_event(event)
                result['success'] = True
                result['message'] = f'Event {event} triggered'

            elif command.action == 'get_status':
                if hasattr(simulation, 'get_state'):
                    state = simulation.get_state()
                    result['success'] = True
                    result['message'] = 'Status retrieved'
                    result['data'] = state

            elif command.action == 'export_results':
                if hasattr(simulation, 'export_results'):
                    filepath = simulation.export_results()
                    result['success'] = True
                    result['message'] = f'Results exported to {filepath}'

            else:
                result['message'] = f'Unknown command: {command.action}'

        except Exception as e:
            result['message'] = f'Error: {str(e)}'

        self.command_history.append(command)
        return result


class AgentDialogue:
    """
    Natural language dialogue between agents and with users.
    """

    # Dialogue templates based on emotional state
    TEMPLATES = {
        'greeting': {
            'joy': ["Hello! Great to see you!", "Hi there! Wonderful day!"],
            'neutral': ["Hello.", "Hi there."],
            'sadness': ["Oh... hello.", "Hi... I guess."],
            'anger': ["What do you want?", "Make it quick."],
            'fear': ["H-hello?", "Who's there?"]
        },
        'help_offer': {
            'joy': ["I'd love to help!", "Sure thing! What do you need?"],
            'neutral': ["I can help.", "What do you need?"],
            'sadness': ["I suppose I could help...", "If you really need me..."],
            'anger': ["Why should I help you?", "Do it yourself."],
            'fear': ["I-I'll try to help...", "If it's safe..."]
        },
        'request_help': {
            'joy': ["Could you help me? It'd be fun!", "Hey, want to work together?"],
            'neutral': ["I need some assistance.", "Can you help me?"],
            'sadness': ["I could really use some help...", "Please, I need help..."],
            'anger': ["You need to help me!", "Do this for me!"],
            'fear': ["Please help me! I'm scared!", "I need help, quickly!"]
        },
        'goodbye': {
            'joy': ["See you later! Have a great day!", "Bye! Take care!"],
            'neutral': ["Goodbye.", "See you."],
            'sadness': ["Goodbye... I'll miss you...", "Bye..."],
            'anger': ["Finally.", "Leave me alone."],
            'fear': ["G-goodbye...", "Stay safe..."]
        }
    }

    def __init__(self, agent):
        self.agent = agent
        self.dialogue_history: list[DialogueTurn] = []
        self.relationship_memory: dict[str, list[str]] = {}

    def generate_utterance(
        self,
        dialogue_type: str,
        target_agent: Any | None = None
    ) -> str:
        """
        Generate natural language utterance based on agent's emotional state.
        """
        # Get dominant emotion
        if hasattr(self.agent, 'emotional_state'):
            emotion = self.agent.emotional_state.get_dominant_emotion()
        else:
            emotion = 'neutral'

        # Get templates for dialogue type and emotion
        templates = self.TEMPLATES.get(dialogue_type, {}).get(emotion, ["..."])

        # Select template
        utterance = random.choice(templates)

        # Personalize based on relationship
        if target_agent and hasattr(target_agent, 'agent_id'):
            target_id = target_agent.agent_id
            memories = self.relationship_memory.get(target_id, [])

            if memories and dialogue_type == 'greeting':
                # Reference past interaction
                last_topic = memories[-1]
                utterance += f" How is the {last_topic} going?"

        # Record dialogue
        turn = DialogueTurn(
            speaker_id=self.agent.agent_id if hasattr(self.agent, 'agent_id') else 'unknown',
            text=utterance,
            emotional_state=self._get_emotional_snapshot()
        )
        self.dialogue_history.append(turn)

        return utterance

    def respond_to(
        self,
        message: str,
        sender: Any,
        context: dict | None = None
    ) -> str:
        """
        Generate response to received message.
        """
        context = context or {}

        # Simple intent detection
        message_lower = message.lower()

        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return self.generate_utterance('greeting', sender)

        elif any(word in message_lower for word in ['help', 'assist', 'aid']):
            if 'can you' in message_lower or 'could you' in message_lower:
                return self.generate_utterance('help_offer', sender)
            else:
                return self.generate_utterance('request_help', sender)

        elif any(word in message_lower for word in ['bye', 'goodbye', 'see you']):
            return self.generate_utterance('goodbye', sender)

        elif '?' in message:
            # Question - respond based on knowledge
            return self._answer_question(message, context)

        else:
            # Generic response
            return self._generate_generic_response(message, sender)

    def _answer_question(self, question: str, context: dict) -> str:
        """Answer a question based on agent's knowledge."""
        question_lower = question.lower()

        if 'weather' in question_lower:
            if hasattr(self.agent, 'environment'):
                weather = self.agent.environment.weather
                return f"It's {weather.weather_type.name.lower()} right now."
            return "I'm not sure about the weather."

        elif 'location' in question_lower or 'where' in question_lower:
            if hasattr(self.agent, 'location'):
                return f"I'm at {self.agent.location}."
            return "I'm not sure where I am."

        elif 'team' in question_lower:
            if hasattr(self.agent, 'current_team') and self.agent.current_team:
                team = self.agent.current_team
                return f"I'm part of {team.name} with {len(team.members)} members."
            return "I'm not in a team right now."

        elif 'feel' in question_lower or 'feeling' in question_lower:
            if hasattr(self.agent, 'emotional_state'):
                emotion = self.agent.emotional_state.get_dominant_emotion()
                return f"I'm feeling {emotion.lower()} right now."
            return "I'm not sure how I feel."

        else:
            return "I'm not sure I understand. Can you rephrase that?"

    def _generate_generic_response(self, message: str, sender: Any) -> str:
        """Generate generic response."""
        # Check emotional state
        if hasattr(self.agent, 'emotional_state'):
            valence = self.agent.emotional_state.get_valence()

            if valence > 0.3:
                return "That's interesting! Tell me more."
            elif valence < -0.3:
                return "I see."

        return "Okay."

    def _get_emotional_snapshot(self) -> dict[str, float]:
        """Get snapshot of emotional state."""
        if hasattr(self.agent, 'emotional_state'):
            return {
                'valence': self.agent.emotional_state.get_valence(),
                'arousal': self.agent.emotional_state.get_arousal(),
                'dominant': self.agent.emotional_state.get_dominant_emotion()
            }
        return {}

    def remember_topic(self, target_id: str, topic: str):
        """Remember topic of conversation with agent."""
        if target_id not in self.relationship_memory:
            self.relationship_memory[target_id] = []
        self.relationship_memory[target_id].append(topic)
        # Keep only last 5 topics
        self.relationship_memory[target_id] = self.relationship_memory[target_id][-5:]


class NLPInterface:
    """
    Main NLP interface coordinating command processing and agent dialogue.
    """

    def __init__(self, simulation: Any = None):
        self.simulation = simulation
        self.command_processor = CommandProcessor()
        self.agent_dialogues: dict[str, AgentDialogue] = {}
        self.conversation_history: list[dict] = []

    def register_agent(self, agent):
        """Register an agent for dialogue."""
        agent_id = agent.agent_id if hasattr(agent, 'agent_id') else str(id(agent))
        self.agent_dialogues[agent_id] = AgentDialogue(agent)

    def process_user_input(
        self,
        text: str,
        user_id: str = 'user'
    ) -> dict[str, Any]:
        """
        Process user input (command or dialogue).
        """
        # Try to parse as command
        command = self.command_processor.parse(text)

        if command and command.confidence > 0.5:
            # Execute command
            result = self.command_processor.execute_command(
                command,
                self.simulation
            )

            self.conversation_history.append({
                'speaker': user_id,
                'text': text,
                'type': 'command',
                'result': result
            })

            return {
                'type': 'command_result',
                'command': command.action,
                'result': result
            }

        else:
            # Treat as dialogue
            response = self._generate_system_response(text)

            self.conversation_history.append({
                'speaker': user_id,
                'text': text,
                'type': 'dialogue'
            })

            return {
                'type': 'dialogue',
                'response': response
            }

    def agent_speak(
        self,
        agent_id: str,
        dialogue_type: str,
        target_agent_id: str | None = None
    ) -> str:
        """
        Have an agent generate dialogue.
        """
        dialogue = self.agent_dialogues.get(agent_id)
        if not dialogue:
            return "..."

        target = self.agent_dialogues.get(target_agent_id)

        utterance = dialogue.generate_utterance(
            dialogue_type,
            target.agent if target else None
        )

        self.conversation_history.append({
            'speaker': agent_id,
            'text': utterance,
            'type': 'agent_dialogue',
            'target': target_agent_id
        })

        return utterance

    def agent_respond(
        self,
        agent_id: str,
        message: str,
        sender_id: str
    ) -> str:
        """
        Have an agent respond to a message.
        """
        dialogue = self.agent_dialogues.get(agent_id)
        if not dialogue:
            return "..."

        sender = self.agent_dialogues.get(sender_id)

        response = dialogue.respond_to(
            message,
            sender.agent if sender else None
        )

        self.conversation_history.append({
            'speaker': agent_id,
            'text': response,
            'type': 'agent_response',
            'target': sender_id
        })

        return response

    def _generate_system_response(self, user_message: str) -> str:
        """Generate system response to user dialogue."""
        message_lower = user_message.lower()

        if 'help' in message_lower:
            return "I can help you control the simulation. Try commands like 'create simulation', 'add agent', or 'start simulation'."

        elif 'hello' in message_lower or 'hi' in message_lower:
            return "Hello! I'm the CABW simulation interface. How can I help you today?"

        elif 'status' in message_lower:
            if self.simulation and hasattr(self.simulation, 'get_state'):
                state = self.simulation.get_state()
                return f"Simulation is at tick {state.get('tick', 0)} with {len(state.get('agents', {}))} agents."
            return "No simulation is currently running."

        else:
            return "I'm not sure I understand. You can ask for 'help' to see available commands."

    def get_conversation_log(self) -> list[dict]:
        """Get full conversation history."""
        return self.conversation_history

    def export_dialogue(self, agent_id: str, filepath: str):
        """Export agent's dialogue history."""
        dialogue = self.agent_dialogues.get(agent_id)
        if not dialogue:
            return

        data = {
            'agent_id': agent_id,
            'dialogue_count': len(dialogue.dialogue_history),
            'dialogues': [
                {
                    'speaker': turn.speaker_id,
                    'text': turn.text,
                    'timestamp': turn.timestamp,
                    'emotion': turn.emotional_state
                }
                for turn in dialogue.dialogue_history
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

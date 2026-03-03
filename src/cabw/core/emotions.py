"""
Advanced Emotion System for CABW Enterprise.

Implements:
- Complex emotional states beyond PAD
- Emotional contagion (spread between agents)
- Mood persistence and personality influence
- Emotional regulation and suppression
- Trauma and PTSD mechanics
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from cabw.config import settings
from cabw.utils.logging import get_logger

logger = get_logger(__name__)


class EmotionType(Enum):
    """Primary emotion types with biological basis."""
    JOY = auto()
    SADNESS = auto()
    ANGER = auto()
    FEAR = auto()
    DISGUST = auto()
    SURPRISE = auto()
    TRUST = auto()
    ANTICIPATION = auto()
    
    # Complex emotions (combinations)
    LOVE = auto()           # Joy + Trust
    SUBMISSION = auto()     # Trust + Fear
    AWE = auto()            # Fear + Surprise
    DISAPPROVAL = auto()    # Surprise + Sadness
    REMORSE = auto()        # Sadness + Disgust
    CONTEMPT = auto()       # Disgust + Anger
    AGGRESSION = auto()     # Anger + Anticipation
    OPTIMISM = auto()       # Anticipation + Joy
    
    # Social emotions
    GUILT = auto()
    SHAME = auto()
    PRIDE = auto()
    ENVY = auto()
    JEALOUSY = auto()
    GRATITUDE = auto()
    EMPATHY = auto()
    LONELINESS = auto()


class MoodState(Enum):
    """Long-term mood states that influence emotional baseline."""
    EUPHORIC = "euphoric"       # Extreme positive
    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    UNEASY = "uneasy"
    ANXIOUS = "anxious"
    DEPRESSED = "depressed"
    TRAUMATIZED = "traumatized"  # Extreme negative


@dataclass
class EmotionalState:
    """
    Complete emotional state for an agent.
    
    Combines:
    - Primary emotions (short-term reactions)
    - Mood (long-term baseline)
    - Emotional history (for trauma/regret)
    """
    # Primary emotions (0-1 intensity)
    joy: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    disgust: float = 0.0
    surprise: float = 0.0
    trust: float = 0.5  # Neutral default
    anticipation: float = 0.0
    
    # Complex emotions (derived from primaries)
    love: float = 0.0
    guilt: float = 0.0
    shame: float = 0.0
    pride: float = 0.0
    envy: float = 0.0
    gratitude: float = 0.0
    
    # Mood state
    mood: MoodState = MoodState.NEUTRAL
    mood_stability: float = 0.5  # How resistant to change
    
    # Trauma tracking
    trauma_score: float = 0.0
    trauma_triggers: Set[str] = field(default_factory=set)
    emotional_scars: List[Dict] = field(default_factory=list)
    
    # Regulation
    suppression_level: float = 0.0  # How much emotions are being suppressed
    regulation_capacity: float = 0.5  # Ability to regulate emotions
    
    # Timestamps
    last_update: datetime = field(default_factory=datetime.utcnow)
    mood_since: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Normalize values after initialization."""
        self._normalize()
        self._update_complex_emotions()
    
    def _normalize(self) -> None:
        """Ensure all emotion values are in valid range."""
        for attr in ['joy', 'sadness', 'anger', 'fear', 'disgust', 
                     'surprise', 'trust', 'anticipation', 'love',
                     'guilt', 'shame', 'pride', 'envy', 'gratitude']:
            setattr(self, attr, max(0.0, min(1.0, getattr(self, attr))))
    
    def _update_complex_emotions(self) -> None:
        """Derive complex emotions from primary emotions."""
        # Love = Joy + Trust (weighted)
        self.love = (self.joy * 0.6 + self.trust * 0.4) * min(1.0, self.joy + self.trust)
        
        # Pride = Joy + high dominance (implied)
        self.pride = self.joy * 0.7 if self.joy > 0.5 else 0.0
        
        # Envy = Sadness + Anger (toward others' success)
        self.envy = (self.sadness * 0.5 + self.anger * 0.5) * 0.5
        
        # Gratitude = Joy + Trust (receiving benefit)
        self.gratitude = (self.joy * 0.4 + self.trust * 0.6) * 0.5
    
    def get_dominant_emotion(self) -> Tuple[EmotionType, float]:
        """Get the currently dominant emotion and its intensity."""
        emotions = {
            EmotionType.JOY: self.joy,
            EmotionType.SADNESS: self.sadness,
            EmotionType.ANGER: self.anger,
            EmotionType.FEAR: self.fear,
            EmotionType.DISGUST: self.disgust,
            EmotionType.SURPRISE: self.surprise,
            EmotionType.TRUST: self.trust,
            EmotionType.ANTICIPATION: self.anticipation,
            EmotionType.LOVE: self.love,
            EmotionType.GUILT: self.guilt,
            EmotionType.SHAME: self.shame,
            EmotionType.PRIDE: self.pride,
            EmotionType.ENVY: self.envy,
            EmotionType.GRATITUDE: self.gratitude,
        }
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        return dominant
    
    def get_valence(self) -> float:
        """Get overall emotional valence (-1 to 1, negative to positive)."""
        positive = self.joy + self.trust + self.love + self.pride + self.gratitude
        negative = self.sadness + self.anger + self.fear + self.disgust + self.guilt + self.shame
        return (positive - negative) / 7  # Normalize
    
    def get_arousal(self) -> float:
        """Get emotional arousal level (0 to 1)."""
        # High arousal emotions
        arousal_emotions = [
            self.anger, self.fear, self.joy, self.surprise, self.anticipation
        ]
        return sum(arousal_emotions) / len(arousal_emotions)
    
    def apply_stimulus(
        self,
        emotion: EmotionType,
        intensity: float,
        source: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Apply an emotional stimulus.
        
        Returns dict with emotion changes and any triggered trauma.
        """
        context = context or {}
        changes = {}
        trauma_triggered = False
        
        # Check for trauma triggers
        if source and source in self.trauma_triggers:
            intensity *= (1 + self.trauma_score)  # Amplify
            trauma_triggered = True
            logger.debug(f"Trauma trigger activated: {source}")
        
        # Apply suppression if active
        if self.suppression_level > 0:
            intensity *= (1 - self.suppression_level * 0.5)
        
        # Apply mood influence
        mood_modifiers = {
            MoodState.EUPHORIC: {'joy': 0.3, 'sadness': -0.2},
            MoodState.HAPPY: {'joy': 0.2, 'sadness': -0.1},
            MoodState.CONTENT: {'joy': 0.1, 'anger': -0.1},
            MoodState.NEUTRAL: {},
            MoodState.UNEASY: {'fear': 0.1, 'trust': -0.1},
            MoodState.ANXIOUS: {'fear': 0.2, 'anticipation': 0.2},
            MoodState.DEPRESSED: {'joy': -0.2, 'sadness': 0.2},
            MoodState.TRAUMATIZED: {'fear': 0.3, 'trust': -0.3},
        }
        
        modifiers = mood_modifiers.get(self.mood, {})
        for emotion_attr, modifier in modifiers.items():
            if emotion_attr == emotion.name.lower():
                intensity += modifier
        
        # Apply to appropriate emotion
        emotion_attr = emotion.name.lower()
        if hasattr(self, emotion_attr):
            old_value = getattr(self, emotion_attr)
            new_value = min(1.0, old_value + intensity)
            setattr(self, emotion_attr, new_value)
            changes[emotion_attr] = new_value - old_value
        
        # Update complex emotions
        self._update_complex_emotions()
        
        # Decay opposite emotions
        self._decay_opposites(emotion, intensity)
        
        self.last_update = datetime.utcnow()
        
        return {
            'changes': changes,
            'trauma_triggered': trauma_triggered,
            'new_valence': self.get_valence(),
            'new_arousal': self.get_arousal(),
        }
    
    def _decay_opposites(self, emotion: EmotionType, intensity: float) -> None:
        """Decay emotions opposite to the one being increased."""
        opposites = {
            EmotionType.JOY: [EmotionType.SADNESS, EmotionType.FEAR],
            EmotionType.SADNESS: [EmotionType.JOY, EmotionType.PRIDE],
            EmotionType.ANGER: [EmotionType.TRUST, EmotionType.GRATITUDE],
            EmotionType.FEAR: [EmotionType.JOY, EmotionType.TRUST],
            EmotionType.TRUST: [EmotionType.FEAR, EmotionType.ANGER],
        }
        
        for opp in opposites.get(emotion, []):
            opp_attr = opp.name.lower()
            if hasattr(self, opp_attr):
                current = getattr(self, opp_attr)
                decay = intensity * 0.3  # 30% decay of opposite
                setattr(self, opp_attr, max(0.0, current - decay))
    
    def decay(self, dt: float = 1.0) -> None:
        """Decay emotions over time."""
        decay_rate = 0.05 * dt
        
        # Primary emotions decay
        for attr in ['joy', 'sadness', 'anger', 'fear', 'disgust', 
                     'surprise', 'anticipation']:
            current = getattr(self, attr)
            setattr(self, attr, max(0.0, current - decay_rate))
        
        # Trust decays toward neutral (0.5)
        self.trust = 0.5 + (self.trust - 0.5) * (1 - decay_rate * 0.5)
        
        # Suppression decays
        self.suppression_level = max(0.0, self.suppression_level - decay_rate * 0.5)
        
        self._update_complex_emotions()
    
    def update_mood(self) -> None:
        """Update long-term mood based on recent emotional history."""
        valence = self.get_valence()
        arousal = self.get_arousal()
        
        # Determine new mood
        if self.trauma_score > 0.7:
            new_mood = MoodState.TRAUMATIZED
        elif valence > 0.6 and arousal > 0.5:
            new_mood = MoodState.EUPHORIC
        elif valence > 0.3:
            new_mood = MoodState.HAPPY
        elif valence > 0.1:
            new_mood = MoodState.CONTENT
        elif valence < -0.5:
            new_mood = MoodState.DEPRESSED
        elif valence < -0.2 or self.fear > 0.5:
            new_mood = MoodState.ANXIOUS
        elif valence < 0:
            new_mood = MoodState.UNEASY
        else:
            new_mood = MoodState.NEUTRAL
        
        # Apply mood stability (resistance to change)
        if new_mood != self.mood:
            if self.mood_stability < 0.5 or (datetime.utcnow() - self.mood_since).seconds > 300:
                self.mood = new_mood
                self.mood_since = datetime.utcnow()
                logger.debug(f"Mood changed to: {new_mood.value}")
    
    def add_trauma(self, event: str, severity: float, triggers: List[str]) -> None:
        """Add traumatic event to agent's history."""
        self.trauma_score = min(1.0, self.trauma_score + severity)
        self.trauma_triggers.update(triggers)
        
        self.emotional_scars.append({
            'event': event,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat(),
            'triggers': triggers,
        })
        
        # Trauma affects mood
        if self.trauma_score > 0.5:
            self.mood = MoodState.TRAUMATIZED
        
        logger.info(f"Trauma added: {event} (severity: {severity})")
    
    def regulate(self, target_emotion: EmotionType, target_level: float) -> bool:
        """Attempt to regulate an emotion to target level."""
        if self.regulation_capacity < 0.3:
            return False  # Can't regulate well
        
        emotion_attr = target_emotion.name.lower()
        if not hasattr(self, emotion_attr):
            return False
        
        current = getattr(self, emotion_attr)
        diff = target_level - current
        
        # Regulation effectiveness
        effectiveness = self.regulation_capacity * (1 - self.trauma_score * 0.5)
        change = diff * effectiveness * 0.3
        
        new_value = max(0.0, min(1.0, current + change))
        setattr(self, emotion_attr, new_value)
        
        # Regulation is tiring
        self.regulation_capacity = max(0.1, self.regulation_capacity - 0.05)
        
        return abs(new_value - target_level) < 0.1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'primary': {
                'joy': round(self.joy, 3),
                'sadness': round(self.sadness, 3),
                'anger': round(self.anger, 3),
                'fear': round(self.fear, 3),
                'disgust': round(self.disgust, 3),
                'surprise': round(self.surprise, 3),
                'trust': round(self.trust, 3),
                'anticipation': round(self.anticipation, 3),
            },
            'complex': {
                'love': round(self.love, 3),
                'guilt': round(self.guilt, 3),
                'shame': round(self.shame, 3),
                'pride': round(self.pride, 3),
                'envy': round(self.envy, 3),
                'gratitude': round(self.gratitude, 3),
            },
            'mood': self.mood.value,
            'valence': round(self.get_valence(), 3),
            'arousal': round(self.get_arousal(), 3),
            'trauma_score': round(self.trauma_score, 3),
            'dominant_emotion': self.get_dominant_emotion()[0].name,
        }


class EmotionalContagion:
    """
    System for emotional contagion between agents.
    
    Emotions spread through social networks based on:
    - Relationship strength
    - Empathy levels
    - Physical proximity
    - Emotional expressiveness
    """
    
    @staticmethod
    def calculate_contagion_strength(
        source_emotion: float,
        relationship_trust: float,
        relationship_affection: float,
        target_empathy: float,
        distance: float,
        source_expressiveness: float = 0.5
    ) -> float:
        """
        Calculate how much emotion transfers from source to target.
        
        Args:
            source_emotion: Intensity of emotion in source (0-1)
            relationship_trust: Trust level between agents (0-1)
            relationship_affection: Affection level (-1 to 1)
            target_empathy: Target's empathy capability (0-1)
            distance: Physical/social distance (0-1, higher = farther)
            source_expressiveness: How much source shows emotions
        """
        # Base contagion from relationship
        relationship_factor = (relationship_trust + max(0, relationship_affection)) / 2
        
        # Empathy amplifies reception
        empathy_factor = target_empathy
        
        # Distance reduces contagion
        distance_factor = max(0, 1 - distance)
        
        # Expressiveness affects transmission
        expression_factor = source_expressiveness
        
        # Combined formula
        contagion = (
            source_emotion * 
            relationship_factor * 
            empathy_factor * 
            distance_factor * 
            expression_factor
        )
        
        return min(1.0, contagion)
    
    @staticmethod
    def apply_contagion(
        source_state: EmotionalState,
        target_state: EmotionalState,
        emotion: EmotionType,
        strength: float
    ) -> Dict:
        """Apply emotional contagion from source to target."""
        emotion_attr = emotion.name.lower()
        
        if not hasattr(source_state, emotion_attr):
            return {'transferred': 0.0}
        
        source_intensity = getattr(source_state, emotion_attr)
        
        # Contagion is partial
        transferred = source_intensity * strength * 0.5
        
        # Apply to target
        if hasattr(target_state, emotion_attr):
            current = getattr(target_state, emotion_attr)
            new_value = min(1.0, current + transferred)
            setattr(target_state, emotion_attr, new_value)
        
        return {
            'emotion': emotion.name,
            'transferred': round(transferred, 3),
            'new_intensity': round(getattr(target_state, emotion_attr, 0), 3),
        }


class GroupEmotionalClimate:
    """
    Tracks and manages the emotional climate of a group.
    
    Groups develop collective emotional states that influence
    individual members and emerge from their interactions.
    """
    
    def __init__(self, group_id: str):
        """Initialize group emotional climate."""
        self.group_id = group_id
        self.member_emotions: Dict[str, EmotionalState] = {}
        self.climate_history: List[Dict] = []
        
        # Collective metrics
        self.collective_valence: float = 0.0
        self.collective_arousal: float = 0.0
        self.emotional_diversity: float = 0.0
        
        # Emergent properties
        self.morale: float = 0.5
        group_cohesion: float = 0.5
        self.tension: float = 0.0
    
    def add_member(self, agent_id: str, state: EmotionalState) -> None:
        """Add member to group climate tracking."""
        self.member_emotions[agent_id] = state
        self._update_climate()
    
    def remove_member(self, agent_id: str) -> None:
        """Remove member from group climate."""
        self.member_emotions.pop(agent_id, None)
        self._update_climate()
    
    def _update_climate(self) -> None:
        """Recalculate collective emotional climate."""
        if not self.member_emotions:
            return
        
        # Calculate averages
        valences = [s.get_valence() for s in self.member_emotions.values()]
        arousals = [s.get_arousal() for s in self.member_emotions.values()]
        fears = [s.fear for s in self.member_emotions.values()]
        joys = [s.joy for s in self.member_emotions.values()]
        
        self.collective_valence = sum(valences) / len(valences)
        self.collective_arousal = sum(arousals) / len(arousals)
        
        # Emotional diversity (standard deviation of valences)
        if len(valences) > 1:
            mean_val = self.collective_valence
            variance = sum((v - mean_val) ** 2 for v in valences) / len(valences)
            self.emotional_diversity = math.sqrt(variance)
        
        # Morale based on collective joy and lack of fear
        avg_fear = sum(fears) / len(fears)
        avg_joy = sum(joys) / len(joys)
        self.morale = (avg_joy + (1 - avg_fear)) / 2
        
        # Tension from high arousal and diversity
        self.tension = (self.collective_arousal + self.emotional_diversity) / 2
        
        # Record history
        self.climate_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'valence': round(self.collective_valence, 3),
            'arousal': round(self.collective_arousal, 3),
            'morale': round(self.morale, 3),
            'tension': round(self.tension, 3),
            'member_count': len(self.member_emotions),
        })
    
    def get_climate_description(self) -> str:
        """Get human-readable description of group climate."""
        if self.morale > 0.7 and self.tension < 0.3:
            return "high_morale"
        elif self.morale < 0.3 and self.tension > 0.6:
            return "crisis"
        elif self.tension > 0.6:
            return "tense"
        elif self.collective_valence < -0.3:
            return "negative"
        elif self.emotional_diversity > 0.5:
            return "divided"
        else:
            return "stable"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'group_id': self.group_id,
            'member_count': len(self.member_emotions),
            'collective_valence': round(self.collective_valence, 3),
            'collective_arousal': round(self.collective_arousal, 3),
            'emotional_diversity': round(self.emotional_diversity, 3),
            'morale': round(self.morale, 3),
            'tension': round(self.tension, 3),
            'climate': self.get_climate_description(),
        }


__all__ = [
    'EmotionType',
    'MoodState',
    'EmotionalState',
    'EmotionalContagion',
    'GroupEmotionalClimate',
]

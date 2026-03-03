"""
Redis-based Message Passing for Distributed Simulation
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class MessageType(Enum):
    """Types of distributed messages."""
    AGENT_MIGRATE = auto()      # Agent moving between partitions
    AGENT_UPDATE = auto()       # Agent state update
    WORLD_UPDATE = auto()       # World state update
    SYNC_REQUEST = auto()       # Request synchronization
    SYNC_RESPONSE = auto()      # Synchronization response
    HAZARD_ALERT = auto()       # Hazard notification
    TEAM_FORMATION = auto()     # Team formation request
    HEARTBEAT = auto()          # Node heartbeat
    SHUTDOWN = auto()           # Shutdown notification


@dataclass
class Message:
    """Message for distributed communication."""
    msg_id: str
    msg_type: MessageType
    source_node: str
    target_node: str | None  # None = broadcast
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 0  # Higher = more urgent

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'msg_id': self.msg_id,
            'msg_type': self.msg_type.name,
            'source_node': self.source_node,
            'target_node': self.target_node,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'priority': self.priority
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls(
            msg_id=data['msg_id'],
            msg_type=MessageType[data['msg_type']],
            source_node=data['source_node'],
            target_node=data['target_node'],
            payload=data['payload'],
            timestamp=data['timestamp'],
            priority=data.get('priority', 0)
        )


class RedisMessenger:
    """
    Redis-based message broker for distributed simulation.
    """

    def __init__(
        self,
        redis_url: str = 'redis://localhost:6379',
        node_id: str | None = None
    ):
        self.redis_url = redis_url
        self.node_id = node_id or f"node_{datetime.now().timestamp()}"
        self.redis = None
        self.subscribers: dict[MessageType, list[Callable]] = {}
        self.message_count = 0

        # Try to import redis
        try:
            import redis as redis_lib
            self.redis_lib = redis_lib
        except ImportError:
            self.redis_lib = None
            print("Warning: redis not installed. Using mock mode.")

    def connect(self) -> bool:
        """Connect to Redis."""
        if not self.redis_lib:
            return False

        try:
            self.redis = self.redis_lib.from_url(self.redis_url)
            self.redis.ping()
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return False

    def publish(self, message: Message) -> bool:
        """Publish message to Redis."""
        if not self.redis:
            # Mock mode - just call local subscribers
            self._notify_subscribers(message)
            return True

        try:
            channel = f"cabw:{message.msg_type.name}"
            self.redis.publish(channel, message.to_json())

            if message.target_node:
                # Also publish to node-specific channel
                self.redis.publish(
                    f"cabw:node:{message.target_node}",
                    message.to_json()
                )

            self.message_count += 1
            return True
        except Exception as e:
            print(f"Publish error: {e}")
            return False

    def subscribe(
        self,
        msg_type: MessageType,
        callback: Callable[[Message], None]
    ):
        """Subscribe to message type."""
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        self.subscribers[msg_type].append(callback)

    def start_listening(self):
        """Start listening for messages (blocking)."""
        if not self.redis:
            return

        import threading

        def listen():
            pubsub = self.redis.pubsub()

            # Subscribe to all message type channels
            for msg_type in MessageType:
                pubsub.subscribe(f"cabw:{msg_type.name}")

            # Subscribe to node-specific channel
            pubsub.subscribe(f"cabw:node:{self.node_id}")

            print(f"Node {self.node_id} listening for messages...")

            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        msg = Message.from_json(message['data'])
                        self._notify_subscribers(msg)
                    except Exception as e:
                        print(f"Message parse error: {e}")

        # Start listener in background thread
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()

    def _notify_subscribers(self, message: Message):
        """Notify all subscribers of message."""
        callbacks = self.subscribers.get(message.msg_type, [])
        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Subscriber error: {e}")

    def send_agent_migrate(
        self,
        agent_data: dict[str, Any],
        from_node: str,
        to_node: str
    ) -> bool:
        """Send agent migration message."""
        msg = Message(
            msg_id=f"migrate_{self.message_count}",
            msg_type=MessageType.AGENT_MIGRATE,
            source_node=from_node,
            target_node=to_node,
            payload={'agent': agent_data},
            priority=10
        )
        return self.publish(msg)

    def broadcast_sync_request(self, tick: int) -> bool:
        """Broadcast synchronization request."""
        msg = Message(
            msg_id=f"sync_{tick}",
            msg_type=MessageType.SYNC_REQUEST,
            source_node=self.node_id,
            target_node=None,  # Broadcast
            payload={'tick': tick},
            priority=5
        )
        return self.publish(msg)

    def send_heartbeat(self) -> bool:
        """Send heartbeat message."""
        msg = Message(
            msg_id=f"hb_{self.message_count}",
            msg_type=MessageType.HEARTBEAT,
            source_node=self.node_id,
            target_node=None,
            payload={'timestamp': datetime.now().isoformat()}
        )
        return self.publish(msg)

    def get_stats(self) -> dict[str, Any]:
        """Get messenger statistics."""
        return {
            'node_id': self.node_id,
            'connected': self.redis is not None,
            'messages_sent': self.message_count,
            'subscribers': {
                msg_type.name: len(callbacks)
                for msg_type, callbacks in self.subscribers.items()
            }
        }

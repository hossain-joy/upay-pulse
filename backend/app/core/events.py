import asyncio
import inspect
import json
import logging
from typing import Callable, Dict, List, Any
from backend.app.core.config import settings

logger = logging.getLogger("upay_pulse.events")

class HybridEventBus:
    """
    Hybrid event bus supporting:
    1. Real Redis pub-sub (for distributed or containerized deployment)
    2. Zero-dependency async In-Memory event queue (for standalone local execution)
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._redis_client = None
        self._is_redis_connected = False
        self._loop = None

    async def initialize(self):
        """Attempt Redis connection, fallback to in-memory bus on failure."""
        if not settings.USE_REDIS_FALLBACK:
            return

        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            await self._redis_client.ping()
            self._is_redis_connected = True
            logger.info("HybridEventBus connected to Redis: %s", settings.REDIS_URL)
        except Exception as e:
            self._is_redis_connected = False
            self._redis_client = None
            logger.info(
                "Redis server not detected on %s (%s). Using high-speed in-memory EventBus.",
                settings.REDIS_URL,
                str(e).strip()
            )

    async def publish(self, topic: str, data: Dict[str, Any]):
        """Publish an event to a topic."""
        payload = json.dumps(data)
        
        # Publish to Redis if connected
        if self._is_redis_connected and self._redis_client:
            try:
                await self._redis_client.publish(topic, payload)
            except Exception as e:
                logger.warning("Redis publish failed, falling back to in-memory: %s", e)

        # Always trigger in-memory subscribers for local fast dispatch
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as exc:
                    logger.error("Error executing subscriber for topic '%s': %s", topic, exc)

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):
        """Register a callback for an event topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug("Subscribed to event topic: %s", topic)

    def status(self) -> Dict[str, Any]:
        """Return bus operating status."""
        return {
            "mode": "redis" if self._is_redis_connected else "in_memory",
            "redis_connected": self._is_redis_connected,
            "active_topics": list(self._subscribers.keys())
        }

event_bus = HybridEventBus()

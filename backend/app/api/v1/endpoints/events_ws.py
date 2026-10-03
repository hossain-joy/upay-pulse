import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from backend.app.core.events import event_bus

logger = logging.getLogger("upay_pulse.websocket")

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections for real-time telemetry."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast payload to all active clients."""
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send WebSocket message: %s", e)
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

# Hook event_bus into WebSocket manager for automatic live relay
async def handle_bus_event(topic: str, data: Dict[str, Any]):
    await manager.broadcast({
        "type": "BUS_EVENT",
        "topic": topic,
        "payload": data
    })

def make_bus_handler(topic_name: str):
    def _bus_callback(data: Dict[str, Any]):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(handle_bus_event(topic_name, data))
        except RuntimeError:
            pass
    return _bus_callback

# Register event_bus topics to pipe directly to WebSocket clients
for topic in [
    "transaction.created",
    "transaction.flagged",
    "risk.score.generated",
    "account.freeze.completed",
    "agent.liquidity.warning",
    "scam.report.created",
    "soundbox.trigger"
]:
    event_bus.subscribe(topic, make_bus_handler(topic))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket stream for Risk Console, Agent Terminal Soundbox, and Customer Freeze alerts.
    """
    await manager.connect(websocket)
    try:
        # Send initial handshake
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to upay Pulse Real-Time Event Stream",
            "active_clients": len(manager.active_connections)
        }))

        while True:
            # Keep connection open and receive optional ping / client events
            text_data = await websocket.receive_text()
            try:
                data = json.loads(text_data)
                # If client requests a test broadcast
                if data.get("action") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG", "timestamp": data.get("timestamp")}))
                elif data.get("action") == "SIMULATE_EVENT":
                    await manager.broadcast({
                        "type": "BUS_EVENT",
                        "topic": data.get("topic", "transaction.created"),
                        "payload": data.get("payload", {})
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket unexpected error: %s", exc)
        manager.disconnect(websocket)

@router.post("/broadcast")
async def trigger_broadcast(event: Dict[str, Any]):
    """
    HTTP trigger to publish an event into the bus and broadcast to all connected WebSocket clients.
    """
    topic = event.get("topic", "system.event")
    payload = event.get("payload", {})
    await event_bus.publish(topic, payload)
    await manager.broadcast({
        "type": "BUS_EVENT",
        "topic": topic,
        "payload": payload
    })
    return {"status": "broadcasted", "clients_notified": len(manager.active_connections)}

import pytest
from backend.app.core.events import event_bus

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "upay-pulse-backend"

def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"]["status"] == "healthy"
    assert "event_bus" in data

def test_api_v1_info_endpoint(client):
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert "SecurityAI" in data["pillars"]
    assert "CustomerAI" in data["pillars"]
    assert "AgentAI" in data["pillars"]

@pytest.mark.asyncio
async def test_event_bus_in_memory_dispatch():
    received = []

    def on_event(payload):
        received.append(payload)

    event_bus.subscribe("test.topic", on_event)
    await event_bus.publish("test.topic", {"msg": "hello_pulse"})
    
    assert len(received) == 1
    assert received[0]["msg"] == "hello_pulse"

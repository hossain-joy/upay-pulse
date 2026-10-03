import pytest
from starlette.testclient import TestClient
from backend.main import app

def test_websocket_connection_and_handshake():
    client = TestClient(app)
    with client.websocket_connect("/api/v1/events/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "CONNECTION_ESTABLISHED"
        assert "upay Pulse Real-Time Event Stream" in data["message"]
        
        # Test ping/pong
        websocket.send_json({"action": "PING", "timestamp": "2026-10-03T12:00:00Z"})
        pong = websocket.receive_json()
        assert pong["type"] == "PONG"

def test_broadcast_http_endpoint():
    client = TestClient(app)
    res = client.post("/api/v1/events/broadcast", json={
        "topic": "transaction.flagged",
        "payload": {
            "reference": "TXN-WS-TEST",
            "amount": 45000.0,
            "risk_score": 0.95
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "broadcasted"

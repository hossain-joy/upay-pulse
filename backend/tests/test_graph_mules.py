import pytest
import time
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.mule_graph import MuleGraphNode, MuleGraphEdge
from backend.app.models.scam import ScamReport, ScamReportStatus

def get_auth_token(client, email, password=None):
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_graph_topology_endpoint(client):
    admin_token = get_auth_token(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    start = time.perf_counter()
    res = client.get("/api/v1/graph/topology?limit=500", headers=headers)
    elapsed = (time.perf_counter() - start) * 1000

    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert "clusters" in data
    assert "summary" in data
    assert elapsed < 500  # Sub-500ms graph query latency

def test_mule_rings_and_ego_graph(client):
    admin_token = get_auth_token(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch detected mule rings
    rings_res = client.get("/api/v1/graph/mule-rings", headers=headers)
    assert rings_res.status_code == 200
    rings = rings_res.json()
    assert isinstance(rings, list)

    # 2. Extract ego graph for customer
    ego_res = client.get("/api/v1/graph/ego/+8801700000001?radius=2", headers=headers)
    assert ego_res.status_code == 200
    ego_data = ego_res.json()
    assert ego_data["center_node"] == "+8801700000001"
    assert "nodes" in ego_data
    assert "edges" in ego_data

def test_scam_reporting_and_freeze_cascade(client):
    # Customer files report
    c_token = get_auth_token(client, "customer@example.com")
    c_headers = {"Authorization": f"Bearer {c_token}"}

    report_payload = {
        "reported_account": "+8801700000002",
        "reason": "Impersonation and unauthorized funds demand",
        "investigation_notes": "Victim pressured via phone call"
    }

    report_res = client.post("/api/v1/scams/report", json=report_payload, headers=c_headers)
    assert report_res.status_code == 201
    report_data = report_res.json()
    assert report_data["status"] == "SUBMITTED"
    report_id = report_data["id"]

    # Verify RBAC: Customer cannot list all reports
    cust_list = client.get("/api/v1/scams/reports", headers=c_headers)
    assert cust_list.status_code == 403

    # Admin lists reports
    a_token = get_auth_token(client, "admin@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    admin_list = client.get("/api/v1/scams/reports", headers=a_headers)
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] >= 1

    # Admin resolves report as CONFIRMED_FRAUD with auto_freeze_account = True
    resolve_res = client.post(f"/api/v1/scams/reports/{report_id}/resolve", json={
        "status": "CONFIRMED_FRAUD",
        "investigation_notes": "Forensic audit confirmed scam syndicate connection",
        "auto_freeze_account": True
    }, headers=a_headers)

    assert resolve_res.status_code == 200
    resolved = resolve_res.json()
    assert resolved["status"] == "CONFIRMED_FRAUD"

    # Verify the reported account (+8801700000002) is now frozen in the database!
    db = SessionLocal()
    target_user = db.query(User).filter(User.phone == "+8801700000002").first()
    assert target_user is not None
    assert target_user.is_frozen is True
    db.close()

def test_graph_sync_to_database(client):
    a_token = get_auth_token(client, "admin@example.com")
    a_headers = {"Authorization": f"Bearer {a_token}"}

    sync_res = client.post("/api/v1/graph/sync", headers=a_headers)
    assert sync_res.status_code == 200
    stats = sync_res.json()
    assert "nodes_synced" in stats
    assert "edges_synced" in stats

    # Verify DB tables contain entries
    db = SessionLocal()
    node_count = db.query(MuleGraphNode).count()
    assert node_count == stats["nodes_synced"]
    db.close()

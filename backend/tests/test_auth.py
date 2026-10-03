import pytest
import uuid

def test_customer_registration_and_login(client):
    uid = uuid.uuid4().hex[:6]
    test_phone = f"+8801799{uid}"
    test_email = f"user_{uid}@example.com"

    # 1. Register a new customer
    reg_payload = {
        "phone": test_phone,
        "email": test_email,
        "password": "Password@123",
        "role": "CUSTOMER",
        "full_name": "Tariqul Islam",
        "freeze_pin": "5678",
        "profession": "Software Engineer",
        "location": "Mohakhali, Dhaka"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["role"] == "CUSTOMER"
    assert reg_data["user"]["profile"]["wallet_balance"] == 500.00

    # 2. Prevent duplicate phone
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "PHONE_ALREADY_EXISTS"

    # 3. Login with email
    login_res = client.post("/api/v1/auth/login", json={
        "identifier": test_email,
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 4. Login with phone
    login_phone_res = client.post("/api/v1/auth/login", json={
        "identifier": test_phone,
        "password": "Password@123"
    })
    assert login_phone_res.status_code == 200

    # 5. Login with invalid password
    bad_login_res = client.post("/api/v1/auth/login", json={
        "identifier": test_email,
        "password": "WrongPassword!"
    })
    assert bad_login_res.status_code == 401
    assert bad_login_res.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # 6. Verify GET /me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == test_email

def test_rbac_customer_agent_admin_isolation(client):
    # Customer Login
    c_login = client.post("/api/v1/auth/login", json={
        "identifier": "customer@example.com",
        "password": "Demo@1234"
    })
    assert c_login.status_code == 200
    c_token = c_login.json()["access_token"]
    c_headers = {"Authorization": f"Bearer {c_token}"}

    # Agent Login
    a_login = client.post("/api/v1/auth/login", json={
        "identifier": "agent@example.com",
        "password": "Demo@1234"
    })
    assert a_login.status_code == 200
    a_token = a_login.json()["access_token"]
    a_headers = {"Authorization": f"Bearer {a_token}"}

    # Admin Login
    adm_login = client.post("/api/v1/auth/login", json={
        "identifier": "admin@example.com",
        "password": "Admin@1234"
    })
    assert adm_login.status_code == 200
    adm_token = adm_login.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # Test Customer route access
    assert client.get("/api/v1/auth/rbac-test/customer-only", headers=c_headers).status_code == 200
    # Agent trying to access Customer route -> 403 Forbidden
    assert client.get("/api/v1/auth/rbac-test/customer-only", headers=a_headers).status_code == 403

    # Test Agent route access
    assert client.get("/api/v1/auth/rbac-test/agent-only", headers=a_headers).status_code == 200
    # Customer trying to access Agent route -> 403 Forbidden
    assert client.get("/api/v1/auth/rbac-test/agent-only", headers=c_headers).status_code == 403

    # Test Admin route access
    assert client.get("/api/v1/auth/rbac-test/admin-only", headers=adm_headers).status_code == 200
    # Customer trying to access Admin route -> 403 Forbidden
    assert client.get("/api/v1/auth/rbac-test/admin-only", headers=c_headers).status_code == 403
    # Agent trying to access Admin route -> 403 Forbidden
    assert client.get("/api/v1/auth/rbac-test/admin-only", headers=a_headers).status_code == 403

def test_session_logout_and_revocation(client):
    login = client.post("/api/v1/auth/login", json={
        "identifier": "victim@example.com",
        "password": "Demo@1234"
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session works
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Reusing the old token must now be rejected (Session Revoked)
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert revoked_res.json()["error"]["code"] == "SESSION_REVOKED"

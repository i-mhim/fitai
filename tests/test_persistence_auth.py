"""Persistence, account ownership and authentication tests."""
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import SessionLocal
from app.assessments.store import load_assessment

client = TestClient(app)

def register():
    r = client.post("/v1/auth/register", json={"email": f"{uuid4()}@example.com", "password": "safe-password-for-tests"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def start(token):
    return client.post("/v1/assessments", headers=auth(token), json={"goal_type": "handstand_hold", "target_value": 10, "requested_weeks": 8})

def test_assessment_requires_login():
    assert client.post("/v1/assessments", json={"goal_type": "handstand_hold", "target_value": 10, "requested_weeks": 8}).status_code == 401
    assert client.get("/v1/assessments/missing/summary").status_code == 401

def test_assessment_is_owner_scoped():
    a, b = register(), register()
    sid = start(a).json()["assessment_id"]
    assert client.get(f"/v1/assessments/{sid}/summary", headers=auth(a)).status_code == 200
    assert client.get(f"/v1/assessments/{sid}/summary", headers=auth(b)).status_code == 404
    assert client.post(f"/v1/assessments/{sid}/answers", headers=auth(b), json={"question_id": "safety_red_flags", "value": "no"}).status_code == 404

def test_answer_persists_across_database_sessions():
    from jwt import decode
    from os import environ
    token = register()
    sid = start(token).json()["assessment_id"]
    assert client.post(f"/v1/assessments/{sid}/answers", headers=auth(token), json={"question_id": "safety_red_flags", "value": "no"}).status_code == 200
    with SessionLocal() as db:
        user_id = decode(token, environ["FITAI_JWT_SECRET"], algorithms=["HS256"], issuer="fitai", audience="fitai-api")["sub"]
        saved = load_assessment(db, sid, user_id)
        assert saved is not None
        assert saved[1].answers == {"safety_red_flags": "no"}

def test_safety_pause_survives_reload():
    token = register()
    sid = start(token).json()["assessment_id"]
    response = client.post(f"/v1/assessments/{sid}/answers", headers=auth(token), json={"question_id": "safety_red_flags", "value": "yes"})
    assert response.json()["status"] == "needs_professional_review"
    summary = client.get(f"/v1/assessments/{sid}/summary", headers=auth(token)).json()
    assert summary["safety_flags"] == ["safety_red_flags"]

def test_login_and_invalid_password():
    email = f"{uuid4()}@example.com"
    password = "test-password-at-least-twelve"
    assert client.post("/v1/auth/register", json={"email": email, "password": password}).status_code == 201
    assert client.post("/v1/auth/register", json={"email": email.upper(), "password": password}).status_code == 409
    assert client.post("/v1/auth/login", json={"email": email, "password": "not-the-correct-password"}).status_code == 401
    token = client.post("/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    assert client.get("/v1/auth/me", headers=auth(token)).json()["email"] == email

def test_invalid_token_rejected():
    assert client.get("/v1/auth/me", headers=auth("garbage.token.here")).status_code == 401

def test_duplicate_answer_rejected():
    token = register()
    sid = start(token).json()["assessment_id"]
    payload = {"question_id": "safety_red_flags", "value": "no"}
    assert client.post(f"/v1/assessments/{sid}/answers", headers=auth(token), json=payload).status_code == 200
    assert client.post(f"/v1/assessments/{sid}/answers", headers=auth(token), json=payload).status_code == 409
    assert len(client.get(f"/v1/assessments/{sid}/summary", headers=auth(token)).json()["answers"]) == 1

"""Authenticated feasibility endpoint tests against the persisted assessment flow."""
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def register():
    r = client.post("/v1/auth/register", json={
        "email": f"feasibility-{uuid4()}@example.com",
        "password": "test-only-password-twelve-plus",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def start(headers, goal_type="pushup_repetitions", weeks=8):
    r = client.post("/v1/assessments", headers=headers, json={
        "goal_type": goal_type,
        "target_value": 25 if goal_type == "pushup_repetitions" else 10,
        "requested_weeks": weeks,
    })
    assert r.status_code == 201, r.text
    return r.json()


def answer_all(headers, state, answers):
    for key, val in answers:
        assert state["next_question"]["id"] == key
        r = client.post(f"/v1/assessments/{state['assessment_id']}/answers",
                        headers=headers, json={"question_id": key, "value": val})
        assert r.status_code == 200, r.text
        state = r.json()
    return state


def test_feasibility_requires_authentication():
    assert client.get("/v1/assessments/unknown/feasibility").status_code == 401


def test_non_owner_cannot_read_feasibility():
    a = register()
    b = register()
    sid = start(a)["assessment_id"]
    assert client.get(f"/v1/assessments/{sid}/feasibility", headers=b).status_code == 404
    assert client.get(f"/v1/assessments/{sid}/feasibility", headers=a).status_code == 200


def test_incomplete_and_safety_pause_api():
    headers = register()
    state = start(headers)
    url = f"/v1/assessments/{state['assessment_id']}/feasibility"
    assert client.get(url, headers=headers).json()["status"] == "needs_assessment"
    state = answer_all(headers, state, [("safety_red_flags", "yes")])
    res = client.get(url, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "needs_professional_review"
    assert res.json()["milestone_keys"] == []


def test_completed_pushup_feasibility_api():
    headers = register()
    state = start(headers)
    state = answer_all(headers, state, [
        ("safety_red_flags", "no"),
        ("training_history", "occasional"),
        ("pu_upper_body_pain", "no"),
        ("pu_baseline_reps", 12),
        ("pu_technique", "controlled"),
    ])
    assert state["status"] == "completed"
    res = client.get(f"/v1/assessments/{state['assessment_id']}/feasibility", headers=headers)
    assert res.status_code == 200, res.text
    result = res.json()
    assert result["status"] == "conditional"
    assert result["timeline_status"] == "unverified"
    assert result["target_gap_repetitions"] == 13
    assert result["policy_version"]


def test_short_handstand_deadline_is_not_promised():
    headers = register()
    state = start(headers, goal_type="handstand_hold", weeks=1)
    state = answer_all(headers, state, [
        ("safety_red_flags", "no"),
        ("training_history", "regular_strength"),
        ("hs_wrist_pain", "no"),
        ("hs_overhead_control", "comfortable"),
        ("hs_inversion_experience", "never"),
        ("hs_core_control", "yes"),
    ])
    result = client.get(f"/v1/assessments/{state['assessment_id']}/feasibility", headers=headers).json()
    assert result["timeline_status"] == "unsupported_automatic_deadline"
    assert result["status"] == "conditional"

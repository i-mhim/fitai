from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_handstand_preview_requires_specific_assessments() -> None:
    response = client.post("/v1/goals/preview", json={
        "goal_type": "handstand_hold",
        "target_value": 10,
        "requested_weeks": 8,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["target_unit"] == "seconds"
    assert "wrist_tolerance" in result["assessment_modules"]
    assert "inversion_experience" in result["assessment_modules"]
    assert result["next_step"] == "safety_screening"
    assert result["feasibility_status"] == "not_evaluated"


def test_pushup_goal_has_different_assessments() -> None:
    response = client.post("/v1/goals/preview", json={
        "goal_type": "pushup_repetitions",
        "target_value": 25,
        "requested_weeks": 12,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["target_unit"] == "repetitions"
    assert "pushup_technique" in result["assessment_modules"]
    assert "inversion_experience" not in result["assessment_modules"]


def test_rejects_impossible_target_value() -> None:
    response = client.post("/v1/goals/preview", json={
        "goal_type": "handstand_hold",
        "target_value": 0,
        "requested_weeks": 8,
    })
    assert response.status_code == 422


def test_rejects_unknown_goal_type() -> None:
    response = client.post("/v1/goals/preview", json={
        "goal_type": "marathon",
        "target_value": 1,
        "requested_weeks": 8,
    })
    assert response.status_code == 422


def test_rejects_out_of_bounds_deadline() -> None:
    response = client.post("/v1/goals/preview", json={
        "goal_type": "handstand_hold",
        "target_value": 10,
        "requested_weeks": 0,
    })
    assert response.status_code == 422

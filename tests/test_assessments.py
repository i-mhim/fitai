"""Behavioral tests for question branching, validation, and safety pauses."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def start(goal_type="handstand_hold") -> dict:
    response = client.post("/v1/assessments", json={
        "goal_type": goal_type,
        "target_value": 10 if goal_type == "handstand_hold" else 25,
        "requested_weeks": 8,
    })
    assert response.status_code == 201, response.text
    assert response.json()["next_question"]["id"] == "safety_red_flags"
    return response.json()


def answer(state: dict, value) -> dict:
    assert state["status"] == "in_progress"
    question_id = state["next_question"]["id"]
    response = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
        "question_id": question_id,
        "value": value,
    })
    assert response.status_code == 200, response.text
    return response.json()


def finish(responses: dict, goal_type="handstand_hold") -> tuple[list[str], dict]:
    state = start(goal_type)
    visited: list[str] = []
    for _ in range(20):
        if state["status"] != "in_progress":
            return visited, state
        question_id = state["next_question"]["id"]
        visited.append(question_id)
        assert question_id in responses, f"Missing test response for {question_id}"
        state = answer(state, responses[question_id])
    raise AssertionError("Assessment did not terminate")


def test_beginner_handstand_gets_foundational_questions() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "none",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "limited",
        "hs_overhead_pain": "no",
        "hs_inversion_experience": "never",
        "hs_pushup_capacity": 2,
        "hs_core_control": "no",
    })
    assert state["status"] == "completed"
    assert state["next_question"] is None
    assert questions == [
        "safety_red_flags", "training_history", "hs_wrist_pain",
        "hs_overhead_control", "hs_overhead_pain", "hs_inversion_experience",
        "hs_pushup_capacity", "hs_core_control",
    ]
    summary = client.get(f"/v1/assessments/{state['assessment_id']}/summary").json()
    assert summary["status"] == "completed"
    assert summary["next_step"] == "baseline_review"
    assert "core_control" in summary["modules_covered"]
    assert summary["question_bank_version"] == "2026-11-v1"
    assert len(summary["answers"]) == 8


def test_bodybuilder_not_forced_through_beginner_pushup_baseline() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "regular_strength",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "comfortable",
        "hs_inversion_experience": "never",
        "hs_core_control": "unsure",
    })
    assert state["status"] == "completed"
    assert "hs_pushup_capacity" not in questions
    assert "hs_core_control" in questions
    assert "hs_wrist_pain" in questions  # Strength does not prove skill readiness.


def test_calisthenics_experience_gets_hold_duration_not_basic_strength() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "regular_calisthenics",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "comfortable",
        "hs_inversion_experience": "wall_supported",
        "hs_wall_hold_seconds": 25,
    })
    assert state["status"] == "completed"
    assert questions[-1] == "hs_wall_hold_seconds"
    assert "hs_pushup_capacity" not in questions


def test_concerning_safety_answer_halts_immediately() -> None:
    state = start()
    state = answer(state, "yes")
    assert state["status"] == "needs_professional_review"
    assert state["safety_flags"] == ["safety_red_flags"]
    assert state["next_question"] is None
    summary = client.get(f"/v1/assessments/{state['assessment_id']}/summary").json()
    assert summary["next_step"] == "professional_guidance"
    assert len(summary["answers"]) == 1


def test_unsure_red_flags_also_pauses() -> None:
    state = answer(start(), "unsure")
    assert state["status"] == "needs_professional_review"


def test_wrist_pain_halts_handstand_assessment() -> None:
    state = start()
    state = answer(state, "no")
    state = answer(state, "regular_strength")
    state = answer(state, "yes")
    assert state["status"] == "needs_professional_review"
    assert state["safety_flags"] == ["hs_wrist_pain"]
    assert state["next_question"] is None


def test_overhead_pain_follow_up_halts_handstand_assessment() -> None:
    state = start()
    for value in ["no", "regular_strength", "no", "limited"]:
        state = answer(state, value)
    assert state["next_question"]["id"] == "hs_overhead_pain"
    state = answer(state, "yes")
    assert state["status"] == "needs_professional_review"
    assert state["safety_flags"] == ["hs_overhead_pain"]


def test_pushup_zero_asks_for_incline_baseline() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "none",
        "pu_upper_body_pain": "no",
        "pu_baseline_reps": 0,
        "pu_incline_reps": 5,
    }, goal_type="pushup_repetitions")
    assert state["status"] == "completed"
    assert "pu_incline_reps" in questions
    assert "pu_technique" not in questions


def test_pushup_positive_baseline_asks_technique() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "occasional",
        "pu_upper_body_pain": "no",
        "pu_baseline_reps": 12,
        "pu_technique": "inconsistent",
    }, goal_type="pushup_repetitions")
    assert state["status"] == "completed"
    assert questions[-1] == "pu_technique"


def test_unknown_numeric_value_is_not_zero() -> None:
    questions, state = finish({
        "safety_red_flags": "no",
        "training_history": "none",
        "pu_upper_body_pain": "no",
        "pu_baseline_reps": "unknown",
    }, goal_type="pushup_repetitions")
    assert state["status"] == "completed"
    assert "pu_incline_reps" not in questions
    assert "pu_technique" not in questions


def test_pushup_pain_pauses_before_baseline() -> None:
    state = start("pushup_repetitions")
    state = answer(state, "no")
    state = answer(state, "none")
    state = answer(state, "unsure")
    assert state["status"] == "needs_professional_review"
    assert state["safety_flags"] == ["pu_upper_body_pain"]


def test_invalid_choice_rejected_without_mutating_session() -> None:
    state = start()
    res = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
        "question_id": "safety_red_flags", "value": "perhaps",
    })
    assert res.status_code == 422
    current = client.get(f"/v1/assessments/{state['assessment_id']}/next").json()
    assert current["answered_count"] == 0
    assert current["next_question"]["id"] == "safety_red_flags"


def test_out_of_order_answer_rejected() -> None:
    state = start()
    res = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
        "question_id": "hs_wall_hold_seconds", "value": 50,
    })
    assert res.status_code == 409


def test_duplicate_answer_rejected() -> None:
    state = start()
    state = answer(state, "no")
    res = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
        "question_id": "safety_red_flags", "value": "no",
    })
    assert res.status_code == 409
    assert state["answered_count"] == 1


def test_invalid_numeric_and_boolean_rejected() -> None:
    state = start("pushup_repetitions")
    for value in ["no", "none", "no"]:
        state = answer(state, value)
    assert state["next_question"]["id"] == "pu_baseline_reps"
    for invalid in [-1, 201, "twelve", True, 4.5]:
        res = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
            "question_id": "pu_baseline_reps", "value": invalid,
        })
        assert res.status_code == 422, (invalid, res.text)
    assert client.get(f"/v1/assessments/{state['assessment_id']}/next").json()["answered_count"] == 3


def test_completed_assessment_cannot_accept_more_answers() -> None:
    _, state = finish({
        "safety_red_flags": "no",
        "training_history": "regular_strength",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "comfortable",
        "hs_inversion_experience": "never",
        "hs_core_control": "yes",
    })
    res = client.post(f"/v1/assessments/{state['assessment_id']}/answers", json={
        "question_id": "hs_inversion_experience", "value": "never",
    })
    assert res.status_code == 409


def test_missing_session_and_invalid_goal() -> None:
    assert client.get("/v1/assessments/no-such-session/next").status_code == 404
    assert client.get("/v1/assessments/no-such-session/summary").status_code == 404
    response = client.post("/v1/assessments", json={
        "goal_type": "unsupported", "target_value": 10, "requested_weeks": 8,
    })
    assert response.status_code == 422


def test_question_view_has_version_and_answer_metadata() -> None:
    state = start()
    question = state["next_question"]
    assert question["version"] == 1
    assert question["kind"] == "single_choice"
    assert {option["id"] for option in question["options"]} == {"yes", "no", "unsure"}

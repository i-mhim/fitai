"""Run two synthetic assessment sessions without starting an HTTP server.

From backend/: python -m scripts.demo_assessment
"""

from fastapi.testclient import TestClient

from app.main import app


def demonstrate(name: str, answers: dict[str, str | int]) -> None:
    with TestClient(app) as client:
        initial = client.post(
            "/v1/assessments",
            json={"goal_type": "handstand_hold", "target_value": 10, "requested_weeks": 8},
        )
        initial.raise_for_status()
        state = initial.json()
        assessment_id = state["assessment_id"]

        print(f"\n{name}")
        while state["status"] == "in_progress":
            question_id = state["next_question"]["id"]
            value = answers[question_id]
            print(f"  {question_id:<28} -> {value}")
            response = client.post(
                f"/v1/assessments/{assessment_id}/answers",
                json={"question_id": question_id, "value": value},
            )
            response.raise_for_status()
            state = response.json()

        print(f"  Final status: {state['status']}")
        print(f"  Questions answered: {state['answered_count']}")


if __name__ == "__main__":
    demonstrate("BEGINNER", {
        "safety_red_flags": "no",
        "training_history": "none",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "limited",
        "hs_overhead_pain": "no",
        "hs_inversion_experience": "never",
        "hs_pushup_capacity": 2,
        "hs_core_control": "no",
    })
    demonstrate("EXPERIENCED STRENGTH TRAINER", {
        "safety_red_flags": "no",
        "training_history": "regular_strength",
        "hs_wrist_pain": "no",
        "hs_overhead_control": "comfortable",
        "hs_inversion_experience": "never",
        "hs_core_control": "unsure",
    })

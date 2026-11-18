"""Conditional question selection and safety routing.

All decisions are deterministic and inspectable. This is a prototype, not a
clinical screening tool or a fitness-prescription engine.
"""

from dataclasses import dataclass, field
from typing import Any

from app.goals.schemas import GoalPreviewRequest
from app.assessments.questions import QUESTIONS, QUESTION_BANK_VERSION, Question


@dataclass
class AssessmentSession:
    id: str
    goal: GoalPreviewRequest
    question_bank_version: str = QUESTION_BANK_VERSION
    answers: dict[str, int | str] = field(default_factory=dict)
    status: str = "in_progress"
    safety_flags: list[str] = field(default_factory=list)


def question_order(session: AssessmentSession) -> list[str]:
    """Build required question IDs from previously submitted answers."""
    answers = session.answers
    order = ["safety_red_flags", "training_history"]

    if session.goal.goal_type == "handstand_hold":
        order += ["hs_wrist_pain", "hs_overhead_control"]
        if answers.get("hs_overhead_control") in {"limited", "unsure"}:
            order.append("hs_overhead_pain")
        order.append("hs_inversion_experience")
        experience = answers.get("training_history")
        inversion = answers.get("hs_inversion_experience")
        if inversion == "never":
            if experience in {"none", "occasional"}:
                order.append("hs_pushup_capacity")
            # Experienced lifters may still lack the specific core control.
            order.append("hs_core_control")
        elif inversion in {
            "wall_supported", "occasional_freestanding", "consistent_freestanding"
        }:
            order.append("hs_wall_hold_seconds")
    else:
        order += ["pu_upper_body_pain", "pu_baseline_reps"]
        baseline = answers.get("pu_baseline_reps")
        if type(baseline) is int and baseline == 0:
            order.append("pu_incline_reps")
        elif type(baseline) is int and baseline > 0:
            order.append("pu_technique")
        # 'unknown' baseline deliberately does not force an unsupported assumption.

    return order


def next_question(session: AssessmentSession) -> Question | None:
    if session.status != "in_progress":
        return None
    for question_id in question_order(session):
        if question_id not in session.answers:
            return QUESTIONS[question_id]
    return None


def validate_value(question: Question, value: Any) -> None:
    """Raise ValueError on invalid input. Never quietly coerce user answers."""
    if question.kind == "single_choice":
        valid = {option.id for option in question.options}
        if type(value) is not str or value not in valid:
            raise ValueError(f"Answer must be one of: {', '.join(sorted(valid))}")
        return

    if value == "unknown" and type(value) is str:
        return
    if type(value) is not int:
        raise ValueError("Answer must be an integer or the string 'unknown'")
    if not (question.minimum <= value <= question.maximum):
        raise ValueError(
            f"Answer must be between {question.minimum} and {question.maximum}"
        )


def record_answer(session: AssessmentSession, question_id: str, value: int | str) -> None:
    current = next_question(session)
    if current is None or current.id != question_id:
        raise RuntimeError("Only the current unanswered question may be submitted")
    validate_value(current, value)
    session.answers[question_id] = value

    # These are conservative pauses, not diagnoses or medical-clearance decisions.
    if question_id in {"safety_red_flags", "hs_wrist_pain", "hs_overhead_pain", "pu_upper_body_pain"}:
        if value in {"yes", "unsure"}:
            session.safety_flags.append(question_id)
            session.status = "needs_professional_review"
            return

    if next_question(session) is None:
        session.status = "completed"

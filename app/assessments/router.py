"""Local demo API. Not safe for multi-user deployment without authorization."""

from fastapi import APIRouter, HTTPException

from app.goals.schemas import GoalPreviewRequest
from app.assessments.engine import AssessmentSession, next_question, record_answer
from app.assessments.questions import QUESTIONS, Question
from app.assessments.schemas import (
    AnswerSubmission,
    AssessmentStateView,
    AssessmentSummaryView,
    OptionView,
    QuestionView,
    RecordedAnswerView,
)
from app.assessments.store import InMemoryAssessmentStore

router = APIRouter(prefix="/v1/assessments", tags=["assessments"])
store = InMemoryAssessmentStore()


def question_view(question: Question | None) -> QuestionView | None:
    if question is None:
        return None
    return QuestionView(
        id=question.id,
        version=question.version,
        module=question.module,
        prompt=question.prompt,
        kind=question.kind,
        options=[OptionView(id=o.id, label=o.label) for o in question.options],
        minimum=question.minimum,
        maximum=question.maximum,
        hint=question.hint,
    )


def state_view(session: AssessmentSession) -> AssessmentStateView:
    messages = {
        "in_progress": "Answer the next question. No exercise testing is required.",
        "completed": "Preliminary self-reported assessment complete; no medical clearance or plan has been provided.",
        "needs_professional_review": "Assessment paused. Seek appropriate professional guidance before continuing relevant exercise testing.",
    }
    return AssessmentStateView(
        assessment_id=session.id,
        question_bank_version=session.question_bank_version,
        goal=session.goal,
        status=session.status,
        answered_count=len(session.answers),
        next_question=question_view(next_question(session)),
        safety_flags=list(session.safety_flags),
        message=messages[session.status],
    )


def require_session(assessment_id: str) -> AssessmentSession:
    session = store.get(assessment_id)
    if session is None:
        raise HTTPException(404, detail="Assessment session not found")
    return session


@router.post("", response_model=AssessmentStateView, status_code=201)
def start_assessment(goal: GoalPreviewRequest) -> AssessmentStateView:
    """Start assessment using the same validated goal schema as /v1/goals/preview."""
    with store.lock:
        return state_view(store.create(goal))


@router.get("/{assessment_id}/next", response_model=AssessmentStateView)
def get_next_assessment_question(assessment_id: str) -> AssessmentStateView:
    with store.lock:
        return state_view(require_session(assessment_id))


@router.post("/{assessment_id}/answers", response_model=AssessmentStateView)
def submit_answer(assessment_id: str, submission: AnswerSubmission) -> AssessmentStateView:
    with store.lock:
        session = require_session(assessment_id)
        try:
            record_answer(session, submission.question_id, submission.value)
        except ValueError as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, detail=str(exc)) from exc
        return state_view(session)


@router.get("/{assessment_id}/summary", response_model=AssessmentSummaryView)
def get_assessment_summary(assessment_id: str) -> AssessmentSummaryView:
    with store.lock:
        session = require_session(assessment_id)
        answer_views = [
            RecordedAnswerView(
                question_id=question_id,
                question_version=QUESTIONS[question_id].version,
                module=QUESTIONS[question_id].module,
                value=value,
            )
            for question_id, value in session.answers.items()
        ]
        step = {
            "in_progress": "continue_assessment",
            "needs_professional_review": "professional_guidance",
            "completed": "baseline_review",
        }[session.status]
        return AssessmentSummaryView(
            assessment_id=session.id,
            question_bank_version=session.question_bank_version,
            goal=session.goal,
            status=session.status,
            answers=answer_views,
            modules_covered=list(dict.fromkeys(a.module for a in answer_views)),
            safety_flags=list(session.safety_flags),
            next_step=step,
            note="Self-reported responses only. This prototype does not offer medical clearance, exercise prescriptions, or goal-feasibility predictions.",
        )

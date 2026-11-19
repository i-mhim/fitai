"""Authenticated, durable assessment API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.core.db import get_db
from app.core.models import User
from app.goals.schemas import GoalPreviewRequest
from app.assessments.engine import AssessmentSession, next_question, record_answer
from app.assessments.questions import QUESTIONS, Question
from app.assessments.schemas import AnswerSubmission, AssessmentStateView, AssessmentSummaryView, OptionView, QuestionView, RecordedAnswerView
from app.assessments.store import create_assessment, load_assessment, persist_answer

router = APIRouter(prefix="/v1/assessments", tags=["assessments"])


def question_view(question: Question | None) -> QuestionView | None:
    if question is None:
        return None
    return QuestionView(id=question.id, version=question.version, module=question.module, prompt=question.prompt, kind=question.kind,
                        options=[OptionView(id=o.id, label=o.label) for o in question.options], minimum=question.minimum, maximum=question.maximum, hint=question.hint)


def state_view(session: AssessmentSession) -> AssessmentStateView:
    messages = {
        "in_progress": "Answer the next question. No exercise testing is required.",
        "completed": "Preliminary self-reported assessment complete; no medical clearance or plan has been provided.",
        "needs_professional_review": "Assessment paused. Seek appropriate professional guidance before continuing relevant exercise testing.",
    }
    return AssessmentStateView(assessment_id=session.id, question_bank_version=session.question_bank_version,
                               goal=session.goal, status=session.status, answered_count=len(session.answers),
                               next_question=question_view(next_question(session)), safety_flags=list(session.safety_flags),
                               message=messages[session.status])


def require_session(db: Session, assessment_id: str, user: User, *, for_update: bool = False):
    result = load_assessment(db, assessment_id, user.id, for_update=for_update)
    if result is None:
        raise HTTPException(404, detail="Assessment session not found")
    return result


@router.post("", response_model=AssessmentStateView, status_code=201)
def start_assessment(goal: GoalPreviewRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AssessmentStateView:
    return state_view(create_assessment(db, user.id, goal))


@router.get("/{assessment_id}/next", response_model=AssessmentStateView)
def get_next_assessment_question(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AssessmentStateView:
    _, session = require_session(db, assessment_id, user)
    return state_view(session)


@router.post("/{assessment_id}/answers", response_model=AssessmentStateView)
def submit_answer(assessment_id: str, submission: AnswerSubmission, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AssessmentStateView:
    record, session = require_session(db, assessment_id, user, for_update=True)
    try:
        record_answer(session, submission.question_id, submission.value)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    persist_answer(db, record, session, submission.question_id)
    return state_view(session)


@router.get("/{assessment_id}/summary", response_model=AssessmentSummaryView)
def get_assessment_summary(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AssessmentSummaryView:
    _, session = require_session(db, assessment_id, user)
    answer_views = [RecordedAnswerView(question_id=q, question_version=QUESTIONS[q].version, module=QUESTIONS[q].module, value=v) for q, v in session.answers.items()]
    step = {"in_progress": "continue_assessment", "needs_professional_review": "professional_guidance", "completed": "baseline_review"}[session.status]
    return AssessmentSummaryView(assessment_id=session.id, question_bank_version=session.question_bank_version, goal=session.goal,
                                 status=session.status, answers=answer_views, modules_covered=list(dict.fromkeys(a.module for a in answer_views)),
                                 safety_flags=list(session.safety_flags), next_step=step,
                                 note="Self-reported responses only. This prototype does not offer medical clearance, exercise prescriptions, or goal-feasibility predictions.")

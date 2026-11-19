"""Durable assessment persistence. Access is scoped to the authenticated user."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.models import AssessmentAnswer, AssessmentRecord
from app.assessments.engine import AssessmentSession
from app.assessments.questions import QUESTIONS
from app.goals.schemas import GoalPreviewRequest


def from_record(record: AssessmentRecord) -> AssessmentSession:
    return AssessmentSession(
        id=record.id,
        goal=GoalPreviewRequest(goal_type=record.goal_type, target_value=record.target_value, requested_weeks=record.requested_weeks),
        question_bank_version=record.question_bank_version,
        answers={a.question_id: a.value for a in record.answers},
        status=record.status,
        safety_flags=list(record.safety_flags),
    )


def create_assessment(db: Session, owner_id: str, goal: GoalPreviewRequest) -> AssessmentSession:
    record = AssessmentRecord(user_id=owner_id, goal_type=goal.goal_type, target_value=goal.target_value, requested_weeks=goal.requested_weeks, question_bank_version=AssessmentSession(id="", goal=goal).question_bank_version, status="in_progress", safety_flags=[])
    db.add(record)
    db.commit()
    db.refresh(record)
    return from_record(record)


def load_assessment(db: Session, assessment_id: str, owner_id: str, *, for_update: bool = False) -> tuple[AssessmentRecord, AssessmentSession] | None:
    query = select(AssessmentRecord).where(AssessmentRecord.id == assessment_id, AssessmentRecord.user_id == owner_id)
    if for_update:
        query = query.with_for_update()
    query = query.options(selectinload(AssessmentRecord.answers))
    record = db.scalar(query)
    if record is None:
        return None
    return record, from_record(record)


def persist_answer(db: Session, record: AssessmentRecord, session: AssessmentSession, question_id: str) -> None:
    db.add(AssessmentAnswer(
        assessment_id=record.id, position=len(session.answers), question_id=question_id,
        question_version=QUESTIONS[question_id].version, value=session.answers[question_id],
    ))
    record.status = session.status
    record.safety_flags = list(session.safety_flags)
    db.commit()

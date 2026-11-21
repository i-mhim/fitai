"""Read-only feasibility API for the owner of a persisted assessment."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import get_current_user
from app.core.db import get_db
from app.core.models import User
from app.assessments.store import load_assessment
from app.feasibility.schemas import FeasibilityResponse
from app.feasibility.service import evaluate_feasibility

router = APIRouter(prefix="/v1/assessments", tags=["feasibility"])


@router.get("/{assessment_id}/feasibility", response_model=FeasibilityResponse)
def get_goal_feasibility(assessment_id: str, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)) -> FeasibilityResponse:
    saved = load_assessment(db, assessment_id, user.id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Assessment session not found")
    return evaluate_feasibility(saved[1])

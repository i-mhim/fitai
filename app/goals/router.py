from fastapi import APIRouter

from app.goals.schemas import GoalPreviewRequest, GoalPreviewResponse
from app.goals.service import preview_goal

router = APIRouter(prefix="/v1/goals", tags=["goals"])


@router.post("/preview", response_model=GoalPreviewResponse)
def create_goal_preview(goal: GoalPreviewRequest) -> GoalPreviewResponse:
    """Validate a goal and identify required assessments. Does not save data."""
    return preview_goal(goal)

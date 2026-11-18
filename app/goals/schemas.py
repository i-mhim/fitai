from typing import Literal

from pydantic import BaseModel, Field

GoalType = Literal["handstand_hold", "pushup_repetitions"]
TargetUnit = Literal["seconds", "repetitions"]


class GoalPreviewRequest(BaseModel):
    goal_type: GoalType
    target_value: int = Field(gt=0, description="Positive target in the goal's unit")
    requested_weeks: int = Field(ge=1, le=104)


class GoalPreviewResponse(BaseModel):
    goal: GoalPreviewRequest
    target_unit: TargetUnit
    assessment_modules: list[str]
    feasibility_status: Literal["not_evaluated"] = "not_evaluated"
    next_step: Literal["safety_screening"] = "safety_screening"

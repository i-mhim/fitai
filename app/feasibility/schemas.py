"""Read-only decision support contracts. A result is not exercise clearance."""
from typing import Literal
from pydantic import BaseModel, Field
from app.goals.schemas import GoalPreviewRequest

FeasibilityStatus = Literal[
    "needs_assessment", "needs_reassessment", "needs_professional_review",
    "needs_baseline", "conditional", "target_reportedly_met",
]
TimelineStatus = Literal[
    "not_evaluated", "unverified", "unsupported_automatic_deadline", "target_reportedly_met",
]
NextStep = Literal[
    "complete_assessment", "start_new_assessment", "seek_professional_guidance",
    "review_milestones", "verify_target",
]


class BaselineEvidence(BaseModel):
    metric: str
    value: int | str
    source: Literal["self_report"] = "self_report"


class FeasibilityResponse(BaseModel):
    assessment_id: str
    goal: GoalPreviewRequest
    status: FeasibilityStatus
    timeline_status: TimelineStatus
    policy_version: str
    question_bank_version: str
    evidence_quality: Literal["self_report_only"] = "self_report_only"
    baseline: list[BaselineEvidence] = Field(default_factory=list)
    target_gap_repetitions: int | None = None
    reason_codes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    milestone_keys: list[str] = Field(default_factory=list)
    next_step: NextStep
    message: str
    disclaimer: str = (
        "Preliminary decision support from self-reported information. Not medical clearance, "
        "a training prescription, or a prediction/guarantee of goal completion."
    )

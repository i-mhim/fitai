"""HTTP contracts for assessment sessions and answer events."""

from typing import Literal

from pydantic import BaseModel, Field, StrictInt, StrictStr

from app.goals.schemas import GoalPreviewRequest

AssessmentStatus = Literal["in_progress", "completed", "needs_professional_review"]


class OptionView(BaseModel):
    id: str
    label: str


class QuestionView(BaseModel):
    id: str
    version: int
    module: str
    prompt: str
    kind: Literal["single_choice", "integer_or_unknown"]
    options: list[OptionView]
    minimum: int | None
    maximum: int | None
    hint: str | None


class AnswerSubmission(BaseModel):
    question_id: str = Field(min_length=1)
    value: StrictInt | StrictStr


class AssessmentStateView(BaseModel):
    assessment_id: str
    question_bank_version: str
    goal: GoalPreviewRequest
    status: AssessmentStatus
    answered_count: int
    next_question: QuestionView | None
    safety_flags: list[str]
    message: str


class RecordedAnswerView(BaseModel):
    question_id: str
    question_version: int
    module: str
    value: int | str


class AssessmentSummaryView(BaseModel):
    assessment_id: str
    question_bank_version: str
    goal: GoalPreviewRequest
    status: AssessmentStatus
    answers: list[RecordedAnswerView]
    modules_covered: list[str]
    safety_flags: list[str]
    next_step: Literal[
        "continue_assessment", "professional_guidance", "baseline_review"
    ]
    note: str

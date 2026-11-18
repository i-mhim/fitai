"""Single-process in-memory sessions; replace with persistence + auth next.

The lock protects read-modify-write interactions, not against process restarts.
"""

from threading import RLock
from uuid import uuid4

from app.goals.schemas import GoalPreviewRequest
from app.assessments.engine import AssessmentSession


class InMemoryAssessmentStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AssessmentSession] = {}
        self.lock = RLock()

    def create(self, goal: GoalPreviewRequest) -> AssessmentSession:
        session = AssessmentSession(id=str(uuid4()), goal=goal)
        with self.lock:
            self._sessions[session.id] = session
        return session

    def get(self, assessment_id: str) -> AssessmentSession | None:
        return self._sessions.get(assessment_id)

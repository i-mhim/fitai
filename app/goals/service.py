from app.goals.schemas import GoalPreviewRequest, GoalPreviewResponse

# Curated initial modules. Future decision-tree logic will choose individual
# questions based on answers, safety screening, and existing evidence.
GOAL_CONFIG = {
    "handstand_hold": {
        "unit": "seconds",
        "modules": [
            "safety",
            "training_history",
            "wrist_tolerance",
            "overhead_control",
            "core_control",
            "inversion_experience",
        ],
    },
    "pushup_repetitions": {
        "unit": "repetitions",
        "modules": [
            "safety",
            "training_history",
            "upper_body_pushing",
            "pushup_technique",
        ],
    },
}


def preview_goal(goal: GoalPreviewRequest) -> GoalPreviewResponse:
    config = GOAL_CONFIG[goal.goal_type]
    return GoalPreviewResponse(
        goal=goal,
        target_unit=config["unit"],
        assessment_modules=config["modules"],
    )

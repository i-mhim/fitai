"""Deterministic, conservative goal-feasibility triage.

The initial questionnaire does not establish a physiological progress rate.
Therefore it never predicts when a user will master a handstand or add push-ups.
"""
from app.assessments.engine import AssessmentSession, question_order
from app.assessments.questions import QUESTION_BANK_VERSION
from app.feasibility.schemas import BaselineEvidence, FeasibilityResponse

POLICY_VERSION = "2026-11-feasibility-v1"


def evaluate_feasibility(session: AssessmentSession) -> FeasibilityResponse:
    """Assess completeness, safety, target evidence and deadline *supportability*.

    No mutations, no LLM and no exercise prescription. Any goal not already
    demonstrated remains conditional, irrespective of requested weeks.
    """
    answers = session.answers
    evidence: list[BaselineEvidence] = []
    for key in ("training_history", "hs_inversion_experience", "hs_wall_hold_seconds",
                "hs_pushup_capacity", "hs_core_control", "pu_baseline_reps", "pu_incline_reps", "pu_technique"):
        if key in answers:
            evidence.append(BaselineEvidence(metric=key, value=answers[key]))

    def result(status, timeline_status, next_step, message, *, reason_codes=(),
               missing_information=(), milestone_keys=(), gap=None):
        return FeasibilityResponse(
            assessment_id=session.id, goal=session.goal, status=status,
            timeline_status=timeline_status, policy_version=POLICY_VERSION,
            question_bank_version=session.question_bank_version,
            baseline=evidence, target_gap_repetitions=gap,
            reason_codes=list(reason_codes), missing_information=list(missing_information),
            milestone_keys=list(milestone_keys), next_step=next_step, message=message,
        )

    # Never bypass a recorded safety pause, even if data has become inconsistent.
    if session.safety_flags or session.status == "needs_professional_review":
        return result("needs_professional_review", "not_evaluated", "seek_professional_guidance",
                      "Automatic goal evaluation is paused based on screening responses. Seek appropriate professional guidance.",
                      reason_codes=["safety_review_required"])

    if session.question_bank_version != QUESTION_BANK_VERSION:
        return result("needs_reassessment", "not_evaluated", "start_new_assessment",
                      "The question bank changed. Complete a new assessment before evaluating this goal.",
                      reason_codes=["stale_question_bank"])

    if session.status != "completed":
        return result("needs_assessment", "not_evaluated", "complete_assessment",
                      "Finish the adaptive assessment before evaluating the requested deadline.",
                      reason_codes=["assessment_incomplete"])

    unanswered = [question_id for question_id in question_order(session) if question_id not in answers]
    if unanswered:
        return result("needs_reassessment", "not_evaluated", "start_new_assessment",
                      "This assessment is missing required answers. Start a new assessment.",
                      reason_codes=["required_answers_missing"], missing_information=unanswered)

    # This is a *product* rule: <=2 weeks is not a deadline we automatically
    # promise for a goal which has not already been verified. It does NOT say
    # that improvement within two weeks is biologically impossible.
    short_deadline = session.goal.requested_weeks <= 2

    if session.goal.goal_type == "pushup_repetitions":
        baseline = answers.get("pu_baseline_reps")
        if type(baseline) is not int:
            return result("needs_baseline", "not_evaluated", "start_new_assessment",
                          "A known current push-up repetition baseline is needed to compare the target. Reassess when available.",
                          reason_codes=["pushup_baseline_unknown"], missing_information=["pu_baseline_reps"])

        gap = max(0, session.goal.target_value - baseline)
        technique = answers.get("pu_technique")
        if baseline >= session.goal.target_value and technique == "controlled":
            return result("target_reportedly_met", "target_reportedly_met", "verify_target",
                          "Your reported controlled push-up count meets the target. Verify form and repetitions before marking the goal achieved.",
                          reason_codes=["reported_repetitions_meet_target", "verification_required"],
                          milestone_keys=["verify_controlled_pushup_target"], gap=gap)

        reasons = ["progress_rate_not_established"]
        milestones = ["review_pushup_form", "reassess_controlled_pushup_baseline"]
        missing = []
        if baseline == 0:
            milestones.insert(0, "foundation_pushup_progression_review")
            if answers.get("pu_incline_reps") == "unknown":
                missing.append("pu_incline_reps")
        elif technique in {"inconsistent", "unsure"}:
            reasons.append("technique_not_verified")
            milestones.insert(0, "technique_quality_review")
        if short_deadline:
            reasons.append("short_deadline_not_supportable")
        return result("conditional", "unsupported_automatic_deadline" if short_deadline else "unverified",
                      "review_milestones", "Use milestone reviews; the available answers cannot establish a safe rate of improvement or guarantee the deadline.",
                      reason_codes=reasons, missing_information=missing,
                      milestone_keys=milestones, gap=gap)

    # Wall-supported holds are not evidence of a freestanding hold.
    inversion = answers.get("hs_inversion_experience")
    wall_hold = answers.get("hs_wall_hold_seconds")
    if inversion != "never" and wall_hold == "unknown":
        return result("needs_baseline", "not_evaluated", "start_new_assessment",
                      "The previous supported-hold baseline is unknown. Reassess when you have a reliable report.",
                      reason_codes=["supported_hold_baseline_unknown"],
                      missing_information=["hs_wall_hold_seconds"])

    milestone_keys = ["review_overhead_and_wrist_readiness"]
    reasons = ["freestanding_duration_not_measured", "skill_completion_date_unpredictable"]
    missing = ["verified_freestanding_hold_seconds"]
    if inversion == "never":
        milestone_keys += ["review_foundational_control", "review_supported_inversion_readiness"]
        if answers.get("hs_core_control") == "unsure" or answers.get("hs_pushup_capacity") == "unknown":
            reasons.append("foundational_baseline_uncertain")
    elif inversion == "wall_supported":
        milestone_keys += ["review_supported_hold_quality", "review_balance_skill_readiness"]
    else:
        milestone_keys += ["review_balance_control", "verify_freestanding_duration"]

    if short_deadline:
        reasons.append("short_deadline_not_supportable")
    return result("conditional", "unsupported_automatic_deadline" if short_deadline else "unverified",
                  "review_milestones", "The requested timeframe cannot be predicted from this self-reported skill assessment. Use milestones instead of a guaranteed completion date.",
                  reason_codes=reasons, missing_information=missing,
                  milestone_keys=milestone_keys)

"""Pure feasibility policy: no DB or network required."""
from app.assessments.engine import AssessmentSession, record_answer
from app.feasibility.service import evaluate_feasibility
from app.goals.schemas import GoalPreviewRequest


def session(goal="handstand_hold", target=10, weeks=8):
    return AssessmentSession(id="test-id", goal=GoalPreviewRequest(
        goal_type=goal, target_value=target, requested_weeks=weeks))


def feed(s, values):
    for question, answer in values:
        record_answer(s, question, answer)
    return s


def test_incomplete_cannot_evaluate():
    r = evaluate_feasibility(session())
    assert r.status == "needs_assessment"
    assert r.timeline_status == "not_evaluated"
    assert not r.milestone_keys


def test_safety_pause_blocks():
    s = feed(session(), [("safety_red_flags", "yes")])
    assert evaluate_feasibility(s).status == "needs_professional_review"


def test_handstand_beginner_8_weeks_conditional():
    s = feed(session(), [
        ("safety_red_flags", "no"), ("training_history", "none"),
        ("hs_wrist_pain", "no"), ("hs_overhead_control", "comfortable"),
        ("hs_inversion_experience", "never"), ("hs_pushup_capacity", 2),
        ("hs_core_control", "no")
    ])
    assert s.status == "completed"
    r = evaluate_feasibility(s)
    assert r.status == "conditional"
    assert r.timeline_status == "unverified"
    assert "freestanding_duration_not_measured" in r.reason_codes
    assert "verified_freestanding_hold_seconds" in r.missing_information


def test_handstand_one_week_does_not_promise():
    s = feed(session(weeks=1), [
        ("safety_red_flags", "no"), ("training_history", "regular_strength"),
        ("hs_wrist_pain", "no"), ("hs_overhead_control", "comfortable"),
        ("hs_inversion_experience", "never"), ("hs_core_control", "yes")
    ])
    assert evaluate_feasibility(s).timeline_status == "unsupported_automatic_deadline"


def test_supported_not_same_as_freestanding():
    s = feed(session(), [
        ("safety_red_flags", "no"), ("training_history", "regular_calisthenics"),
        ("hs_wrist_pain", "no"), ("hs_overhead_control", "comfortable"),
        ("hs_inversion_experience", "consistent_freestanding"), ("hs_wall_hold_seconds", 180),
    ])
    r = evaluate_feasibility(s)
    assert r.status == "conditional"
    assert r.target_gap_repetitions is None
    assert r.timeline_status == "unverified"


def test_unknown_wall_hold_requests_baseline():
    s = feed(session(), [
        ("safety_red_flags", "no"), ("training_history", "regular_calisthenics"),
        ("hs_wrist_pain", "no"), ("hs_overhead_control", "comfortable"),
        ("hs_inversion_experience", "wall_supported"), ("hs_wall_hold_seconds", "unknown"),
    ])
    assert evaluate_feasibility(s).status == "needs_baseline"


def test_pushup_gap_and_technique_review():
    s = feed(session(goal="pushup_repetitions", target=25), [
        ("safety_red_flags", "no"), ("training_history", "occasional"),
        ("pu_upper_body_pain", "no"), ("pu_baseline_reps", 12),
        ("pu_technique", "inconsistent")
    ])
    r = evaluate_feasibility(s)
    assert r.status == "conditional"
    assert r.target_gap_repetitions == 13
    assert "technique_quality_review" in r.milestone_keys


def test_unknown_pushup_baseline_no_fabricated_gap():
    s = feed(session(goal="pushup_repetitions", target=25), [
        ("safety_red_flags", "no"), ("training_history", "none"),
        ("pu_upper_body_pain", "no"), ("pu_baseline_reps", "unknown"),
    ])
    r = evaluate_feasibility(s)
    assert r.status == "needs_baseline"
    assert r.target_gap_repetitions is None


def test_reported_pushup_target_needs_verification():
    s = feed(session(goal="pushup_repetitions", target=25), [
        ("safety_red_flags", "no"), ("training_history", "regular_strength"),
        ("pu_upper_body_pain", "no"), ("pu_baseline_reps", 30),
        ("pu_technique", "controlled")
    ])
    r = evaluate_feasibility(s)
    assert r.status == "target_reportedly_met"
    assert r.next_step == "verify_target"
    assert r.target_gap_repetitions == 0


def test_inconsistent_form_not_marked_met():
    s = feed(session(goal="pushup_repetitions", target=25), [
        ("safety_red_flags", "no"), ("training_history", "regular_strength"),
        ("pu_upper_body_pain", "no"), ("pu_baseline_reps", 30),
        ("pu_technique", "inconsistent")
    ])
    assert evaluate_feasibility(s).status == "conditional"


def test_changed_question_bank_forces_reassessment():
    s = session()
    s.question_bank_version = "old-version"
    assert evaluate_feasibility(s).status == "needs_reassessment"


def test_completed_but_missing_required_answers_rejected():
    s = session()
    s.status = "completed"
    assert evaluate_feasibility(s).status == "needs_reassessment"

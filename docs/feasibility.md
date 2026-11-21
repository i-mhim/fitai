# Phase 4: Goal feasibility (prototype)

## How to use

After registering/logging in and completing an assessment:

`GET /v1/assessments/{assessment_id}/feasibility`

Use the same bearer token that owns the assessment. Assessments owned by other users return 404; an unauthenticated request returns 401. The endpoint is **read-only** and computes the evaluation from persisted answers.

## Decision output

- `needs_assessment`: answers are still in progress.
- `needs_reassessment`: old question bank or inconsistent completed record; start a new assessment.
- `needs_professional_review`: a recorded safety flag pauses evaluation.
- `needs_baseline`: an essential reported ability measurement is unknown.
- `conditional`: milestone-based preparation may be considered, **without** a predicted completion date.
- `target_reportedly_met`: the user reports controlled push-up repetitions at or above the target; it needs verification.

The separate `timeline_status` is one of `not_evaluated`, `unverified`, `unsupported_automatic_deadline`, or `target_reportedly_met`. For goals not already reported as achieved, requests of **2 weeks or less** are marked `unsupported_automatic_deadline`: a *product limitation*, not a claim that improvement is physiologically impossible.

`baseline` lists self-reported evidence only; `reason_codes` and `milestone_keys` are stable machine-readable identifiers suitable for a future frontend and planning engine. These are *review milestones*, not exercise prescriptions.

## Design limitations

- **No timing prediction:** no validated rate-of-improvement model exists yet.
- **Freestanding handstand:** the current assessment measures prior inversion experience and wall-supported holds, **not** verified freestanding-hold duration. Do not treat a wall hold as a freestanding hold.
- **Self-reported data:** even an apparent push-up goal completion must be verified before awarding completion.
- **Unknown baselines:** request a new assessment rather than inventing an ability estimate. Do not pressure people into high-risk testing.
- **No prescription:** this endpoint never returns repetitions, sets, session frequency, exercise clearance or a plan.
- **Authentication:** assessments can only be accessed by their owners. Keep all health-related data private.

## Next work

The training planner will consume reviewed milestone candidates, equipment, available time, exercise prerequisites, and additional safety policies. It must **not** equate `conditional` with clearance for unrestricted workouts.

# Example End-to-End Flow (FastAPI + Postgres + JSONB)

This flow matches the schemas and tables defined in this spec.

## 1) Create weekly plan

1. `POST /weekly-plans` with `week_start_date`, `timezone`, `strategy`.
2. Service generates `weekly_plans` row and 7 `weekly_plan_days` rows.
3. Response returns `WeeklyPlan` JSON for client scheduling UI.

## 2) Generate today's session

1. Client requests `GET /session-plans/today`.
2. Service selects today’s `weekly_plan_days.label`.
3. `generate_session_plan(...)` builds a `SessionPlan` from templates and user stats.
4. Store as `session_plans` with `plan_json` (JSONB).
5. Response returns `SessionPlan` JSON to render the workout.

## 3) Log session

1. Client submits `POST /session-logs` with sets, reps, loads, optional RPE, and readiness.
2. Service writes `session_logs` row + `session_log_sets` rows.

## 4) Update stats

1. For each exercise in `session_log_sets`, run `progress_exercise(...)` from `spec/progression.md`.
2. Update `user_exercise_stats.next_load`, `stagnation_count`, and `phase`.
3. If `phase_override == "DELOAD"`, mark the next session accordingly.

## 5) Next session adjusts

1. Next time `generate_session_plan(...)` runs, it uses updated `user_exercise_stats`.
2. Suggested loads reflect progression, deloads, or readiness adjustment.

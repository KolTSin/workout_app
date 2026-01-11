# Buildable Spec: Training Plan System

This spec includes the canonical JSON schemas, progression/calibration logic, database schema, and beginner-safe templates.
The implementation target is FastAPI + Postgres + JSONB to match the schemas cleanly.

## Schemas

- Weekly plan: `spec/schemas/WeeklyPlan.schema.json`
- Session plan: `spec/schemas/SessionPlan.schema.json`

### Weekly plan example instance

```json
{
  "id": "7c3e1c9b-3c2a-4df6-8d9f-1e0edc59ef1d",
  "user_id": "f2a84d3c-5f0d-4e57-a1d1-6a1d3b2f3f44",
  "week_start_date": "2026-01-12",
  "timezone": "Europe/Copenhagen",
  "strategy": "ULF_2C",
  "days": [
    { "date": "2026-01-12", "label": "UPPER", "session_plan_id": null, "notes": null },
    { "date": "2026-01-13", "label": "CARDIO", "session_plan_id": null, "notes": "Zone 2" },
    { "date": "2026-01-14", "label": "LOWER", "session_plan_id": null, "notes": null },
    { "date": "2026-01-15", "label": "REST", "session_plan_id": null, "notes": null },
    { "date": "2026-01-16", "label": "FULL", "session_plan_id": null, "notes": null },
    { "date": "2026-01-17", "label": "CARDIO", "session_plan_id": null, "notes": "Intervals" },
    { "date": "2026-01-18", "label": "REST", "session_plan_id": null, "notes": null }
  ],
  "created_at": "2026-01-11T12:50:00Z"
}
```

## Progression + calibration

See `spec/progression.md` for the exact algorithms and guardrails.

## Database schema

Postgres-ready schema lives in `spec/db/schema.sql`.

## Beginner templates

See `spec/templates/beginner_templates.md` for Upper, Lower, Full, and Cardio templates.

## Exercise library seed JSON

See `spec/exercises_seed.json` for IDs, patterns, equipment, and default progression values.

## Session plan generator

See `spec/session_plan_generator.md` for template selection, substitutions, and load assignment logic.

## Weekly plan generator rules

See `spec/weekly_plan_generator.md` for the initial scheduling rule set.

## End-to-end flow

See `spec/end_to_end_flow.md` for the full weekly plan → session → log → progression flow.
## Weekly plan generator rules

See `spec/weekly_plan_generator.md` for the initial scheduling rule set.

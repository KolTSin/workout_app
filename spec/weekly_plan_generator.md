# Weekly Plan Generator (simple rules)

**Inputs:**

- `training_days_per_week` (e.g. 5)
- `strategy` (e.g. ULF_2C)
- `preferred_days` (optional)
- `recent_history` (to avoid repeating missed sessions badly)

**Rule set for ULF_2C (5 days):**

- Place strength first: Upper, Lower, Full with at least 1 day between Lower and Full if possible.
- Insert cardio on remaining training days.
- Ensure at least 1 REST day.

**If user misses a planned day:**

- “Roll forward”: the next gym visit does the next planned workout type (don’t cram).

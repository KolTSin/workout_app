# Progression + Calibration Functions

## Required session inputs (minimum)

For each performed set:

- `reps_done`
- `load_used` (kg/lb/machine level, or null for bodyweight)
- Optional: `rpe` (1–10). If you want easier UX, collect `easy/ok/hard` and map to RPE.

## Stored per exercise (minimum)

`UserExerciseStats`:

- `next_load`
- `rep_range_min`, `rep_range_max`
- `target_rpe`
- `last_n_sessions` summary
- `stagnation_count`

## Calibration (safe beginner version)

**Goal:** derive a starting `next_load` without maxing out.

**Protocol:** During calibration sessions, prescribe 2–3 sets of 8 reps @ RPE 6–7.

**Computation:**

```text
function estimate_e1rm_epley(load, reps):
    return load * (1 + reps/30)

function starting_load_from_calibration(best_set_load, best_set_reps, rep_range_max):
    e1rm = estimate_e1rm_epley(best_set_load, best_set_reps)
    training_max = 0.90 * e1rm  # conservative for beginners
    # choose a % that usually lands in the target rep range
    # for 6–10 reps: ~70% of training max is a decent start
    start = 0.70 * training_max
    return start
```

**Output:**

- `next_load = round_to_step(start, exercise.rounding_step)`

## Progression (double progression + RPE guardrails)

We assume each exercise has:

- `rep_range = [min,max]` (e.g., 6–10)
- `target_rpe` (e.g., 7.5)
- `step_up_pct` (upper ~2.5%, lower ~5% default)
- `rounding_step` (2.5kg for barbells, 2kg DB increments, etc.)

**Key rule:** progress only when reps are high *and* effort is controlled.

**Inputs:**

```text
exercise_stats:
  next_load (the load you suggested for this session)
  rep_min, rep_max
  target_rpe
  step_up_pct
  rounding_step
  stagnation_count

session_performance:
  performed_sets: list of { reps_done, load_used, rpe? }
  used_same_load_for_all_sets (bool)
```

**Outputs:**

- `new_next_load`
- `stagnation_count` updated
- Optional `phase_override` (e.g., DELOAD trigger)

**Pseudocode:**

```text
function progress_exercise(exercise_stats, performed_sets):
    load = median(load_used across sets)  # robust
    reps = [s.reps_done for s in performed_sets]
    rpes = [s.rpe for s in performed_sets if s.rpe is not null]

    achieved_all_at_or_above_min = all(r >= rep_min for r in reps)
    achieved_all_at_max = all(r >= rep_max for r in reps)

    avg_rpe = mean(rpes) if len(rpes) > 0 else null

    # Guardrails for "too hard"
    if not achieved_all_at_or_above_min:
        new_load = load * 0.90   # -10%
        stagnation = 0
        return round_to_step(new_load), stagnation, null

    if avg_rpe is not null and avg_rpe >= (target_rpe + 1.0):
        # You made it but it was grindy; keep load and try to add reps next time
        stagnation = exercise_stats.stagnation_count + 1
        return round_to_step(load), stagnation, maybe_deload(stagnation)

    # Progress condition: top end reps AND not too hard
    if achieved_all_at_max and (avg_rpe is null or avg_rpe <= target_rpe + 0.5):
        new_load = load * (1 + step_up_pct)
        stagnation = 0
        return round_to_step(new_load), stagnation, null

    # Otherwise: hold load (progress by reps next time)
    stagnation = exercise_stats.stagnation_count + 1
    return round_to_step(load), stagnation, maybe_deload(stagnation)
```

**Deload trigger (simple):**

```text
function maybe_deload(stagnation_count):
    if stagnation_count >= 6:
        return "DELOAD"
    return null
```

**Deload behavior:**

- Reduce `next_load` by ~10%.
- Reduce total sets for that movement by 1 for a week.

## Readiness adjustment (optional)

**Inputs:**

- `soreness` (0–10)
- `sleep` (0–10)
- `stress` (0–10)

**Rule:**

```text
readiness_score = 0.5*sleep + 0.25*(10-soreness) + 0.25*(10-stress)

if readiness_score < 4.5: adjustment = LIGHTEN_LOAD_5
elif readiness_score < 5.5: adjustment = REDUCE_ONE_SET
else adjustment = NONE
```

**Apply:**

- `LIGHTEN_LOAD_5`: reduce all compound loads by 5%.
- `REDUCE_ONE_SET`: for compounds, -1 set.

# Session Plan Generator (template + substitutions + loads)

This function chooses the right template, resolves substitutions, and applies progression/calibration to set suggested loads.

## Inputs

- `user_id`
- `session_type` (UPPER/LOWER/FULL/CARDIO/MOBILITY)
- `date`, `timezone`
- `user_profile` (equipment availability, preferred units)
- `exercise_library` (from `exercises`)
- `substitutions` (from `exercise_substitutions`)
- `user_exercise_stats` (from `user_exercise_stats`)
- `templates` (from `spec/templates/beginner_templates.md`)
- `phase_override` (optional, e.g. DELOAD)
- `readiness_adjustment` (optional)

## Outputs

- `SessionPlan` JSON (matches `spec/schemas/SessionPlan.schema.json`)

## Pseudocode

```text
function generate_session_plan(input):
    template = pick_template(session_type, user_profile, templates)
    items = []

    for exercise_slot in template.exercises:
        exercise = resolve_exercise(exercise_slot, user_profile, exercise_library, substitutions)
        stats = user_exercise_stats.get(user_id, exercise.id)

        if stats is null:
            stats = seed_stats_from_exercise(user_id, exercise)

        phase = phase_override or stats.phase

        if phase == "CALIBRATION":
            sets = calibration_sets(exercise, stats)
            next_load = null
        else:
            sets, next_load = load_prescription(exercise, stats)

        items.append(build_item(exercise, sets, next_load, stats, user_profile))

    items = apply_readiness(items, readiness_adjustment)

    return build_session_plan(user_id, date, timezone, session_type, phase, template.warmup, items)
```

### pick_template

```text
function pick_template(session_type, user_profile, templates):
    if session_type == "CARDIO":
        return templates.cardio
    if session_type == "UPPER":
        return templates.upper
    if session_type == "LOWER":
        return templates.lower
    if session_type == "FULL":
        return templates.full
    return templates.mobility
```

### resolve_exercise

```text
function resolve_exercise(slot, user_profile, exercise_library, substitutions):
    if slot.preferred_exercise_id in user_profile.available_exercises:
        return exercise_library[slot.preferred_exercise_id]

    for sub in substitutions[slot.preferred_exercise_id] ordered by priority:
        if sub in user_profile.available_exercises:
            return exercise_library[sub]

    return exercise_library[slot.preferred_exercise_id]
```

### seed_stats_from_exercise

```text
function seed_stats_from_exercise(user_id, exercise):
    return {
        user_id: user_id,
        exercise_id: exercise.id,
        phase: "CALIBRATION",
        next_load: null,
        rep_min: exercise.default_rep_min,
        rep_max: exercise.default_rep_max,
        target_rpe: exercise.default_target_rpe,
        stagnation_count: 0
    }
```

### calibration_sets

```text
function calibration_sets(exercise, stats):
    return build_sets(
        count=2,
        reps_min=stats.rep_min,
        reps_max=stats.rep_max,
        target_rpe=6.5,
        rest_seconds=120
    )
```

### load_prescription

```text
function load_prescription(exercise, stats):
    load = stats.next_load

    if load is null:
        load = estimate_starting_load(exercise, stats)

    sets = build_sets(
        count=3,
        reps_min=stats.rep_min,
        reps_max=stats.rep_max,
        target_rpe=stats.target_rpe,
        rest_seconds=default_rest(exercise)
    )

    return sets, load
```

### build_item

```text
function build_item(exercise, sets, next_load, stats, user_profile):
    return {
        order: next_order(),
        exercise_id: exercise.id,
        name: exercise.name,
        category: categorize(exercise),
        equipment: exercise.equipment,
        substitutions: substitution_names(exercise.id),
        prescription: {
            sets: attach_load(sets, next_load, exercise, user_profile)
        }
    }
```

### apply_readiness

```text
function apply_readiness(items, readiness_adjustment):
    if readiness_adjustment == "LIGHTEN_LOAD_5":
        return lighten_compounds(items, pct=0.05)
    if readiness_adjustment == "REDUCE_ONE_SET":
        return reduce_compound_sets(items, count=1)
    return items
```

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from app import db
from app.schemas import (
    SessionLogCreate,
    SessionPlanRequest,
    SessionPlanResponse,
    WeeklyPlanCreate,
    WeeklyPlanDay,
    WeeklyPlanResponse,
)
from app.templates import get_templates

app = FastAPI(title="Workout MVP API")


def _round_to_step(value: float | None, step: float | None) -> float | None:
    if value is None:
        return None
    if not step or step <= 0:
        return round(value, 2)
    return round(round(value / step) * step, 2)


def _week_start(input_date: date) -> date:
    return input_date - timedelta(days=input_date.weekday())


def _generate_week_labels(strategy: str) -> list[str]:
    if strategy == "FULL_3":
        return ["FULL", "REST", "FULL", "REST", "FULL", "REST", "REST"]
    if strategy == "UL_4":
        return ["UPPER", "LOWER", "REST", "UPPER", "LOWER", "REST", "REST"]
    if strategy == "CUSTOM":
        return ["REST"] * 7
    return ["UPPER", "CARDIO", "LOWER", "REST", "FULL", "CARDIO", "REST"]


def _seed_stats_from_exercise(user_id: str, exercise: dict) -> dict:
    return {
        "user_id": user_id,
        "exercise_id": exercise["id"],
        "phase": "CALIBRATION",
        "next_load": None,
        "rep_min": exercise["default_rep_min"],
        "rep_max": exercise["default_rep_max"],
        "target_rpe": exercise["default_target_rpe"],
        "stagnation_count": 0,
    }


def _estimate_e1rm_epley(load: float, reps: int) -> float:
    return load * (1 + reps / 30)


def _starting_load_from_calibration(best_load: float, best_reps: int) -> float:
    e1rm = _estimate_e1rm_epley(best_load, best_reps)
    training_max = 0.90 * e1rm
    return 0.70 * training_max


def _maybe_deload(stagnation_count: int) -> str | None:
    if stagnation_count >= 6:
        return "DELOAD"
    return None


def _progress_exercise(stats: dict, sets: list[dict], step_up_pct: float, rounding_step: float) -> dict:
    loads = [s["load_used"] for s in sets if s.get("load_used") is not None]
    reps = [s["reps_done"] for s in sets]
    rpes = [s["rpe"] for s in sets if s.get("rpe") is not None]

    if loads:
        load = median(loads)
    else:
        load = stats.get("next_load") or 0.0

    achieved_all_at_or_above_min = all(r >= stats["rep_min"] for r in reps)
    achieved_all_at_max = all(r >= stats["rep_max"] for r in reps)

    avg_rpe = mean(rpes) if rpes else None

    if not achieved_all_at_or_above_min:
        new_load = load * 0.90
        return {
            **stats,
            "next_load": _round_to_step(new_load, rounding_step),
            "stagnation_count": 0,
            "phase": "TRAINING",
        }

    if avg_rpe is not None and avg_rpe >= (stats["target_rpe"] + 1.0):
        stagnation = stats["stagnation_count"] + 1
        phase_override = _maybe_deload(stagnation)
        return {
            **stats,
            "next_load": _round_to_step(load, rounding_step),
            "stagnation_count": stagnation,
            "phase": phase_override or "TRAINING",
        }

    if achieved_all_at_max and (avg_rpe is None or avg_rpe <= stats["target_rpe"] + 0.5):
        new_load = load * (1 + step_up_pct)
        return {
            **stats,
            "next_load": _round_to_step(new_load, rounding_step),
            "stagnation_count": 0,
            "phase": "TRAINING",
        }

    stagnation = stats["stagnation_count"] + 1
    phase_override = _maybe_deload(stagnation)
    return {
        **stats,
        "next_load": _round_to_step(load, rounding_step),
        "stagnation_count": stagnation,
        "phase": phase_override or "TRAINING",
    }


def _build_sets(slot: dict, stats: dict, phase: str, load_suggestion: dict | None) -> list[dict]:
    sets = []
    set_count = slot["sets"]
    if phase == "CALIBRATION":
        set_count = min(2, slot["sets"])
    for idx in range(1, set_count + 1):
        set_row = {
            "set_number": idx,
            "target_reps_min": stats["rep_min"],
            "target_reps_max": stats["rep_max"],
            "target_rpe": stats["target_rpe"],
            "rest_seconds": slot["rest_seconds"],
            "load_suggestion": load_suggestion,
            "tempo": None,
            "notes": None,
        }
        if phase == "CALIBRATION":
            set_row["notes"] = "Pick a load you can do at ~RPE 6–7"
        sets.append(set_row)
    return sets


def _resolve_exercise(slot: dict, exercises: dict) -> dict:
    preferred = slot["preferred_exercise_id"]
    if preferred in exercises:
        return exercises[preferred]
    for sub in slot.get("substitutions", []):
        if sub in exercises:
            return exercises[sub]
    raise KeyError(f"Exercise {preferred} not found in library")


def _session_phase(stats_map: dict) -> str:
    phases = {stats["phase"] for stats in stats_map.values()}
    if "DELOAD" in phases:
        return "DELOAD"
    if "CALIBRATION" in phases:
        return "CALIBRATION"
    return "TRAINING"


def _build_session_plan(user_id: str, input_date: date, session_type: str) -> dict:
    templates = get_templates()
    exercises = db.fetch_exercises()
    stats_map = db.fetch_user_exercise_stats(user_id)

    template = templates[session_type.lower()]
    items = []
    for order, slot in enumerate(template["exercises"], start=1):
        if session_type == "CARDIO":
            exercise = {
                "id": "cardio_generic",
                "name": "Cardio Session",
                "pattern": "CARDIO",
                "equipment": "CARDIO",
                "default_rep_min": 1,
                "default_rep_max": 1,
                "default_target_rpe": 6.0,
                "step_up_pct": 0.0,
                "rounding_step": 0.0,
            }
        else:
            exercise = _resolve_exercise(slot, exercises)

        stats = stats_map.get(exercise["id"])
        if not stats:
            stats = _seed_stats_from_exercise(user_id, exercise)
            if session_type != "CARDIO":
                db.upsert_user_exercise_stats(user_id, stats)
            stats_map[exercise["id"]] = stats

        phase = stats["phase"]
        load_suggestion = None
        if phase != "CALIBRATION":
            next_load = stats.get("next_load")
            if next_load is not None:
                load_suggestion = {
                    "kind": "KG",
                    "value": next_load,
                    "unit": "kg",
                    "rounding_step": exercise["rounding_step"],
                }
        sets = _build_sets(slot, stats, phase, load_suggestion)

        items.append(
            {
                "order": order,
                "exercise_id": exercise["id"],
                "name": exercise["name"],
                "category": slot["category"],
                "equipment": exercise.get("equipment"),
                "substitutions": slot.get("substitutions", []),
                "prescription": {"sets": sets},
            }
        )

    if session_type == "CARDIO":
        plan_phase = "TRAINING"
    else:
        plan_phase = _session_phase(
            {
                item["exercise_id"]: stats_map.get(
                    item["exercise_id"], {"phase": "CALIBRATION"}
                )
                for item in items
            }
        )
    return {
        "id": str(uuid4()),
        "user_id": user_id,
        "date": input_date.isoformat(),
        "timezone": "UTC",
        "session_type": session_type,
        "phase": plan_phase,
        "readiness_hint": {"enabled": False, "adjustment": "NONE"},
        "warmup": template["warmup"],
        "items": items,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def _update_stats_from_log(user_id: str, exercise_id: str, sets: list[dict]) -> None:
    exercises = db.fetch_exercises()
    exercise = exercises.get(exercise_id)
    if not exercise:
        return

    stats_map = db.fetch_user_exercise_stats(user_id)
    stats = stats_map.get(exercise_id) or _seed_stats_from_exercise(user_id, exercise)

    if stats["phase"] == "DELOAD":
        if stats["next_load"] is not None:
            stats["next_load"] = _round_to_step(stats["next_load"] * 0.9, exercise["rounding_step"])
        stats["phase"] = "TRAINING"
        stats["stagnation_count"] = 0
        db.upsert_user_exercise_stats(user_id, stats)
        return

    if stats["phase"] == "CALIBRATION":
        best_set = None
        for set_row in sets:
            if set_row.get("load_used") is None:
                continue
            if best_set is None or set_row["load_used"] > best_set["load_used"]:
                best_set = set_row
        if best_set:
            start = _starting_load_from_calibration(best_set["load_used"], best_set["reps_done"])
            stats["next_load"] = _round_to_step(start, exercise["rounding_step"])
        stats["phase"] = "TRAINING"
        stats["stagnation_count"] = 0
        db.upsert_user_exercise_stats(user_id, stats)
        return

    updated = _progress_exercise(stats, sets, exercise["step_up_pct"], exercise["rounding_step"])
    if updated["phase"] == "DELOAD" and updated["next_load"] is not None:
        updated["next_load"] = _round_to_step(updated["next_load"] * 0.9, exercise["rounding_step"])
    db.upsert_user_exercise_stats(user_id, updated)


@app.on_event("startup")
def startup() -> None:
    db.init_db()
    db.seed_exercises()


@app.post("/weekly-plans", response_model=WeeklyPlanResponse)

def create_weekly_plan(payload: WeeklyPlanCreate) -> WeeklyPlanResponse:
    plan_id = str(uuid4())
    db.ensure_user(str(payload.user_id), payload.timezone)
    labels = _generate_week_labels(payload.strategy)
    days = []
    for offset, label in enumerate(labels):
        day_date = payload.week_start_date + timedelta(days=offset)
        days.append(
            {
                "date": day_date.isoformat(),
                "label": label,
                "session_plan_id": None,
                "notes": None,
            }
        )

    plan = {
        "id": plan_id,
        "user_id": str(payload.user_id),
        "week_start_date": payload.week_start_date.isoformat(),
        "timezone": payload.timezone,
        "strategy": payload.strategy,
    }

    db.insert_weekly_plan(plan, days)

    return WeeklyPlanResponse(
        id=plan_id,
        user_id=payload.user_id,
        week_start_date=payload.week_start_date,
        timezone=payload.timezone,
        strategy=payload.strategy,
        days=[WeeklyPlanDay(**day) for day in days],
        created_at=datetime.utcnow(),
    )


@app.post("/session-plans", response_model=SessionPlanResponse)

def generate_session_plan(payload: SessionPlanRequest) -> SessionPlanResponse:
    day_info = db.fetch_weekly_plan_day(str(payload.user_id), payload.date.isoformat())
    if not day_info:
        raise HTTPException(status_code=404, detail="No weekly plan for this date")
    session_type = day_info["label"]
    if session_type == "REST":
        raise HTTPException(status_code=400, detail="Rest day has no session plan")
    plan = db.fetch_session_plan(str(payload.user_id), payload.date.isoformat(), session_type)
    if plan:
        return SessionPlanResponse(**plan)

    plan = _build_session_plan(str(payload.user_id), payload.date, session_type)
    db.insert_session_plan(plan)
    return SessionPlanResponse(**plan)


@app.post("/session-logs")

def log_session(payload: SessionLogCreate) -> dict:
    log_id = str(uuid4())
    db.ensure_user(str(payload.user_id), "UTC")
    set_rows = []
    for entry in payload.sets:
        set_rows.append(
            {
                "id": str(uuid4()),
                "exercise_id": entry.exercise_id,
                "set_number": entry.set_number,
                "reps_done": entry.reps_done,
                "load_used": entry.load_used,
                "rpe": entry.rpe,
            }
        )

    db.insert_session_log(
        {
            "id": log_id,
            "user_id": str(payload.user_id),
            "session_plan_id": str(payload.session_plan_id) if payload.session_plan_id else None,
            "date": payload.date.isoformat(),
            "session_type": payload.session_type,
            "readiness": payload.readiness,
            "notes": payload.notes,
        },
        set_rows,
    )

    grouped_sets = defaultdict(list)
    for row in set_rows:
        grouped_sets[row["exercise_id"]].append(row)

    for exercise_id, exercise_sets in grouped_sets.items():
        _update_stats_from_log(str(payload.user_id), exercise_id, exercise_sets)

    return {"status": "ok", "session_log_id": log_id}

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg2
from psycopg2.extras import Json

BASE_DIR = Path(__file__).resolve().parent.parent
SPEC_DIR = BASE_DIR / "spec"


def _database_url() -> str:
    return (
        "dbname=workout_app user=workout_app password=workout_app "
        "host=localhost port=5432"
    )


@contextmanager
def get_conn() -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    schema_sql = (SPEC_DIR / "db" / "schema.sql").read_text()
    schema_sql = schema_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
    schema_sql = schema_sql.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)


def ensure_user(user_id: str, timezone: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, timezone) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET timezone = EXCLUDED.timezone",
                (user_id, timezone),
            )


def seed_exercises() -> int:
    seed_path = SPEC_DIR / "exercises_seed.json"
    exercises = json.loads(seed_path.read_text())
    insert_sql = (
        "INSERT INTO exercises ("
        "id, name, pattern, equipment, default_rep_min, default_rep_max, "
        "default_target_rpe, step_up_pct, rounding_step"
        ") VALUES ("
        "%(id)s, %(name)s, %(pattern)s, %(equipment)s, %(default_rep_min)s, "
        "%(default_rep_max)s, %(default_target_rpe)s, %(step_up_pct)s, "
        "%(rounding_step)s"
        ") ON CONFLICT (id) DO NOTHING"
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            for exercise in exercises:
                cur.execute(insert_sql, exercise)
    return len(exercises)


def fetch_exercises() -> dict[str, dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, pattern, equipment, default_rep_min, "
                "default_rep_max, default_target_rpe, step_up_pct, rounding_step "
                "FROM exercises"
            )
            rows = cur.fetchall()
    return {
        row[0]: {
            "id": row[0],
            "name": row[1],
            "pattern": row[2],
            "equipment": row[3],
            "default_rep_min": row[4],
            "default_rep_max": row[5],
            "default_target_rpe": float(row[6]),
            "step_up_pct": float(row[7]),
            "rounding_step": float(row[8]),
        }
        for row in rows
    }


def fetch_user_exercise_stats(user_id: str) -> dict[str, dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT exercise_id, phase, next_load, rep_min, rep_max, target_rpe, "
                "stagnation_count "
                "FROM user_exercise_stats WHERE user_id = %s",
                (user_id,),
            )
            rows = cur.fetchall()
    return {
        row[0]: {
            "exercise_id": row[0],
            "phase": row[1],
            "next_load": float(row[2]) if row[2] is not None else None,
            "rep_min": row[3],
            "rep_max": row[4],
            "target_rpe": float(row[5]),
            "stagnation_count": row[6],
        }
        for row in rows
    }


def upsert_user_exercise_stats(user_id: str, stats: dict) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_exercise_stats (user_id, exercise_id, phase, next_load, "
                "rep_min, rep_max, target_rpe, stagnation_count) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (user_id, exercise_id) DO UPDATE SET "
                "phase = EXCLUDED.phase, next_load = EXCLUDED.next_load, "
                "rep_min = EXCLUDED.rep_min, rep_max = EXCLUDED.rep_max, "
                "target_rpe = EXCLUDED.target_rpe, stagnation_count = EXCLUDED.stagnation_count, "
                "last_updated_at = now()",
                (
                    user_id,
                    stats["exercise_id"],
                    stats["phase"],
                    stats["next_load"],
                    stats["rep_min"],
                    stats["rep_max"],
                    stats["target_rpe"],
                    stats["stagnation_count"],
                ),
            )


def insert_session_plan(plan: dict) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO session_plans (id, user_id, date, timezone, session_type, phase, plan_json) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    plan["id"],
                    plan["user_id"],
                    plan["date"],
                    plan["timezone"],
                    plan["session_type"],
                    plan["phase"],
                    Json(plan),
                ),
            )
    return plan["id"]


def fetch_session_plan(user_id: str, date_str: str, session_type: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan_json FROM session_plans WHERE user_id = %s AND date = %s AND session_type = %s",
                (user_id, date_str, session_type),
            )
            row = cur.fetchone()
    return row[0] if row else None


def insert_weekly_plan(plan: dict, days: list[dict]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO weekly_plans (id, user_id, week_start_date, timezone, strategy) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id, week_start_date) DO NOTHING",
                (
                    plan["id"],
                    plan["user_id"],
                    plan["week_start_date"],
                    plan["timezone"],
                    plan["strategy"],
                ),
            )
            for day in days:
                cur.execute(
                    "INSERT INTO weekly_plan_days (weekly_plan_id, date, label, session_plan_id, notes) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (weekly_plan_id, date) DO NOTHING",
                    (
                        plan["id"],
                        day["date"],
                        day["label"],
                        day.get("session_plan_id"),
                        day.get("notes"),
                    ),
                )


def fetch_weekly_plan_day(user_id: str, date_str: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT weekly_plans.id, weekly_plans.timezone, weekly_plans.strategy, "
                "weekly_plan_days.label "
                "FROM weekly_plans "
                "JOIN weekly_plan_days ON weekly_plan_days.weekly_plan_id = weekly_plans.id "
                "WHERE weekly_plans.user_id = %s AND weekly_plan_days.date = %s",
                (user_id, date_str),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "weekly_plan_id": row[0],
        "timezone": row[1],
        "strategy": row[2],
        "label": row[3],
    }


def insert_session_log(log: dict, sets: list[dict]) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO session_logs (id, user_id, session_plan_id, date, session_type, readiness_json, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    log["id"],
                    log["user_id"],
                    log.get("session_plan_id"),
                    log["date"],
                    log["session_type"],
                    Json(log.get("readiness")) if log.get("readiness") else None,
                    log.get("notes"),
                ),
            )
            for row in sets:
                cur.execute(
                    "INSERT INTO session_log_sets (id, session_log_id, exercise_id, set_number, reps_done, load_used, rpe) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        row["id"],
                        log["id"],
                        row["exercise_id"],
                        row["set_number"],
                        row["reps_done"],
                        row.get("load_used"),
                        row.get("rpe"),
                    ),
                )
    return log["id"]

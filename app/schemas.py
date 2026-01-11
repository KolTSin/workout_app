from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeeklyPlanCreate(BaseModel):
    user_id: UUID
    week_start_date: date
    timezone: str = "UTC"
    strategy: Literal["ULF_2C", "FULL_3", "UL_4", "CUSTOM"] = "ULF_2C"


class WeeklyPlanDay(BaseModel):
    date: date
    label: Literal["UPPER", "LOWER", "FULL", "CARDIO", "MOBILITY", "REST"]
    session_plan_id: Optional[UUID] = None
    notes: Optional[str] = None


class WeeklyPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    week_start_date: date
    timezone: str
    strategy: Optional[str] = None
    days: list[WeeklyPlanDay]
    created_at: datetime


class LoadSuggestion(BaseModel):
    kind: Literal["KG", "LB", "BODYWEIGHT", "MACHINE_LEVEL"]
    value: float
    unit: str
    rounding_step: Optional[float] = None


class PrescriptionSet(BaseModel):
    set_number: int
    target_reps_min: Optional[int] = None
    target_reps_max: Optional[int] = None
    target_rpe: Optional[float] = None
    rest_seconds: Optional[int] = None
    load_suggestion: Optional[LoadSuggestion] = None
    tempo: Optional[str] = None
    notes: Optional[str] = None


class Prescription(BaseModel):
    sets: list[PrescriptionSet]


class SessionItem(BaseModel):
    order: int
    exercise_id: str
    name: str
    category: Literal["COMPOUND", "ACCESSORY", "CORE", "CONDITIONING"]
    equipment: Optional[str] = None
    substitutions: list[str] = Field(default_factory=list)
    prescription: Prescription


class WarmupItem(BaseModel):
    kind: Literal["GENERAL", "SPECIFIC"]
    text: str
    duration_seconds: Optional[int] = None


class ReadinessHint(BaseModel):
    enabled: bool
    adjustment: Optional[
        Literal["NONE", "LIGHTEN_LOAD_5", "REDUCE_ONE_SET", "EASIER_VARIATION"]
    ] = None


class SessionPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: date
    timezone: str
    session_type: Literal["UPPER", "LOWER", "FULL", "CARDIO", "MOBILITY"]
    phase: Literal["CALIBRATION", "TRAINING", "DELOAD"]
    readiness_hint: Optional[ReadinessHint] = None
    warmup: list[WarmupItem]
    items: list[SessionItem]
    created_at: datetime


class SessionPlanRequest(BaseModel):
    user_id: UUID
    date: date


class SessionLogSet(BaseModel):
    exercise_id: str
    set_number: int
    reps_done: int
    load_used: Optional[float] = None
    rpe: Optional[float] = None


class SessionLogCreate(BaseModel):
    user_id: UUID
    date: date
    session_type: Literal["UPPER", "LOWER", "FULL", "CARDIO", "MOBILITY"]
    session_plan_id: Optional[UUID] = None
    readiness: Optional[dict] = None
    notes: Optional[str] = None
    sets: list[SessionLogSet]

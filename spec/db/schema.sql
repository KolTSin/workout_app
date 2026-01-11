-- USERS
CREATE TABLE users (
  id UUID PRIMARY KEY,
  timezone TEXT NOT NULL DEFAULT 'Europe/Copenhagen',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- EXERCISES (global library)
CREATE TABLE exercises (
  id TEXT PRIMARY KEY,                         -- e.g. "db_bench_press"
  name TEXT NOT NULL,
  pattern TEXT NOT NULL,                       -- "PUSH_H", "PULL_H", "SQUAT", "HINGE", ...
  equipment TEXT NOT NULL,                     -- "DUMBBELL", "BARBELL", "MACHINE", "BODYWEIGHT"
  default_rep_min INT NOT NULL,
  default_rep_max INT NOT NULL,
  default_target_rpe NUMERIC(3,1) NOT NULL,
  step_up_pct NUMERIC(6,4) NOT NULL,           -- e.g. 0.025
  rounding_step NUMERIC(6,2) NOT NULL          -- e.g. 2.5
);

-- SUBSTITUTIONS (directed graph)
CREATE TABLE exercise_substitutions (
  exercise_id TEXT REFERENCES exercises(id) ON DELETE CASCADE,
  substitute_id TEXT REFERENCES exercises(id) ON DELETE CASCADE,
  priority INT NOT NULL DEFAULT 1,
  PRIMARY KEY (exercise_id, substitute_id)
);

-- USER EXERCISE STATS (the personalization core)
CREATE TABLE user_exercise_stats (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  exercise_id TEXT REFERENCES exercises(id) ON DELETE CASCADE,
  phase TEXT NOT NULL DEFAULT 'CALIBRATION',   -- CALIBRATION/TRAINING/DELOAD
  next_load NUMERIC(10,2),                     -- null for bodyweight-only
  rep_min INT NOT NULL,
  rep_max INT NOT NULL,
  target_rpe NUMERIC(3,1) NOT NULL,
  stagnation_count INT NOT NULL DEFAULT 0,
  last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, exercise_id)
);

-- WEEKLY PLANS
CREATE TABLE weekly_plans (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  timezone TEXT NOT NULL,
  strategy TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, week_start_date)
);

CREATE TABLE weekly_plan_days (
  weekly_plan_id UUID REFERENCES weekly_plans(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  label TEXT NOT NULL,                         -- UPPER/LOWER/FULL/CARDIO/REST
  session_plan_id UUID,
  notes TEXT,
  PRIMARY KEY (weekly_plan_id, date)
);

-- SESSION PLANS (what the app shows)
CREATE TABLE session_plans (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  timezone TEXT NOT NULL,
  session_type TEXT NOT NULL,
  phase TEXT NOT NULL,
  plan_json JSONB NOT NULL,                    -- store full SessionPlan
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, date, session_type)
);

-- SESSION LOGS (what actually happened)
CREATE TABLE session_logs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  session_plan_id UUID REFERENCES session_plans(id) ON DELETE SET NULL,
  date DATE NOT NULL,
  session_type TEXT NOT NULL,
  readiness_json JSONB,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE session_log_sets (
  id UUID PRIMARY KEY,
  session_log_id UUID REFERENCES session_logs(id) ON DELETE CASCADE,
  exercise_id TEXT REFERENCES exercises(id),
  set_number INT NOT NULL,
  reps_done INT NOT NULL,
  load_used NUMERIC(10,2),
  rpe NUMERIC(3,1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_log_sets_exercise ON session_log_sets (exercise_id);
CREATE INDEX idx_user_log_date ON session_logs (user_id, date DESC);

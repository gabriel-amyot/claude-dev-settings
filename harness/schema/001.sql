-- Shared harness data contract, version 1. Original evidence stays with its producer.
CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('skill','agent','hook','workflow')),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_path TEXT NOT NULL,
    revision TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    group_name TEXT NOT NULL DEFAULT 'ungrouped',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    producer TEXT NOT NULL CHECK (producer = 'collector')
) STRICT;

CREATE TABLE IF NOT EXISTS availability (
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    host TEXT NOT NULL CHECK (host IN ('claude','codex','shared','unknown')),
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('discovered','validated','blocked','unknown')),
    observed_at TEXT NOT NULL,
    evidence TEXT NOT NULL,
    producer TEXT NOT NULL CHECK (producer = 'collector'),
    PRIMARY KEY (capability_id,host,role,path)
) STRICT;

CREATE TABLE IF NOT EXISTS dependencies (
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    target_id TEXT NOT NULL REFERENCES capabilities(id),
    relationship TEXT NOT NULL CHECK (relationship IN ('references','requires','delegates')),
    evidence TEXT NOT NULL,
    producer TEXT NOT NULL CHECK (producer = 'collector'),
    PRIMARY KEY (capability_id,target_id,relationship)
) STRICT;

CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    host TEXT NOT NULL CHECK (host IN ('claude','codex','shared','unknown')),
    role TEXT NOT NULL,
    session_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    signal TEXT NOT NULL CHECK (signal IN ('invoked','loaded','historical_estimate')),
    source_path TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    revision TEXT,
    outcome TEXT NOT NULL DEFAULT 'unknown' CHECK (outcome IN ('unknown','success','failure')),
    count INTEGER NOT NULL DEFAULT 1 CHECK (count > 0),
    producer TEXT NOT NULL CHECK (producer = 'collector')
) STRICT;
CREATE INDEX IF NOT EXISTS usage_capability_time ON usage_events(capability_id,occurred_at);

CREATE TABLE IF NOT EXISTS frictions (
    id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    host TEXT NOT NULL CHECK (host IN ('claude','codex','shared','unknown')),
    role TEXT NOT NULL,
    session_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    impact TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
    resolves_id TEXT REFERENCES frictions(id),
    producer TEXT NOT NULL CHECK (producer IN ('agent','maintainer')),
    CHECK ((status = 'open' AND resolves_id IS NULL AND producer = 'agent')
        OR (status = 'resolved' AND resolves_id IS NOT NULL AND producer = 'maintainer')),
    CHECK (resolves_id IS NULL OR resolves_id != id)
) STRICT;
CREATE UNIQUE INDEX IF NOT EXISTS friction_resolution_once ON frictions(resolves_id) WHERE resolves_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS friction_capability_time ON frictions(capability_id,occurred_at);

-- Registry definitions are mutable metadata, never proof of an execution.
CREATE TABLE IF NOT EXISTS eval_suites (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    layer TEXT NOT NULL,
    source_path TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    runner TEXT,
    last_green TEXT,
    producer TEXT NOT NULL CHECK (producer='collector'),
    UNIQUE(source_path,suite_id)
) STRICT;
CREATE INDEX IF NOT EXISTS eval_suite_capability ON eval_suites(capability_id);

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    occurred_at TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('pass','fail','error','skipped','unknown')),
    source_path TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    revision TEXT,
    host TEXT NOT NULL DEFAULT 'unknown' CHECK (host IN ('claude','codex','shared','unknown')),
    layer TEXT NOT NULL DEFAULT 'unknown',
    summary TEXT,
    producer TEXT NOT NULL CHECK (producer = 'eval-runner')
) STRICT;
CREATE INDEX IF NOT EXISTS eval_capability_time ON eval_runs(capability_id,occurred_at);
CREATE INDEX IF NOT EXISTS eval_suite_time ON eval_runs(suite_id,occurred_at);

CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    occurred_at TEXT NOT NULL,
    status TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    host TEXT NOT NULL DEFAULT 'unknown' CHECK (host IN ('claude','codex','shared','unknown')),
    role TEXT NOT NULL DEFAULT 'unknown',
    revision TEXT,
    summary TEXT,
    producer TEXT NOT NULL CHECK (producer = 'collector')
) STRICT;
CREATE INDEX IF NOT EXISTS outcome_capability_time ON outcomes(capability_id,occurred_at);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL REFERENCES capabilities(id),
    occurred_at TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('keep','promote','polish','review','retire','prioritize','propose')),
    status TEXT NOT NULL CHECK (status IN ('proposed','approved')),
    rationale TEXT NOT NULL,
    authority TEXT NOT NULL,
    evidence TEXT NOT NULL,
    producer TEXT NOT NULL CHECK (producer IN ('agent','maintainer')),
    CHECK ((producer = 'agent' AND status = 'proposed')
        OR (producer = 'maintainer' AND status = 'approved'))
) STRICT;

CREATE TABLE IF NOT EXISTS coverage (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    host TEXT NOT NULL CHECK (host IN ('claude','codex','shared','unknown')),
    scope TEXT NOT NULL,
    since TEXT,
    until TEXT,
    observed_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('complete','partial','unavailable')),
    detail TEXT NOT NULL,
    producer TEXT NOT NULL CHECK (producer = 'collector')
) STRICT;

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    source_path TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    summary TEXT,
    producer TEXT NOT NULL CHECK (producer IN ('collector','eval-runner','agent','maintainer'))
) STRICT;

PRAGMA user_version = 1;

-- Preserve original observations. Resolutions and revised decisions are new events.
CREATE TRIGGER IF NOT EXISTS usage_events_no_update BEFORE UPDATE ON usage_events BEGIN SELECT RAISE(ABORT,'usage_events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS usage_events_no_delete BEFORE DELETE ON usage_events BEGIN SELECT RAISE(ABORT,'usage_events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS frictions_no_update BEFORE UPDATE ON frictions BEGIN SELECT RAISE(ABORT,'frictions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS frictions_no_delete BEFORE DELETE ON frictions BEGIN SELECT RAISE(ABORT,'frictions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS eval_runs_no_update BEFORE UPDATE ON eval_runs BEGIN SELECT RAISE(ABORT,'eval_runs are immutable'); END;
CREATE TRIGGER IF NOT EXISTS eval_runs_no_delete BEFORE DELETE ON eval_runs BEGIN SELECT RAISE(ABORT,'eval_runs are immutable'); END;
CREATE TRIGGER IF NOT EXISTS outcomes_no_update BEFORE UPDATE ON outcomes BEGIN SELECT RAISE(ABORT,'outcomes are immutable'); END;
CREATE TRIGGER IF NOT EXISTS outcomes_no_delete BEFORE DELETE ON outcomes BEGIN SELECT RAISE(ABORT,'outcomes are immutable'); END;
CREATE TRIGGER IF NOT EXISTS decisions_no_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'decisions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS decisions_no_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'decisions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS artifacts_no_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS artifacts_no_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are immutable'); END;

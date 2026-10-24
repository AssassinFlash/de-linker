"""Versioned planning persistence; no mutable physics in WP post metadata."""

SCHEMA_VERSION = 4
READABLE_SCHEMA_VERSIONS = (1, 2, 3, 4)

JOBS_COLUMNS = """
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    kind TEXT NOT NULL CHECK (kind IN ('evaluate', 'render_report', 'abort_weather', 'reconcile_weather')),
    request_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('queued', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')
    ),
    attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts > 0),
    worker TEXT,
    lease_token TEXT,
    lease_until REAL,
    available_at REAL NOT NULL,
    error_sha256 TEXT,
    output_sha256 TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
"""

EVALUATION_ROUTES_TABLE = """
CREATE TABLE IF NOT EXISTS evaluation_routes (
    job_id TEXT PRIMARY KEY REFERENCES jobs(id),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    execution_sha256 TEXT NOT NULL
);
"""

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    title TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (id, revision) REFERENCES revisions(project_id, number)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS projects_owner ON projects(owner, updated_at);
CREATE TABLE IF NOT EXISTS revisions (
    project_id TEXT NOT NULL REFERENCES projects(id),
    number INTEGER NOT NULL CHECK (number > 0),
    input_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (project_id, number)
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    result_sha256 TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (project_id, revision) REFERENCES revisions(project_id, number)
);
CREATE INDEX IF NOT EXISTS runs_project ON runs(project_id, created_at);
CREATE TABLE IF NOT EXISTS jobs ({JOBS_COLUMNS});
CREATE UNIQUE INDEX IF NOT EXISTS evaluate_once ON jobs(run_id)
    WHERE kind = 'evaluate';
CREATE UNIQUE INDEX IF NOT EXISTS weather_abort_once ON jobs(run_id)
    WHERE kind = 'abort_weather';
CREATE UNIQUE INDEX IF NOT EXISTS weather_reconcile_pending ON jobs(run_id)
    WHERE kind = 'reconcile_weather' AND state IN ('queued','running','retry_wait');
CREATE INDEX IF NOT EXISTS jobs_available ON jobs(state, available_at, lease_until);
-- Durable external-start evidence. This additive extension keeps the existing
-- run/job/wire schemas; old archives acquire the empty table on private restore.
CREATE TABLE IF NOT EXISTS weather_acquisitions (
    run_id TEXT PRIMARY KEY REFERENCES runs(id),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    manifest_sha256 TEXT NOT NULL,
    plan_sha256 TEXT NOT NULL,
    nonce TEXT NOT NULL,
    post_claimed INTEGER NOT NULL CHECK (post_claimed IN (0, 1)),
    started_at REAL NOT NULL,
    deadline_at REAL NOT NULL CHECK (deadline_at > started_at),
    remote_run_id TEXT,
    acknowledgement_sha256 TEXT,
    observation_sha256 TEXT,
    capture_sha256 TEXT,
    abort_sha256 TEXT,
    CHECK ((remote_run_id IS NULL) = (acknowledgement_sha256 IS NULL)),
    CHECK (remote_run_id IS NULL OR post_claimed = 1),
    CHECK (observation_sha256 IS NULL OR remote_run_id IS NOT NULL),
    CHECK (capture_sha256 IS NULL OR remote_run_id IS NOT NULL),
    CHECK (abort_sha256 IS NULL OR remote_run_id IS NOT NULL)
);
-- Additive operator/cache extension. Core schema-v2 records and wire documents
-- are unchanged; old unindexed jobs can be routed from their frozen manifests.
{EVALUATION_ROUTES_TABLE}
CREATE INDEX IF NOT EXISTS evaluation_routes_key
    ON evaluation_routes(execution_sha256, job_id);
CREATE TABLE IF NOT EXISTS execution_control (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    draining INTEGER NOT NULL CHECK (draining IN (0, 1))
);
INSERT OR IGNORE INTO execution_control (id, schema_version, draining) VALUES (1, 1, 0);
CREATE TABLE IF NOT EXISTS idempotency (
    actor TEXT NOT NULL,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    command_sha256 TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (actor, scope, key)
);
CREATE TABLE IF NOT EXISTS project_assets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    content_sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    purpose TEXT NOT NULL,
    metadata_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS assets_project ON project_assets(project_id);
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    content_sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    locale TEXT NOT NULL,
    branding_sha256 TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS handoffs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    revision INTEGER NOT NULL,
    candidate_id TEXT NOT NULL,
    snapshot_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS ownership_transfers (
    project_id TEXT PRIMARY KEY REFERENCES projects(id),
    previous_owner TEXT NOT NULL,
    new_owner TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS principal_closures (
    guest TEXT PRIMARY KEY,
    new_owner TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS closures_owner ON principal_closures(new_owner, guest);
CREATE TRIGGER IF NOT EXISTS retired_guest_insert
BEFORE INSERT ON projects
WHEN EXISTS (SELECT 1 FROM principal_closures WHERE guest=NEW.owner)
BEGIN
    SELECT RAISE(ABORT, 'retired principal');
END;
CREATE TRIGGER IF NOT EXISTS retired_guest_owner_update
BEFORE UPDATE OF owner ON projects
WHEN EXISTS (SELECT 1 FROM principal_closures WHERE guest=NEW.owner)
BEGIN
    SELECT RAISE(ABORT, 'retired principal');
END;
CREATE TRIGGER IF NOT EXISTS guest_closure_requires_complete_transfer
BEFORE INSERT ON principal_closures
WHEN EXISTS (SELECT 1 FROM projects WHERE owner=NEW.guest)
BEGIN
    SELECT RAISE(ABORT, 'guest projects remain');
END;
"""

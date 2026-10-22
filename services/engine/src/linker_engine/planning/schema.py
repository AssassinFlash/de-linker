"""Versioned planning persistence; no mutable physics in WP post metadata."""

SCHEMA_VERSION = 2
READABLE_SCHEMA_VERSIONS = (1, 2)

SCHEMA = """
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
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    kind TEXT NOT NULL CHECK (kind IN ('evaluate', 'render_report')),
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
);
CREATE UNIQUE INDEX IF NOT EXISTS evaluate_once ON jobs(run_id)
    WHERE kind = 'evaluate';
CREATE INDEX IF NOT EXISTS jobs_available ON jobs(state, available_at, lease_until);
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

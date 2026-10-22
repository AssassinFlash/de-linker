"""Research-only experiment for a new planning application, not a production module.

Exercises revision snapshots, durable work, fencing, and immutable report reads.
No geometry, electrical, energy calculation, authorization, or production I/O.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

HERE = Path(__file__).resolve().parent


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


class Conflict(Exception):
    pass


class PlanningStore:
    def __init__(self, path):
        self.path = path
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS project(id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS revision(
                    project TEXT NOT NULL, number INTEGER NOT NULL, payload TEXT NOT NULL,
                    hash TEXT NOT NULL, PRIMARY KEY(project,number));
                CREATE TABLE IF NOT EXISTS run(
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, revision INTEGER NOT NULL,
                    manifest TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL, epoch INTEGER NOT NULL DEFAULT 0,
                    worker TEXT, lease_until REAL, result TEXT,
                    UNIQUE(project, revision, fingerprint));
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def create(self, payload):
        project = str(uuid4())
        with self.transaction() as db:
            db.execute("INSERT INTO project VALUES (?,1)", (project,))
            db.execute("INSERT INTO revision VALUES (?,1,?,?)", (project, encode(payload), digest(payload)))
        return project

    def revise(self, project, expected, payload):
        with self.transaction() as db:
            updated = db.execute("UPDATE project SET revision=revision+1 WHERE id=? AND revision=?", (project, expected))
            if updated.rowcount != 1:
                raise Conflict("project revision changed")
            number = expected + 1
            db.execute("INSERT INTO revision VALUES (?,?,?,?)", (project, number, encode(payload), digest(payload)))
        return number

    def submit(self, project, revision, versions):
        with self.transaction() as db:
            original = db.execute("SELECT * FROM revision WHERE project=? AND number=?", (project, revision)).fetchone()
            if original is None:
                raise Conflict("unknown project revision")
            manifest = {"input_hash": original["hash"], "versions": versions}
            fingerprint = digest(manifest)
            known = db.execute("SELECT id FROM run WHERE project=? AND revision=? AND fingerprint=?", (project, revision, fingerprint)).fetchone()
            if known:
                return known["id"]
            run = str(uuid4())
            db.execute("INSERT INTO run(id,project,revision,manifest,fingerprint,status) VALUES (?,?,?,?,?,'queued')",
                       (run, project, revision, encode(manifest), fingerprint))
        return run

    def claim(self, worker, now, ttl):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM run WHERE status='queued' OR (status='running' AND lease_until<=?) ORDER BY rowid LIMIT 1", (now,)).fetchone()
            if row is None:
                return None
            epoch = row["epoch"] + 1
            db.execute("UPDATE run SET status='running',epoch=?,worker=?,lease_until=? WHERE id=?", (epoch, worker, now + ttl, row["id"]))
            snapshot = db.execute("SELECT payload FROM revision WHERE project=? AND number=?", (row["project"], row["revision"])).fetchone()
            return {"id": row["id"], "epoch": epoch, "input": json.loads(snapshot["payload"])}

    def finish(self, lease, now, result):
        with self.transaction() as db:
            updated = db.execute("UPDATE run SET status='succeeded',result=? WHERE id=? AND status='running' AND epoch=? AND lease_until>?",
                                 (encode(result), lease["id"], lease["epoch"], now))
            if updated.rowcount != 1:
                raise Conflict("lease expired, cancelled, or superseded")

    def cancel(self, run):
        with self.transaction() as db:
            return db.execute("UPDATE run SET status='cancelled' WHERE id=? AND status IN ('queued','running')", (run,)).rowcount == 1

    def view(self, run):
        with self.connection() as db:
            r = db.execute("SELECT r.*,p.revision AS current_revision,v.payload FROM run r JOIN project p ON p.id=r.project JOIN revision v ON v.project=r.project AND v.number=r.revision WHERE r.id=?", (run,)).fetchone()
            return {"status": r["status"], "revision": r["revision"], "current_revision": r["current_revision"],
                    "current": r["revision"] == r["current_revision"],
                    "input": json.loads(r["payload"]), "manifest": json.loads(r["manifest"]),
                    "result": json.loads(r["result"]) if r["result"] else None}

    def export(self, run):
        v = self.view(run)
        if v["status"] != "succeeded":
            raise Conflict("no completed result")
        # Historical export is valid and explicitly retains its revision.
        snapshot = {k: v[k] for k in ("revision", "input", "manifest", "result")}
        return {"snapshot": snapshot, "content_hash": digest(snapshot)}

    def current_proposal(self, run):
        v = self.view(run)
        if v["status"] != "succeeded" or not v["current"] or v["result"].get("feasibility") != "validated":
            raise Conflict("current validated proposal required")
        return self.export(run)


def rejected(action):
    try:
        action()
    except Conflict:
        return True
    return False


def main():
    results = {}
    versions = {"physics": "research-v1", "capabilities": "source-hash", "country_policy": "policy-hash"}
    with tempfile.TemporaryDirectory(prefix="roof-architecture-research-") as directory:
        path = Path(directory) / "planning.sqlite"
        store = PlanningStore(path)
        project = store.create({"modules": 19, "annual_kwh": 4500})
        run = store.submit(project, 1, versions)
        assert store.submit(project, 1, versions) == run
        results["duplicate_submission"] = {"single_run": True}

        first = store.claim("worker-a", 0, 10)
        store.revise(project, 1, {"modules": 19, "annual_kwh": 6000})
        store.finish(first, 1, {"feasibility": "validated", "bom_modules": 19})
        old = store.export(run)
        assert old["snapshot"]["input"]["annual_kwh"] == 4500
        assert not store.view(run)["current"]
        assert rejected(lambda: store.current_proposal(run))
        assert rejected(lambda: store.revise(project, 1, {"modules": 20}))
        results["editing_during_calculation"] = {"calculated_revision": 1, "current_revision": 2,
            "historical_report_consumption": 4500, "current_proposal_rejected": True,
            "stale_edit_rejected": True}

        second = store.submit(project, 2, versions)
        a = store.claim("worker-a", 10, 10)
        # Another process/instance can recover the expired durable job.
        recovered = PlanningStore(path)
        b = recovered.claim("worker-b", 21, 10)
        assert a["id"] == b["id"] == second and b["epoch"] > a["epoch"]
        assert rejected(lambda: store.finish(a, 22, {"feasibility": "validated", "bom_modules": 999}))
        recovered.finish(b, 22, {"feasibility": "validated", "bom_modules": 19})
        assert recovered.current_proposal(second)["snapshot"]["result"]["bom_modules"] == 19
        assert store.export(run) == old
        results["restart_and_expired_worker"] = {"recovered_same_run": True, "old_worker_fenced": True,
            "final_modules": 19, "historical_export_unchanged": True}

        unknown_project = store.create({"backup_load_kw": 10})
        unknown_run = store.submit(unknown_project, 1, versions)
        lease = store.claim("worker-c", 30, 10)
        store.finish(lease, 31, {"feasibility": "needs_evidence", "missing": ["continuous_backup_power"]})
        assert store.view(unknown_run)["status"] == "succeeded"
        assert rejected(lambda: store.current_proposal(unknown_run))
        results["job_success_is_not_engineering_pass"] = {"job": "succeeded", "feasibility": "needs_evidence", "proposal_rejected": True}

        cancelled_project = store.create({"modules": 25})
        cancelled_run = store.submit(cancelled_project, 1, versions)
        lease = store.claim("worker-d", 40, 10)
        assert store.cancel(cancelled_run)
        assert rejected(lambda: store.finish(lease, 41, {"feasibility": "validated"}))
        results["cancelled_worker_completion"] = {"rejected": True}

        concurrent_project = store.create({"modules": 30})
        concurrent_run = store.submit(concurrent_project, 1, versions)
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda n: PlanningStore(path).claim(n, 50, 10), ("x", "y")))
        winners = [x for x in claims if x]
        assert len(winners) == 1 and winners[0]["id"] == concurrent_run
        results["two_real_connections"] = {"claimants": 2, "winners": 1}

    output = {"purpose": "architecture workflow experiment only, not engineering validation",
              "database": "temporary SQLite WAL, removed after run", "sqlite_library": sqlite3.sqlite_version,
              "cases": results, "limitations": ["no authorization or tenant isolation implemented",
              "no production throughput or power-loss test", "no actual physics model", "no external delivery/outbox proof"]}
    (HERE / "lifecycle-results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

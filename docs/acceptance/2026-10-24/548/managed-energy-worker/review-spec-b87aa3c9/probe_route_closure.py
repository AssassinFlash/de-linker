"""Independent closure probe; all queue/database/byte mutations are in memory.

Reuse only the preserved failure probe's import/memory adapters. Its failure-case
body is not executed. Planning modules load immutable git bytes at the final pin.
"""

from pathlib import Path

FINAL_PIN = "b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3"
original = Path(__file__).parent.parent / "review-spec-af4aa66e/probe_route_cache.py"
adapters = original.read_text().split("workspace = Workspace.__new__(Workspace)", 1)[0]
assert 'PIN = "af4aa66e9f4994efcbe2159f428a93cc9007c71a"' in adapters
adapters = adapters.replace("af4aa66e9f4994efcbe2159f428a93cc9007c71a", FINAL_PIN)
exec(compile(adapters, str(original) + ":memory-adapters", "exec"), globals())
assert PIN == FINAL_PIN


def make_workspace():
    workspace = Workspace.__new__(Workspace)
    workspace.database = MemoryDatabase()
    workspace.blobs = MemoryBlobs()
    now = [100_000.0]
    workspace.clock = lambda: now[0]
    return workspace, now


def enqueue(workspace, actor, context, key):
    project = workspace.create(actor, key, {"fixture_only": True}, key=key)
    return workspace.evaluate(actor, project.id, 1, context, key="run", max_attempts=2)


owner = Actor("user", "synthetic-closure-review")
own_context = Context(
    code_sha256=digest(b"synthetic-current-runtime"),
    models={"closure-probe": "1"}, assets={}, parameters={"fixture_only": True},
)
foreign_context = Context(
    code_sha256=digest(b"synthetic-retained-runtime"),
    models={"closure-probe": "1"}, assets={}, parameters={"fixture_only": True},
)
workspace, now = make_workspace()
foreign = []
for index in range(5):
    foreign.append(enqueue(workspace, owner, foreign_context, "earlier-foreign-" + str(index)))
    now[0] += 1
own = enqueue(workspace, owner, own_context, "later-own")
wrong_key = digest(b"no-live-worker-for-this-key")
with workspace.database.transaction() as connection:
    connection.execute(
        "UPDATE evaluation_routes SET execution_sha256=? WHERE job_id IN "
        "(SELECT id FROM jobs WHERE run_id=?)", (wrong_key, own.id),
    )
jobs = Jobs(workspace)
routing = EvaluationRouting(execution_key(own_context.document()), 1)
for _ in range(5):
    assert jobs.claim("matching", kinds=("evaluate",), lease_seconds=30, routing=routing) is None
lease = jobs.claim("matching", kinds=("evaluate",), lease_seconds=30, routing=routing)
assert lease is not None and lease.run_id == own.id and lease.attempt == 1
assert workspace.run(owner, own.id).manifest_sha256 == own.manifest_sha256
assert all(workspace.run(owner, run.id).state == "queued" for run in foreign)
with workspace.database.read() as connection:
    assert connection.execute("SELECT COUNT(*) FROM jobs WHERE attempt=0").fetchone()[0] == 5
    assert connection.execute(
        "SELECT execution_sha256 FROM evaluation_routes JOIN jobs ON jobs.id=job_id WHERE run_id=?",
        (own.id,),
    ).fetchone()[0] == routing.key

# A later corrupt route behind the cursor must be repaired on wraparound too.
with workspace.database.transaction() as connection:
    connection.execute(
        "UPDATE evaluation_routes SET execution_sha256=? WHERE job_id IN "
        "(SELECT id FROM jobs WHERE run_id=?)", (wrong_key, foreign[0].id),
    )
assert jobs.claim("matching", kinds=("evaluate",), lease_seconds=30, routing=routing) is None
with workspace.database.read() as connection:
    assert connection.execute(
        "SELECT execution_sha256 FROM evaluation_routes JOIN jobs ON jobs.id=job_id WHERE run_id=?",
        (foreign[0].id,),
    ).fetchone()[0] == execution_key(foreign_context.document())
print(json.dumps({
    "pin": PIN, "batch_size": 1, "earlier_foreign_rows": 5,
    "own_unknown_route_repaired_on_poll": 6, "own_attempt": lease.attempt,
    "foreign_attempts_unchanged": True, "manifest_unchanged": True,
    "wraparound_repairs_present_route": True,
}))
workspace.database.connection.close()

# Missing original request still fails explicitly even with a present wrong cache.
workspace, _ = make_workspace()
run = enqueue(workspace, owner, own_context, "corrupt-request")
with workspace.database.transaction() as connection:
    connection.execute("UPDATE jobs SET request_sha256=?", (digest(b"absent-request"),))
    connection.execute("UPDATE evaluation_routes SET execution_sha256=?", (wrong_key,))
assert Jobs(workspace).claim("matching", kinds=("evaluate",), lease_seconds=30, routing=routing) is None
failed = workspace.run(owner, run.id)
assert failed.state == "failed"
assert failed.error == {"code": "version_unavailable", "retryable": False}
print(json.dumps({"present_route_corrupt_request": "failed", "code": failed.error["code"]}))
workspace.database.connection.close()

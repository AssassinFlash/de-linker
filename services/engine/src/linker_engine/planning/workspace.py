"""The project authority: immutable inputs/runs and optimistic, owned commands.

HTTP and commerce adapters use this interface instead of assembling project
facts from mutable WordPress fields. Identity and dependency resolution happen
in the trusted adapters; this module never accepts a browser-selected owner.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast
from uuid import uuid4

from . import commands
from .access import active_actor, positive_integer, project_row
from .brief import validate_new_brief
from .canonical import Object, digest, encode
from .country_rules import validate_country_rule_inputs
from .equipment_condition_inputs import validate_condition_inputs
from .errors import (
    Conflict,
    EvaluationRevisionChanged,
    InvalidInput,
    NotFound,
    VersionUnavailable,
)
from .execution_control import require_accepting
from .execution_identity import execution_key
from .geometry import validate_project_geometry
from .grid_connection import validate_grid_connection
from .installation_inputs import validate_installation_project
from .project_input_contracts import (
    create_command,
    require_input_contract,
    revise_command,
)
from .records import Actor, Context, JobState, Project, Run
from .runtime_snapshot import RuntimeSnapshot
from .storage import Blobs, Database


class Workspace:
    """Same-host project authority shared by a gateway and durable workers."""

    def __init__(
        self,
        directory: Path,
        *,
        clock: Callable[[], float] = time.time,
        runtime: RuntimeSnapshot | None = None,
    ) -> None:
        self.database = Database(directory / "workspace.sqlite")
        self.blobs = Blobs(directory / "blobs")
        self.clock = clock
        self._runtime = runtime
        if runtime is not None:
            self.blobs.put(runtime.content)

    def kernel_runtime(self) -> RuntimeSnapshot:
        """Configured kernels share their host's immutable, already stored release."""
        if self._runtime is not None:
            return self._runtime
        # Standalone kernels can be constructed across code changes on the same store.
        snapshot = RuntimeSnapshot.capture()
        self.blobs.put(snapshot.content)
        return snapshot

    def _project(
        self,
        connection: sqlite3.Connection,
        actor: Actor,
        project_id: str,
        revision: int | None = None,
    ) -> Project:
        project = project_row(connection, actor, project_id)
        number = project["revision"] if revision is None else revision
        row = connection.execute(
            "SELECT input_sha256 FROM revisions WHERE project_id=? AND number=?",
            (project_id, number),
        ).fetchone()
        if row is None:
            raise NotFound("revision not found")
        return Project(
            id=project_id,
            title=project["title"],
            revision=number,
            input_sha256=row["input_sha256"],
            inputs=self.blobs.object(row["input_sha256"]),
            owner=project["owner"],
        )

    def create(
        self,
        actor: Actor,
        title: str,
        inputs: Object,
        *,
        key: str,
        input_contract: str | None = None,
    ) -> Project:
        if actor.kind == "team":
            raise NotFound("project not found")
        if not title.strip():
            raise InvalidInput("project title required")
        command = commands.command_hash(
            create_command(title, inputs, input_contract=input_contract), key
        )
        with self.database.transaction() as connection:
            active_actor(connection, actor)
            receipt = commands.replay(
                connection, self.blobs, actor, "create", key, command
            )
            if receipt is not None:
                return self._project(
                    connection, actor, commands.receipt_string(receipt, "project_id"), 1
                )
            require_input_contract(None, inputs, input_contract)
            validate_new_brief(inputs)
            validate_grid_connection(inputs)
            validate_country_rule_inputs(inputs)
            validate_project_geometry(inputs)
            validate_installation_project(inputs)
            validate_condition_inputs(inputs)
            content = self.blobs.put_object(inputs)
            project_id = uuid4().hex
            now = self.clock()
            connection.execute(
                "INSERT INTO projects "
                "(id, owner, title, revision, created_at, updated_at) "
                "VALUES (?, ?, ?, 1, ?, ?)",
                (project_id, actor.key, title, now, now),
            )
            connection.execute(
                "INSERT INTO revisions (project_id, number, input_sha256, created_at) "
                "VALUES (?, 1, ?, ?)",
                (project_id, content, now),
            )
            commands.remember(
                connection,
                self.blobs,
                actor,
                "create",
                key,
                command,
                {"project_id": project_id, "revision": 1},
                now,
            )
            return self._project(connection, actor, project_id)

    def get(
        self, actor: Actor, project_id: str, *, revision: int | None = None
    ) -> Project:
        if revision is not None:
            positive_integer(revision, "revision")
        with self.database.read() as connection:
            return self._project(connection, actor, project_id, revision)

    def projects(self, actor: Actor) -> list[Project]:
        with self.database.read() as connection:
            active_actor(connection, actor)
            rows = connection.execute(
                "SELECT id FROM projects WHERE owner=? ORDER BY updated_at DESC, id",
                (actor.key,),
            ).fetchall()
            return [self._project(connection, actor, row["id"]) for row in rows]

    def revise(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        *,
        key: str,
        input_contract: str | None = None,
    ) -> Project:
        positive_integer(expected_revision, "expected revision")
        command = commands.command_hash(
            revise_command(expected_revision, inputs, input_contract=input_contract),
            key,
        )
        scope = f"revise:{project_id}"
        with self.database.transaction() as connection:
            project = project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.blobs, actor, scope, key, command
            )
            if receipt is not None:
                return self._project(
                    connection,
                    actor,
                    project_id,
                    commands.receipt_number(receipt, "revision"),
                )
            if project["revision"] != expected_revision:
                raise Conflict("project inputs have changed")
            previous = self._project(connection, actor, project_id)
            require_input_contract(previous.inputs, inputs, input_contract)
            validate_new_brief(inputs)
            validate_grid_connection(inputs)
            validate_country_rule_inputs(inputs)
            validate_project_geometry(inputs)
            validate_installation_project(inputs)
            validate_condition_inputs(inputs)
            content = self.blobs.put_object(inputs)
            number = expected_revision + 1
            now = self.clock()
            connection.execute(
                "INSERT INTO revisions (project_id, number, input_sha256, created_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, number, content, now),
            )
            connection.execute(
                "UPDATE projects SET revision=?, updated_at=? WHERE id=?",
                (number, now, project_id),
            )
            commands.remember(
                connection,
                self.blobs,
                actor,
                scope,
                key,
                command,
                {"project_id": project_id, "revision": number},
                now,
            )
            return self._project(connection, actor, project_id, number)

    def evaluate(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        context: Context,
        *,
        key: str,
        max_attempts: int,
        intent: Object | None = None,
    ) -> Run:
        """Enqueue a frozen dependency manifest; no numerical work in this call."""
        positive_integer(expected_revision, "expected revision")
        positive_integer(max_attempts, "maximum attempts")
        resolved = context.document()
        command = commands.command_hash(
            {
                "expected_revision": expected_revision,
                "context": resolved,
                "max_attempts": max_attempts,
            }
            if intent is None
            else {"expected_revision": expected_revision, "intent": intent},
            key,
        )
        # A command cannot refer to bytes that were never published. The
        # evaluator rechecks every hash on replay instead of trusting a path.
        for sha256 in context.assets.values():
            self.blobs.read(sha256)
        scope = f"evaluate:{project_id}"
        with self.database.transaction() as connection:
            project = project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.blobs, actor, scope, key, command
            )
            if receipt is not None:
                return self._run(
                    connection, actor, commands.receipt_string(receipt, "run_id")
                )
            require_accepting(connection)
            if project["revision"] != expected_revision:
                raise EvaluationRevisionChanged("project inputs have changed")
            inputs = self._project(connection, actor, project_id, expected_revision)
            manifest = self.blobs.put_object(
                {
                    "schema": 1,
                    "project_id": project_id,
                    "revision": expected_revision,
                    "input_sha256": inputs.input_sha256,
                    "context": resolved,
                }
            )
            run_id = uuid4().hex
            request = self.blobs.put_object({"manifest_sha256": manifest})
            now = self.clock()
            job_id = uuid4().hex
            connection.execute(
                "INSERT INTO runs "
                "(id, project_id, revision, manifest_sha256, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, project_id, expected_revision, manifest, now),
            )
            connection.execute(
                "INSERT INTO jobs "
                "(id, run_id, kind, request_sha256, state, max_attempts, "
                "available_at, created_at, updated_at) "
                "VALUES (?, ?, 'evaluate', ?, 'queued', ?, ?, ?, ?)",
                (job_id, run_id, request, max_attempts, now, now, now),
            )
            connection.execute(
                "INSERT INTO evaluation_routes (job_id, schema_version, execution_sha256) "
                "VALUES (?, 1, ?)",
                (job_id, execution_key(resolved)),
            )
            commands.remember(
                connection,
                self.blobs,
                actor,
                scope,
                key,
                command,
                {"run_id": run_id},
                now,
            )
            return self._run(connection, actor, run_id)

    def _run(self, connection: sqlite3.Connection, actor: Actor, run_id: str) -> Run:
        row = connection.execute(
            "SELECT runs.*, jobs.state, jobs.error_sha256 FROM runs "
            "JOIN jobs ON jobs.run_id=runs.id AND jobs.kind='evaluate' "
            "WHERE runs.id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise NotFound("run not found")
        project = project_row(connection, actor, row["project_id"])
        return Run(
            id=run_id,
            project_id=row["project_id"],
            revision=row["revision"],
            state=cast(JobState, row["state"]),
            manifest_sha256=row["manifest_sha256"],
            manifest=self.blobs.object(row["manifest_sha256"]),
            result_sha256=row["result_sha256"],
            result=(
                self.blobs.object(row["result_sha256"])
                if row["result_sha256"] is not None
                else None
            ),
            error=(
                self.blobs.object(row["error_sha256"])
                if row["error_sha256"] is not None
                else None
            ),
            is_current=project["revision"] == row["revision"],
        )

    def run(self, actor: Actor, run_id: str) -> Run:
        with self.database.read() as connection:
            return self._run(connection, actor, run_id)

    def runs(self, actor: Actor, project_id: str) -> list[Run]:
        with self.database.read() as connection:
            project_row(connection, actor, project_id)
            rows = connection.execute(
                "SELECT id FROM runs WHERE project_id=? ORDER BY created_at DESC, id",
                (project_id,),
            ).fetchall()
            return [self._run(connection, actor, row["id"]) for row in rows]

    def cancel(self, actor: Actor, run_id: str) -> Run:
        with self.database.transaction() as connection:
            run = self._run(connection, actor, run_id)
            project_row(connection, actor, run.project_id, write=True)
            connection.execute(
                "UPDATE jobs SET state='cancelled', updated_at=? WHERE run_id=? "
                "AND kind NOT IN ('abort_weather','reconcile_weather') AND state IN ('queued', 'running', 'retry_wait')",
                (self.clock(), run_id),
            )
            return self._run(connection, actor, run_id)

    def claim_guest(
        self, guest: Actor, user: Actor, project_id: str, *, key: str
    ) -> Project:
        """The gateway must verify BOTH the guest cookie and logged-in account."""
        if guest.kind != "guest" or user.kind != "user":
            raise InvalidInput("verified guest and account required")
        command = commands.command_hash({"guest": guest.key}, key)
        scope = f"claim:{project_id}"
        with self.database.transaction() as connection:
            receipt = commands.replay(connection, self.blobs, user, scope, key, command)
            if receipt is not None:
                return self._project(connection, user, project_id)
            project = project_row(connection, guest, project_id, write=True)
            now = self.clock()
            connection.execute(
                "INSERT INTO ownership_transfers "
                "(project_id, previous_owner, new_owner, created_at) VALUES (?, ?, ?, ?)",
                (project_id, project["owner"], user.key, now),
            )
            connection.execute(
                "UPDATE projects SET owner=?, updated_at=? WHERE id=?",
                (user.key, now, project_id),
            )
            commands.remember(
                connection,
                self.blobs,
                user,
                scope,
                key,
                command,
                {"project_id": project_id},
                now,
            )
            return self._project(connection, user, project_id)

    def pinned_inputs(self, manifest: Object) -> Object:
        """Private worker read: return the frozen input, never project latest."""
        value = manifest.get("input_sha256")
        if not isinstance(value, str):
            raise VersionUnavailable("input hash absent from manifest")
        return self.blobs.object(value)

    @staticmethod
    def input_hash(inputs: Object) -> str:
        return digest(encode(inputs))

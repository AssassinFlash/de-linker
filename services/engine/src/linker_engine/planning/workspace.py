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
from typing import Literal, cast
from uuid import uuid4

from . import commands
from .access import active_actor, positive_integer, project_row
from .backup_demand import BackupDemand
from .brief import validate_new_brief
from .canonical import Object, digest, encode
from .country_rules import validate_country_rule_inputs
from .equipment_condition_inputs import validate_condition_inputs
from .errors import (
    Conflict,
    EvaluationRevisionChanged,
    InquiryChanged,
    InvalidInput,
    NotFound,
    PreparedHandoff,
    ProjectRevisionNotFound,
    VersionUnavailable,
)
from .execution_control import require_accepting
from .execution_identity import execution_key
from .existing_system import ExistingSystem
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
        temporary_id: str | None = None,
        minimum_free_bytes: int = 0,
    ) -> None:
        self.database = Database(directory / "workspace.sqlite")
        self.blobs = Blobs(
            directory / "blobs",
            temporary_id=temporary_id,
            minimum_free_bytes=minimum_free_bytes,
        )
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
            if "existing_system" in inputs:
                ExistingSystem.read(inputs["existing_system"])
            validate_grid_connection(inputs)
            validate_country_rule_inputs(inputs)
            validate_project_geometry(inputs)
            validate_installation_project(inputs)
            validate_condition_inputs(inputs)
            BackupDemand.from_inputs(inputs)
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
            try:
                return self._project(connection, actor, project_id, revision)
            except NotFound as exc:
                if revision is None:
                    raise
                raise ProjectRevisionNotFound("project revision not found") from exc

    def projects(self, actor: Actor) -> list[Project]:
        with self.database.read() as connection:
            active_actor(connection, actor)
            rows = connection.execute(
                "SELECT id FROM projects WHERE owner=? ORDER BY updated_at DESC, id",
                (actor.key,),
            ).fetchall()
            return [self._project(connection, actor, row["id"]) for row in rows]

    @staticmethod
    def _inquiry_state(
        connection: sqlite3.Connection, project_id: str
    ) -> tuple[bool, int]:
        row = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM handoffs WHERE project_id=?), "
            "COALESCE((SELECT generation FROM inquiry_generations WHERE project_id=?), 0)",
            (project_id, project_id),
        ).fetchone()
        return bool(row[0]), int(row[1])

    @staticmethod
    def advance_inquiry_generation(
        connection: sqlite3.Connection, project_id: str
    ) -> None:
        connection.execute(
            "INSERT INTO inquiry_generations (project_id,generation) VALUES (?,1) "
            "ON CONFLICT(project_id) DO UPDATE SET generation=generation+1",
            (project_id,),
        )

    def admit_project_inquiry(
        self, actor: Actor, project_id: str, revision: int
    ) -> Object:
        with self.database.transaction() as connection:
            try:
                project_row(connection, actor, project_id, write=True)
            except NotFound as exc:
                raise ProjectRevisionNotFound("project revision not found") from exc
            if (
                connection.execute(
                    "SELECT 1 FROM revisions WHERE project_id=? AND number=?",
                    (project_id, revision),
                ).fetchone()
                is None
            ):
                raise ProjectRevisionNotFound("project revision not found")
            self.advance_inquiry_generation(connection, project_id)
            return {"admitted": True}

    def prepared_handoffs(self, actor: Actor, project_id: str) -> Object:
        with self.database.read() as connection:
            project_row(connection, actor, project_id, write=True)
            prepared, generation = self._inquiry_state(connection, project_id)
            return {"has_handoffs": prepared, "inquiry_generation": generation}

    def delete(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        *,
        key: str,
        inquiry_generation: int | None = None,
    ) -> Object:
        positive_integer(expected_revision, "expected revision")
        command = commands.command_hash({"expected_revision": expected_revision}, key)
        scope = f"delete:{project_id}"
        with self.database.transaction() as connection:
            # A retired guest must not read its old receipts. A claimed account
            # is not retired, so it still replays the guest's deletion below
            # without any project row to lean on.
            active_actor(connection, actor)
            receipt = commands.replay(
                connection, self.blobs, actor, scope, key, command
            )
            if receipt is not None:
                return {
                    "project_id": project_id,
                    "revision": commands.receipt_number(receipt, "revision"),
                    "deleted": True,
                }
            project = project_row(connection, actor, project_id, write=True)
            if project["revision"] != expected_revision:
                raise Conflict("project inputs have changed")
            prepared, generation = self._inquiry_state(connection, project_id)
            if inquiry_generation is None:
                if prepared:
                    raise PreparedHandoff(
                        "prepared handoff requires a Woo inquiry check"
                    )
                raise InquiryChanged("project deletion requires a Woo inquiry check")
            if generation != inquiry_generation:
                raise InquiryChanged("inquiry admission changed since the Woo check")
            if prepared:
                connection.execute(
                    "DELETE FROM handoffs WHERE project_id=?", (project_id,)
                )
            now = self.clock()
            connection.execute(
                "UPDATE jobs SET state='cancelled', updated_at=? "
                "WHERE run_id IN (SELECT id FROM runs WHERE project_id=?) "
                "AND state IN ('queued', 'running', 'retry_wait')",
                (now, project_id),
            )
            connection.execute(
                "DELETE FROM evaluation_routes WHERE job_id IN "
                "(SELECT id FROM jobs WHERE run_id IN "
                "(SELECT id FROM runs WHERE project_id=?))",
                (project_id,),
            )
            connection.execute(
                "DELETE FROM artifacts WHERE run_id IN "
                "(SELECT id FROM runs WHERE project_id=?)",
                (project_id,),
            )
            connection.execute(
                "DELETE FROM weather_downloads WHERE run_id IN "
                "(SELECT id FROM runs WHERE project_id=?)",
                (project_id,),
            )
            if (
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='weather_acquisitions'"
                ).fetchone()
                is not None
            ):
                connection.execute(
                    "DELETE FROM weather_acquisitions WHERE run_id IN "
                    "(SELECT id FROM runs WHERE project_id=?)",
                    (project_id,),
                )
            connection.execute(
                "DELETE FROM jobs WHERE run_id IN "
                "(SELECT id FROM runs WHERE project_id=?)",
                (project_id,),
            )
            connection.execute("DELETE FROM runs WHERE project_id=?", (project_id,))
            connection.execute(
                "DELETE FROM project_assets WHERE project_id=?", (project_id,)
            )
            connection.execute(
                "DELETE FROM ownership_transfers WHERE project_id=?", (project_id,)
            )
            connection.execute(
                "DELETE FROM revisions WHERE project_id=?", (project_id,)
            )
            connection.execute("DELETE FROM projects WHERE id=?", (project_id,))
            commands.remember(
                connection,
                self.blobs,
                actor,
                scope,
                key,
                command,
                {"project_id": project_id, "revision": expected_revision},
                now,
            )
            return {
                "project_id": project_id,
                "revision": expected_revision,
                "deleted": True,
            }

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
            if "existing_system" in inputs:
                ExistingSystem.read(inputs["existing_system"])
            validate_grid_connection(inputs)
            validate_country_rule_inputs(inputs)
            validate_project_geometry(inputs)
            validate_installation_project(inputs)
            validate_condition_inputs(inputs)
            BackupDemand.from_inputs(inputs)
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

    def evaluate_inputs(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        resolve: Callable[[], Context],
        *,
        operation: Literal["calculate", "find-equipment", "check-equipment"],
        publish: Callable[[sqlite3.Connection], None] | None = None,
        key: str,
        max_attempts: int,
        input_contract: str | None = None,
    ) -> tuple[Project, Run]:
        """Admit authored inputs and their resolved task in one operation's scope."""
        positive_integer(expected_revision, "expected revision")
        positive_integer(max_attempts, "maximum attempts")
        command = commands.command_hash(
            revise_command(expected_revision, inputs, input_contract=input_contract),
            key,
        )
        scope = f"{operation}:{project_id}"
        with self.database.read() as connection:
            project = project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.blobs, actor, scope, key, command
            )
            if receipt is not None:
                run = self._run(
                    connection, actor, commands.receipt_string(receipt, "run_id")
                )
                return self._project(connection, actor, project_id, run.revision), run
            require_accepting(connection)
            if project["revision"] != expected_revision:
                raise EvaluationRevisionChanged("project inputs have changed")
            previous = self._project(connection, actor, project_id)
            require_input_contract(previous.inputs, inputs, input_contract)
        validate_new_brief(inputs)
        if "existing_system" in inputs:
            ExistingSystem.read(inputs["existing_system"])
        validate_grid_connection(inputs)
        validate_country_rule_inputs(inputs)
        validate_project_geometry(inputs)
        validate_installation_project(inputs)
        validate_condition_inputs(inputs)
        BackupDemand.from_inputs(inputs)
        # Source reads and derivation stage CAS bytes without holding a writer.
        context = resolve()
        with self.database.transaction() as connection:
            project = project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.blobs, actor, scope, key, command
            )
            if receipt is not None:
                run = self._run(
                    connection, actor, commands.receipt_string(receipt, "run_id")
                )
                return self._project(connection, actor, project_id, run.revision), run
            require_accepting(connection)
            if project["revision"] != expected_revision:
                raise EvaluationRevisionChanged("project inputs have changed")
            if publish is not None:
                publish(connection)
            content = self.blobs.put_object(inputs)
            number = expected_revision
            if content != previous.input_sha256:
                number += 1
                now = self.clock()
                connection.execute(
                    "INSERT INTO revisions (project_id, number, input_sha256, created_at) VALUES (?, ?, ?, ?)",
                    (project_id, number, content, now),
                )
                connection.execute(
                    "UPDATE projects SET revision=?, updated_at=? WHERE id=?",
                    (number, now, project_id),
                )
            snapshot = self._project(connection, actor, project_id, number)
            run = self._enqueue(connection, actor, snapshot, context, max_attempts)
            commands.remember(
                connection,
                self.blobs,
                actor,
                scope,
                key,
                command,
                {"run_id": run.id},
                self.clock(),
            )
            return snapshot, run

    def _enqueue(
        self,
        connection: sqlite3.Connection,
        actor: Actor,
        project: Project,
        context: Context,
        max_attempts: int,
    ) -> Run:
        resolved = context.document()
        for sha256 in context.assets.values():
            self.blobs.read(sha256)
        manifest = self.blobs.put_object(
            {
                "schema": 1,
                "project_id": project.id,
                "revision": project.revision,
                "input_sha256": project.input_sha256,
                "context": resolved,
            }
        )
        run_id, job_id, now = uuid4().hex, uuid4().hex, self.clock()
        request = self.blobs.put_object({"manifest_sha256": manifest})
        connection.execute(
            "INSERT INTO runs (id, project_id, revision, manifest_sha256, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, project.id, project.revision, manifest, now),
        )
        connection.execute(
            "INSERT INTO jobs (id, run_id, kind, request_sha256, state, max_attempts, available_at, created_at, updated_at) "
            "VALUES (?, ?, 'evaluate', ?, 'queued', ?, ?, ?, ?)",
            (job_id, run_id, request, max_attempts, now, now, now),
        )
        connection.execute(
            "INSERT INTO evaluation_routes (job_id, schema_version, execution_sha256) VALUES (?, 1, ?)",
            (job_id, execution_key(resolved)),
        )
        return self._run(connection, actor, run_id)

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
            run = self._enqueue(connection, actor, inputs, context, max_attempts)
            commands.remember(
                connection,
                self.blobs,
                actor,
                scope,
                key,
                command,
                {"run_id": run.id},
                self.clock(),
            )
            return run

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
        context = manifest.get("context")
        assets = context.get("assets") if isinstance(context, dict) else None
        if isinstance(assets, dict) and "resolved_inputs" in assets:
            sha = assets["resolved_inputs"]
            if not isinstance(sha, str):
                raise VersionUnavailable("resolved input hash missing")
            resolved = self.blobs.object(sha)
            inputs = resolved.get("inputs")
            if (
                type(resolved.get("schema_version")) is not int
                or resolved["schema_version"] != 1
                or resolved.get("source_input_sha256") != value
                or not isinstance(inputs, dict)
            ):
                raise VersionUnavailable(
                    "resolved execution inputs differ from their authored snapshot"
                )
            return inputs
        return self.blobs.object(value)

    @staticmethod
    def input_hash(inputs: Object) -> str:
        return digest(encode(inputs))

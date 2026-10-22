"""Read existing owned mutation receipts before public admission is charged.

No writes, CSV parsing, new source capture, context compilation or numerical
execution occur here. An absent receipt cannot authorise a mutation: WP still
admits its command, and the actual command repeats ownership/idempotency checks.
"""

from __future__ import annotations

from . import commands
from .access import active_actor, project_row
from .canonical import Object
from .energy_service import EnergyService
from .errors import NotFound
from .http_asset_intake import HttpAssetIntake
from .http_documents import (
    BatteryScenario,
    CsvImport,
    EnergyEvaluate,
    ProjectCreate,
    ProjectRevise,
)
from .http_views import asset_view, project_view, run_view
from .records import Actor
from .workspace import Workspace


class HttpReplay:
    def __init__(
        self, workspace: Workspace, energy: EnergyService, intake: HttpAssetIntake
    ) -> None:
        self.workspace = workspace
        self.energy = energy
        self.intake = intake

    def read(self, actor: Actor, path: str, value: Object) -> Object:
        if actor.kind == "team":
            raise NotFound("mutation receipt not found")
        result: Object | None
        if path == "projects/create":
            create = ProjectCreate.model_validate(value)
            receipt, command_sha256 = self.receipt(
                actor,
                "create",
                create.key,
                {"title": create.title, "inputs": create.inputs},
            )
            result = (
                None
                if receipt is None
                else project_view(
                    self.workspace.get(
                        actor,
                        commands.receipt_string(receipt, "project_id"),
                        revision=1,
                    )
                )
            )
        elif path == "projects/revise":
            revise = ProjectRevise.model_validate(value)
            receipt, command_sha256 = self.receipt(
                actor,
                f"revise:{revise.project_id}",
                revise.key,
                {
                    "expected_revision": revise.expected_revision,
                    "inputs": revise.inputs,
                },
                project_id=revise.project_id,
            )
            result = (
                None
                if receipt is None
                else project_view(
                    self.workspace.get(
                        actor,
                        revise.project_id,
                        revision=commands.receipt_number(receipt, "revision"),
                    )
                )
            )
        elif path == "runs/energy":
            evaluate = EnergyEvaluate.model_validate(value)
            receipt, command_sha256 = self.receipt(
                actor,
                f"evaluate:{evaluate.project_id}",
                evaluate.key,
                {
                    "expected_revision": evaluate.expected_revision,
                    "intent": {"kind": self.energy.kernel.kind},
                },
                project_id=evaluate.project_id,
            )
            result = (
                None
                if receipt is None
                else run_view(
                    self.workspace.run(
                        actor, commands.receipt_string(receipt, "run_id")
                    )
                )
            )
        elif path == "profiles/csv":
            csv = CsvImport.model_validate(value)
            command = self.intake.csv_command(actor, csv)
            command_sha256 = commands.command_hash(command, csv.key)
            asset = self.intake.assets.receipt(actor, csv.project_id, csv.key, command)
            result = None if asset is None else asset_view(asset)
        elif path == "battery/scenario":
            battery = BatteryScenario.model_validate(value)
            command = self.intake.battery_command(battery)
            command_sha256 = commands.command_hash(command, battery.key)
            asset = self.intake.assets.receipt(
                actor, battery.project_id, battery.key, command
            )
            result = None if asset is None else asset_view(asset)
        else:
            raise NotFound("mutation receipt not found")
        return (
            {"schema_version": 1, "status": "absent", "command_sha256": command_sha256}
            if result is None
            else {
                "schema_version": 1,
                "status": "replayed",
                "command_sha256": command_sha256,
                "result": result,
            }
        )

    def receipt(
        self,
        actor: Actor,
        scope: str,
        key: str,
        command: Object,
        *,
        project_id: str | None = None,
    ) -> tuple[Object | None, str]:
        command_sha256 = commands.command_hash(command, key)
        with self.workspace.database.read() as connection:
            active_actor(connection, actor)
            if project_id is not None:
                project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection,
                self.workspace.blobs,
                actor,
                scope,
                key,
                command_sha256,
            )
            return receipt, command_sha256

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
from .equipment_kernel import EquipmentKernel
from .equipment_search_kernel import EquipmentSearchKernel
from .errors import NotFound
from .geometry_import import GeometryImport
from .handoffs import Handoffs
from .http_asset_intake import HttpAssetIntake
from .http_documents import (
    BatteryScenario,
    CsvImport,
    EnergyEvaluate,
    GeometryImportCommand,
    HandoffPrepare,
    ProjectCreate,
    ProjectRevise,
    ReportEvaluate,
)
from .http_views import asset_view, project_view, run_view
from .project_input_contracts import (
    create_command,
    require_input_contract,
    revise_command,
)
from .pv_preparation import PvReferenceKernel
from .pvgis_reference_kernel import PvgisRoofReferenceKernel
from .records import Actor
from .weather_kernel import WeatherKernel
from .workspace import Workspace


class HttpReplay:
    def __init__(
        self,
        workspace: Workspace,
        energy: EnergyService,
        intake: HttpAssetIntake,
        geometry_intake: GeometryImport,
    ) -> None:
        self.workspace = workspace
        self.energy = energy
        self.intake = intake
        self.geometry_intake = geometry_intake

    def read(self, actor: Actor, path: str, value: Object) -> Object:
        if actor.kind == "team":
            raise NotFound("mutation receipt not found")
        result: Object | None
        if path == "projects/create":
            create = ProjectCreate.model_validate(value)
            command_scope = "create"
            receipt, command_sha256 = self.receipt(
                actor,
                command_scope,
                create.key,
                create_command(
                    create.title, create.inputs, input_contract=create.input_contract
                ),
            )
            if receipt is None:
                require_input_contract(None, create.inputs, create.input_contract)
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
            command_scope = f"revise:{revise.project_id}"
            receipt, command_sha256 = self.receipt(
                actor,
                command_scope,
                revise.key,
                revise_command(
                    revise.expected_revision,
                    revise.inputs,
                    input_contract=revise.input_contract,
                ),
                project_id=revise.project_id,
            )
            if receipt is None:
                previous = self.workspace.get(actor, revise.project_id)
                if previous.revision == revise.expected_revision:
                    require_input_contract(
                        previous.inputs, revise.inputs, revise.input_contract
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
        elif path == "handoffs/prepare":
            handoff = HandoffPrepare.model_validate(value)
            command_scope = f"handoff:{handoff.project_id}"
            receipt, command_sha256 = self.receipt(
                actor,
                command_scope,
                handoff.key,
                {
                    "expected_revision": handoff.expected_revision,
                    "report_run_id": handoff.report_run_id,
                },
                project_id=handoff.project_id,
            )
            result = (
                None
                if receipt is None
                else Handoffs(self.workspace).read(
                    actor, commands.receipt_string(receipt, "handoff_id")
                )
            )
        elif path == "runs/report":
            report = ReportEvaluate.model_validate(value)
            command_scope = f"evaluate:{report.project_id}"
            receipt, command_sha256 = self.receipt(
                actor,
                command_scope,
                report.key,
                {
                    "expected_revision": report.expected_revision,
                    "intent": report.options.intent(),
                },
                project_id=report.project_id,
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
        elif path in (
            "runs/energy",
            "runs/pv",
            "runs/pvgis-reference",
            "runs/weather",
            "runs/equipment",
            "runs/equipment-search",
        ):
            evaluate = EnergyEvaluate.model_validate(value)
            command_scope = f"evaluate:{evaluate.project_id}"
            receipt, command_sha256 = self.receipt(
                actor,
                command_scope,
                evaluate.key,
                {
                    "expected_revision": evaluate.expected_revision,
                    "intent": {
                        "kind": self.energy.kind_for(
                            actor, evaluate.project_id, evaluate.expected_revision
                        )
                        if path == "runs/energy"
                        else PvReferenceKernel.kind
                        if path == "runs/pv"
                        else PvgisRoofReferenceKernel.kind
                        if path == "runs/pvgis-reference"
                        else EquipmentKernel.kind
                        if path == "runs/equipment"
                        else EquipmentSearchKernel.kind
                        if path == "runs/equipment-search"
                        else WeatherKernel.kind
                    },
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
            command_scope = f"asset:{csv.project_id}"
            command = self.intake.csv_command(actor, csv)
            command_sha256 = commands.command_hash(command, csv.key)
            asset = self.intake.assets.receipt(actor, csv.project_id, csv.key, command)
            result = None if asset is None else asset_view(asset)
        elif path == "geometry/import":
            geometry = GeometryImportCommand.model_validate(value)
            self.intake.assets.check_write(actor, geometry.project_id)
            content = self.geometry_intake.decode(geometry.content_base64)
            command_scope = f"asset:{geometry.project_id}"
            command = self.geometry_intake.command(content, geometry.options)
            command_sha256 = commands.command_hash(command, geometry.key)
            asset = self.geometry_intake.previous(
                actor, geometry.project_id, content, geometry.options, key=geometry.key
            )
            result = None if asset is None else asset_view(asset)
        elif path == "battery/scenario":
            battery = BatteryScenario.model_validate(value)
            command_scope = f"asset:{battery.project_id}"
            command = self.intake.battery_command(battery)
            command_sha256 = commands.command_hash(command, battery.key)
            asset = self.intake.assets.receipt(
                actor, battery.project_id, battery.key, command
            )
            result = None if asset is None else asset_view(asset)
        else:
            raise NotFound("mutation receipt not found")
        reply: Object = {
            "schema_version": 1,
            "status": "absent" if result is None else "replayed",
            "command_scope": command_scope,
            "command_sha256": command_sha256,
        }
        if result is not None:
            reply["result"] = result
        return reply

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

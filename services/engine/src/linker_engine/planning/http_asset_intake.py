"""One construction of the user-declared asset command for intake and replay."""

from __future__ import annotations

import base64
import binascii
from typing import cast

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .csv_mapping import CsvMapping
from .dc_energy_parameters import DcLossScenario
from .dc_parameter_source import prepare_dc_parameters
from .equipment_plant import EquipmentPlant
from .errors import InvalidInput
from .http_documents import BatteryScenario, CsvImport, StandardProfile
from .load_profile import expand, to_csv
from .power_series import Measurement
from .product_sources import ProductSources
from .profile_import import ProfileImport
from .records import Actor
from .timezone_rules import require_iana_timezone


class HttpAssetIntake:
    def __init__(
        self,
        assets: Assets,
        *,
        max_csv_bytes: int,
        products: ProductSources | None = None,
    ) -> None:
        self.assets = assets
        self.max_csv_bytes = max_csv_bytes
        self.products = products

    def csv_content(self, actor: Actor, body: CsvImport) -> bytes:
        self.assets.check_write(actor, body.project_id)
        return self.decode_csv(body.content_base64)

    def decode_csv(self, content_base64: str) -> bytes:
        try:
            content = base64.b64decode(content_base64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise InvalidInput("CSV must be valid base64") from error
        if len(content) > self.max_csv_bytes:
            raise InvalidInput("CSV exceeds deployment file limit")
        return content

    @staticmethod
    def csv_provenance(body: CsvImport) -> Object:
        # User declaration, not proof of measured data/provider retention rights.
        return {
            "label": body.source_label,
            "basis": "user_upload_declaration",
            "rights_basis": body.rights_note,
        }

    def csv(self, actor: Actor, body: CsvImport) -> Asset:
        return ProfileImport(self.assets).csv(
            actor,
            body.project_id,
            self.csv_content(actor, body),
            body.mapping.mapping(),
            self.csv_provenance(body),
            key=body.key,
        )

    def previous_csv(self, actor: Actor, body: CsvImport) -> Asset | None:
        return self.assets.receipt(
            actor, body.project_id, body.key, self.csv_command(actor, body)
        )

    def csv_command(self, actor: Actor, body: CsvImport) -> Object:
        return ProfileImport.command(
            self.csv_content(actor, body),
            body.mapping.mapping(),
            self.csv_provenance(body),
        )

    def standard_materials(
        self, actor: Actor, body: StandardProfile
    ) -> tuple[bytes, CsvMapping, Object]:
        self.assets.check_write(actor, body.project_id)
        # A zone key that ZoneInfo cannot resolve must be intake rejection, not
        # a 500 from the expansion's first calendar lookup.
        require_iana_timezone(body.timezone)
        expanded = expand(
            body.edition,
            body.profile,
            year=body.year,
            annual_kwh=body.annual_kwh,
            timezone=body.timezone,
        )
        content = to_csv(expanded, body.timezone)
        if len(content) > self.max_csv_bytes:
            raise InvalidInput("expanded profile exceeds deployment file limit")
        mapping = CsvMapping(
            "time",
            "power",
            cast(Measurement, expanded.measurement_role),
            "interval_average_kw",
            "start",
            body.timezone,
            "template",
            900,
            ",",
            ".",
        )
        return content, mapping, cast(Object, expanded.provenance())

    def standard(self, actor: Actor, body: StandardProfile) -> Asset:
        command = self.standard_command(body)
        previous = self.assets.receipt(actor, body.project_id, body.key, command)
        if previous is not None:
            return previous
        content, mapping, provenance = self.standard_materials(actor, body)
        return ProfileImport(self.assets).csv(
            actor,
            body.project_id,
            content,
            mapping,
            provenance,
            key=body.key,
            receipt_command=command,
        )

    @staticmethod
    def standard_command(body: StandardProfile) -> Object:
        return {
            "standard_profile": cast(
                Object, body.model_dump(mode="json", exclude={"key"})
            ),
        }

    @staticmethod
    def battery_content(body: BatteryScenario) -> bytes:
        # Preserve an older durable request's exact parameter shape when an
        # additive optional condition was absent. New explicit fields retain
        # their null/value; they are never backfilled into an old command hash.
        return encode(body.parameters.model_dump(mode="json", exclude_unset=True))

    @staticmethod
    def battery_metadata(body: BatteryScenario) -> Object:
        return {
            "retention": "permanent",
            "provenance": {
                "label": body.source_note,
                "basis": "user_explicit_scenario_not_equipment_release",
                "rights_basis": "user-declared numeric scenario, no third-party provider asset",
            },
            **(
                {"derived_from_revision": body.expected_revision}
                if isinstance(body.parameters, DcLossScenario)
                else {}
            ),
            **(
                {"equipment_unit_id": body.equipment_unit_id}
                if body.equipment_unit_id is not None
                else {}
            ),
        }

    def battery(self, actor: Actor, body: BatteryScenario) -> Asset:
        previous = self.previous_battery(actor, body)
        if previous is not None:
            return previous
        metadata = self.battery_metadata(body)
        if isinstance(body.parameters, DcLossScenario):
            if self.products is None or body.expected_revision is None:
                raise InvalidInput(
                    "current Woo source is required for DC parameter preparation"
                )
            project = self.assets.workspace.get(
                actor, body.project_id, revision=body.expected_revision
            )
            basis = self.products.equipment_basis()
            selected = project.inputs
            if body.equipment_unit_id is not None:
                plant = EquipmentPlant.from_inputs(project.inputs)
                unit = next(
                    (unit for unit in plant.units if unit.id == body.equipment_unit_id),
                    None,
                )
                if unit is None:
                    raise InvalidInput(
                        "the parameter request must name a prepared plant unit"
                    )
                selected = {
                    key: value
                    for key, value in project.inputs.items()
                    if key
                    not in {
                        "equipment_plant",
                        "equipment_plant_setup",
                        "equipment_plant_requirements",
                        "equipment_candidate",
                    }
                }
                selected["equipment_selection"] = unit.selection.model_dump(mode="json")
            prepared = prepare_dc_parameters(selected, basis, body.parameters)
            self.products.confirm_basis(basis, require_reference=False)
            metadata = {
                **metadata,
                "dependencies": {
                    "dc_prepared_parameters": self.assets.workspace.blobs.put_object(
                        prepared.model_dump(mode="json")
                    ),
                    "dc_woo_inputs": self.assets.workspace.blobs.put_object(basis),
                },
            }
        return self.assets.add(
            actor,
            body.project_id,
            self.battery_content(body),
            "application/json",
            "battery_parameters_v1",
            metadata,
            key=body.key,
            logical_metadata=self.battery_metadata(body),
        )

    def previous_battery(self, actor: Actor, body: BatteryScenario) -> Asset | None:
        return self.assets.receipt(
            actor, body.project_id, body.key, self.battery_command(body)
        )

    @classmethod
    def battery_command(cls, body: BatteryScenario) -> Object:
        return {
            "content_sha256": digest(cls.battery_content(body)),
            "media_type": "application/json",
            "purpose": "battery_parameters_v1",
            "metadata": cls.battery_metadata(body),
        }

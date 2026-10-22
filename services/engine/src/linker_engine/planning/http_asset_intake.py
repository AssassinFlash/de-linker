"""One construction of the user-declared asset command for intake and replay."""

from __future__ import annotations

import base64
import binascii

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .errors import InvalidInput
from .http_documents import BatteryScenario, CsvImport
from .profile_import import ProfileImport
from .records import Actor


class HttpAssetIntake:
    def __init__(self, assets: Assets, *, max_csv_bytes: int) -> None:
        self.assets = assets
        self.max_csv_bytes = max_csv_bytes

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

    @staticmethod
    def battery_content(body: BatteryScenario) -> bytes:
        return encode(body.parameters.model_dump(mode="json"))

    @staticmethod
    def battery_metadata(body: BatteryScenario) -> Object:
        return {
            "retention": "permanent",
            "provenance": {
                "label": body.source_note,
                "basis": "user_explicit_scenario_not_equipment_release",
                "rights_basis": "user-declared numeric scenario, no third-party provider asset",
            },
        }

    def battery(self, actor: Actor, body: BatteryScenario) -> Asset:
        return self.assets.add(
            actor,
            body.project_id,
            self.battery_content(body),
            "application/json",
            "battery_parameters_v1",
            self.battery_metadata(body),
            key=body.key,
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

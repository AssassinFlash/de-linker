"""A downloaded original and safe exact evidence, not an owned publication."""

from dataclasses import dataclass

from .canonical import Object
from .pv_source import PvSource
from .storage import Blobs


@dataclass(frozen=True)
class WeatherDownload:
    source: PvSource
    submitted_input_json: bytes
    effective_input_json: bytes
    selected_dataset_record_json: bytes
    transport_json: bytes

    def retain_evidence(self, blobs: Blobs) -> Object:
        return {
            "schema_version": 1,
            "kind": "apify_weather_transport_evidence_v1",
            "dataset_retention": "selected_record_without_temporary_access_query",
            "dependencies": {
                "submitted_input_original": blobs.put(self.submitted_input_json),
                "effective_input_original": blobs.put(self.effective_input_json),
                "selected_dataset_record": blobs.put(self.selected_dataset_record_json),
                "transport_receipts": blobs.put(self.transport_json),
            },
        }

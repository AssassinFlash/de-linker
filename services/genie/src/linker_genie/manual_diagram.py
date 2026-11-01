"""Stable identity of a physically reviewed manufacturer figure."""

from collections.abc import Mapping
from typing import Any


def physical_descriptor(record: Mapping[str, Any]) -> dict[str, Any]:
    """Exact source rectangle and reviewed pixels, independent of OCR order."""
    return {
        "kind": "manual_diagram",
        "target_chunk_id": record["source_id"],
        "source_sha256": record["sha256"],
        "source_page": record["source_page"],
        "figure": record["figure"],
        "bbox": record["bbox"],
        "scale": 2,
        "pixel_size": record["pixel_size"],
        "pixel_sha256": record["pixel_sha256"],
    }


def model_list_descriptor(record: Mapping[str, Any]) -> dict[str, Any]:
    """The separately reviewed visible manufacturer model list on page one."""
    return {
        "kind": "manual_model_list",
        "target_chunk_id": record["anchor_id"],
        "source_sha256": record["sha256"],
        "source_page": 1,
        "figure": record["anchor_figure"],
        "bbox": record["anchor_bbox"],
        "scale": 2,
        "pixel_size": record["anchor_pixel_size"],
        "pixel_sha256": record["anchor_pixel_sha256"],
    }

"""Explicit saved analyses and optional customer branding for one report."""

from __future__ import annotations

import base64
import binascii
import io
import re
import warnings
from typing import Annotated, Literal

from PIL import Image
from pydantic import Field, model_validator

from .canonical import Object, digest, encode
from .energy_inputs import Document
from .errors import InvalidInput

type RunId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
# Existing report-upload resource policy: 500 kB, before base64 transport.
LOGO_BYTES = 500_000
_LOGO = re.compile(r"^data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)$")


class InvalidReportLogo(InvalidInput):
    code = "report_logo_invalid"


class ComparisonSelection(Document):
    baseline_run_id: RunId
    candidate_run_id: RunId

    @model_validator(mode="after")
    def distinct_runs(self) -> ComparisonSelection:
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("choose two different saved calculations")
        return self


class ReportOptions(Document):
    locale: Literal["en", "de"]
    energy_run_id: RunId | None
    pv_run_id: RunId | None
    equipment_run_id: RunId | None
    logo: Annotated[str, Field(max_length=700_000)] | None
    comparison: ComparisonSelection | None = None

    def intent(self) -> Object:
        options = self.model_dump(mode="json")
        # The additive empty comparison does not change historical receipts,
        # including the normalized body used by the native replay adapter.
        if self.comparison is None:
            options.pop("comparison")
        return {
            "kind": "planning_report_v1",
            "options_sha256": digest(encode(options)),
        }

    def logo_bytes(self) -> bytes | None:
        if self.logo is None:
            return None
        match = _LOGO.fullmatch(self.logo)
        if match is None:
            raise InvalidReportLogo("report logo must be a PNG or JPEG data URL")
        try:
            raw = base64.b64decode(match[2], validate=True)
            if not raw or len(raw) > LOGO_BYTES:
                raise ValueError("logo exceeds the upload policy")
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    expected = "PNG" if match[1] == "png" else "JPEG"
                    if image.format != expected or min(image.size) <= 0:
                        raise ValueError("logo format differs from its media type")
                    image.verify()
        except (
            binascii.Error,
            OSError,
            ValueError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ) as error:
            raise InvalidReportLogo(
                "report logo is invalid or exceeds the upload policy"
            ) from error
        return raw

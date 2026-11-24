"""Request and response bodies of the HTTP API.

The JSON Schemas of the requests are exported to `schemas/api/` and into the
configurator (scripts/export_schemas.py); the configurator validates its form
against them, so the rules of an input exist once.
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Locale = Literal["en", "de"]
Backup = Literal["none", "needed", "needed_accessory_ok"]
# A European postcode as the country writes it: `10115`, `75001`, `M1 1AE`,
# `D1`, `3750-000`, `59-700`. The shape check only rejects what no country
# writes; whether the postcode names a place is the lookup's answer, not a
# pattern's (measured 2026-11-15: this used to accept five digits only, so a
# British or Dutch project could not be described at all).
Plz = Annotated[
    str,
    Field(
        min_length=2,
        max_length=12,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 -]*$",
        description="European postcode (PLZ) as its country writes it",
    ),
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


PositiveMeasurement = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class PanelDimensions(Strict):
    """Declared panel dimensions and rated power for a roof packing calculation."""

    pmax_w: PositiveMeasurement
    length_m: PositiveMeasurement
    width_m: PositiveMeasurement


class PanelElectrical(Strict):
    """Declared panel values used by a string design, independent of stock."""

    pmax_w: PositiveMeasurement
    voc_v: PositiveMeasurement
    vmpp_v: PositiveMeasurement
    isc_a: PositiveMeasurement
    impp_a: PositiveMeasurement
    beta_voc_pct_per_c: Annotated[float, Field(le=0, allow_inf_nan=False)]
    max_series_fuse_a: PositiveMeasurement


class PlaneInput(Strict):
    """One roof plane of the array. Without planes the array is one plane at the default tilt and facing."""

    kwp: Annotated[float, Field(gt=0, le=100)]
    tilt_deg: Annotated[float, Field(ge=0, le=90)]
    azimuth_deg: Annotated[
        float,
        Field(
            ge=0, lt=360, description="Facing: north 0, east 90, south 180, west 270"
        ),
    ]


# Geographic Europe in WGS84, rounded outwards to include its islands: the
# Canaries reach 27.6 N, the Azores 31.3 W, the North Cape 71.2 N, and the
# Caspian edge of the continent 46.7 E. The site sells into every European
# country it lists, so a Greek or Portuguese position is a normal project, not
# a typing error (measured 2026-11-15: this used to be Germany's own extent,
# 47.0-55.2 N by 5.8-15.1 E, which refused Athens and Lisbon outright).
LATITUDE = Field(ge=27.0, le=71.5)
LONGITUDE = Field(ge=-32.0, le=47.0)
# A drawn plane larger than this is no roof plane of a building this tool plans;
# the bound also caps the packing work of one request.
MAX_DRAWN_PLANE_M2 = 3000.0


class Location(Strict):
    latitude: Annotated[float, LATITUDE]
    longitude: Annotated[float, LONGITUDE]


class ResidentialInput(Strict):
    module: PanelElectrical | None = None
    locale: Locale = "en"
    plz: Plz
    # The postcode alone is not unique across Europe — 80538 is both Munich and
    # a Ukrainian code, 10115 both Berlin and Tallinn — so the country is what
    # makes the site a place. Measured 2026-11-15: without it the design refused
    # the German home market's own postcodes.
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    annual_kwh: Annotated[
        float,
        Field(
            ge=500,
            le=50000,
            description="Annual household consumption. The bounds only reject typing errors; "
            "where the methods are valid is checked and reported separately.",
        ),
    ]
    pv_kwp: Annotated[float, Field(gt=0, le=100)]
    planes: list[PlaneInput] | None = None
    location: Location | None = Field(
        default=None,
        description="The roof's position from the roof step; otherwise the PLZ centre.",
    )
    roof_source: Literal["lod2", "drawn"] | None = Field(
        default=None,
        description="Where the planes come from: the state's official LoD2 building model "
        "(the report credits it under its licence) or drawn by hand on the aerial image.",
    )
    phase: Literal[1, 3]
    backup: Backup = "none"
    backup_load_kw: Annotated[float, Field(gt=0, le=50)] | None = None
    backup_hours: Annotated[float, Field(gt=0, le=72)] | None = None
    heat_pump: bool = False
    electric_vehicle: bool = False
    existing_inverter: Annotated[str, Field(max_length=80)] | None = Field(
        default=None, description="Model of an inverter already installed (retrofit)."
    )
    inverter_id: int | None = Field(
        default=None, description="Swap: use this inverter."
    )
    battery_id: int | None = Field(default=None, description="Swap: use this battery.")

    @model_validator(mode="after")
    def planes_add_up(self) -> ResidentialInput:
        if self.planes and abs(sum(p.kwp for p in self.planes) - self.pv_kwp) > 0.01:
            raise ValueError("the planes' kWp must add up to pv_kwp")
        if self.roof_source and not self.planes:
            raise ValueError("roof_source describes planes; send the planes with it")
        return self


class Range(BaseModel):
    low: float
    high: float


class Doc(BaseModel):
    url: str
    page: int | None = None


class RuleResult(BaseModel):
    id: str
    passed: bool | None = Field(
        description="None: a limit that is reported, not tested"
    )
    value: float | str | None
    limit: float | str | None = None
    label: str
    text: str = Field(description="The value in words, in the request's language")


class YieldResult(BaseModel):
    kwh_year_range: Range
    kwh_per_kwp_range: Range
    kwh_year_mean: float
    monthly_kwh: list[float]
    years: tuple[int, int]
    planes: list[PlaneInput]
    latitude: float
    longitude: float
    source: str


class StorageResult(BaseModel):
    recommended: bool
    usable_kwh_range: Range | None
    upper_kwh: float
    backup_reserve_kwh: float
    basis: list[RuleResult]


class MetricsResult(BaseModel):
    usable_kwh: float
    autarky_range: Range
    self_consumption_range: Range
    without_storage_autarky_range: Range
    without_storage_self_consumption_range: Range
    basis: str


class ProductRef(BaseModel):
    id: int
    sku: str
    model: str
    brand: str
    device_class: str


class Release(BaseModel):
    verdict: Literal["released", "released_with_accessory", "not_released", "unknown"]
    conditions: list[str]
    documents: list[Doc]


Role = Literal[
    "inverter",
    "battery",
    "accessory",
    "meter",
    "backup",
    "controller",
    "pv_module",
    "mounting",
    "dc_cable",
    "connector",
    "string_fuse",
    "ac_protection",
]


class Line(BaseModel):
    """One Stückliste line. Lines with a product are ours; the others are the installer's scope."""

    role: Role
    product: ProductRef | None
    quantity: float | None
    unit: Literal["pcs", "m", "pairs", "set"]
    label: str
    basis: list[str]
    documents: list[Doc]


class StringGroup(BaseModel):
    mppt: int
    strings: int
    modules_per_string: int
    fuses: int


class StringLayoutResult(BaseModel):
    module: str
    module_wp: float
    modules_per_string: int
    module_count: int
    array_kwp: float
    voc_cold_v: float
    vmp_hot_v: float
    groups: list[StringGroup]


class BatteryChoice(BaseModel):
    product: ProductRef
    quantity: int
    stacks: int
    usable_kwh: float
    above_upper_limit: bool
    release: Release


class Selection(BaseModel):
    inverter: ProductRef
    inverter_rules: list[RuleResult]
    battery: BatteryChoice | None
    strings: StringLayoutResult | None = Field(
        description="None for a retrofit: the array exists"
    )
    lines: list[Line]


class CandidateInverter(BaseModel):
    product: ProductRef
    ac_power_kw: float | None
    battery: BatteryChoice | None


class Excluded(BaseModel):
    product: ProductRef
    failed: list[RuleResult]


class Candidates(BaseModel):
    inverters: list[CandidateInverter]
    batteries: list[BatteryChoice]
    accessories: list[ProductRef]
    excluded: list[Excluded]


class ReportRow(BaseModel):
    label: str
    value: str
    href: str | None = None  # a document on de-linker.com the value names


class ReportTable(BaseModel):
    columns: list[str]
    rows: list[list[str]]
    # Relative presentation widths. These are document layout, not engineering
    # quantities; absent hints retain the existing bill-of-materials layout.
    column_weights: list[Annotated[float, Field(gt=0, allow_inf_nan=False)]] | None = (
        None
    )

    @model_validator(mode="after")
    def matching_column_weights(self) -> ReportTable:
        if self.column_weights is not None and len(self.column_weights) != len(
            self.columns
        ):
            raise ValueError("table layout must name every column")
        return self


class ReportSummaryCard(BaseModel):
    label: str
    value: str
    note: str | None = None


class ReportMonthlyChart(BaseModel):
    title: str
    unit: str
    months: list[str] = Field(min_length=12, max_length=12)
    pv_kwh: list[Annotated[float, Field(ge=0, allow_inf_nan=False)]] = Field(
        min_length=12, max_length=12
    )
    load_kwh: list[Annotated[float, Field(ge=0, allow_inf_nan=False)]] | None = Field(
        default=None, min_length=12, max_length=12
    )
    source_note: str


class ReportSection(BaseModel):
    tier: Literal["commercial", "appendix"] = "commercial"
    id: str
    title: str
    rows: list[ReportRow] = []
    paragraphs: list[str] = []
    table: ReportTable | None = None


class ReportPhaseConflict(BaseModel):
    unit: str | None
    actual: Literal[1, 3]
    required: Literal[1, 3]


class Report(BaseModel):
    title: str
    subtitle: str
    generated_at: str
    locale: Locale
    sections: list[ReportSection]
    summary_cards: list[ReportSummaryCard] = Field(default_factory=list)
    monthly_chart: ReportMonthlyChart | None = None
    phase_conflicts: list[ReportPhaseConflict] = Field(
        default_factory=list, exclude_if=lambda conflicts: not conflicts
    )


class ResidentialResult(BaseModel):
    publication: dict[str, Any] | None = None
    selection_fingerprint: str | None = None
    status: Literal["solution", "no_candidate"]
    yield_: YieldResult = Field(alias="yield")
    storage: StorageResult
    metrics: MetricsResult | None
    selected: Selection | None
    candidates: Candidates
    rules: list[RuleResult]
    warnings: list[str]
    relaxations: list[str]
    report: Report

    model_config = ConfigDict(populate_by_name=True)


# Postcodes and imagery -----------------------------------------------------------------


class Imagery(BaseModel):
    tiles: list[str]
    credit: str
    licence: str
    licence_url: str


class PlaceResult(BaseModel):
    plz: str
    latitude: float
    longitude: float
    state: str
    place: str
    attribution: str
    imagery: Imagery | None
    # The site's own facts. Every answer names the country, region and civil
    # time it resolved to; nothing inherits Germany's. Where an official
    # outline or aerial service exists, `state` and `imagery` carry it.
    country: str
    region: str
    timezone: str


# Roof step --------------------------------------------------------------------------------


class RoofRequest(Strict):
    module: PanelDimensions
    plz: Plz
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    location: Location
    locale: Locale = "en"


class RoofPackRequest(Strict):
    """A roof plane drawn by hand where no official outline is available."""

    module: PanelDimensions

    polygon: Annotated[
        list[tuple[Annotated[float, LONGITUDE], Annotated[float, LATITUDE]]],
        Field(min_length=3, max_length=200),
    ] = Field(description="Ring as [longitude, latitude] pairs")
    tilt_deg: Annotated[float, Field(ge=0, le=90)]
    azimuth_deg: Annotated[float, Field(ge=0, lt=360)]
    locale: Locale = "en"

    @model_validator(mode="after")
    def roof_sized(self) -> RoofPackRequest:
        # Plan area on a local equirectangular projection; exact enough for a bound.
        mean = math.radians(sum(lat for _, lat in self.polygon) / len(self.polygon))
        points = [
            (lon * 111_320 * math.cos(mean), lat * 110_540) for lon, lat in self.polygon
        ]
        twice = sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True)
        )
        if abs(twice) / 2 > MAX_DRAWN_PLANE_M2:
            raise ValueError(
                f"a drawn plane covers at most {MAX_DRAWN_PLANE_M2:.0f} m²"
            )
        return self


class RoofPlaneResult(BaseModel):
    publication: dict[str, Any] | None = None
    id: int
    polygon: list[tuple[float, float]] = Field(
        description="Ring as [longitude, latitude] pairs"
    )
    tilt_deg: float
    azimuth_deg: float
    area_m2: float
    usable: bool
    excluded_reason: str | None
    modules: int
    kwp: float
    module_polygons: list[list[tuple[float, float]]]


class RoofResult(BaseModel):
    publication: dict[str, Any] | None = None
    found: bool
    building_id: str | None
    address: str | None
    distance_m: float | None
    outline: list[list[tuple[float, float]]]
    planes: list[RoofPlaneResult]
    modules: int
    kwp: float
    module: str
    module_wp: float
    source: str
    licence: str
    assumptions: list[str]


# Report -------------------------------------------------------------------------------------


class ReportRequest(Strict):
    selection_fingerprint: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    input: ResidentialInput
    logo: str | None = Field(
        default=None,
        max_length=700_000,
        description="Logo for the report header as a data URL (image/png or image/jpeg, at most about 500 kB).",
    )


# Commercial and industrial ---------------------------------------------------------------

Goal = Literal["peak_shaving", "self_consumption", "backup"]


class Site(Strict):
    installation: Literal["indoor", "outdoor", "unknown"] = "unknown"
    notes: Annotated[str, Field(max_length=500)] = ""


class CommercialInput(Strict):
    locale: Locale = "en"
    plz: Plz
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    grid_connection_kva: Annotated[float, Field(gt=0, le=10000)]
    annual_kwh: Annotated[float, Field(gt=0, le=100_000_000)]
    goals: Annotated[list[Goal], Field(min_length=1)]
    peak_kw: Annotated[float, Field(gt=0, le=10000)] | None = None
    target_peak_kw: Annotated[float, Field(gt=0, le=10000)] | None = None
    pv_kwp: Annotated[float, Field(gt=0, le=10000)] | None = None
    backup_load_kw: Annotated[float, Field(gt=0, le=10000)] | None = None
    backup_hours: Annotated[float, Field(gt=0, le=72)] | None = None
    load_profile_csv: Annotated[str, Field(max_length=4_000_000)] | None = Field(
        default=None,
        description="15-minute load profile: one value per line, optionally after a timestamp",
    )
    load_profile_unit: Literal["kW", "kWh"] = "kW"
    site: Site = Site()


class LoadSummary(BaseModel):
    intervals: int
    days: float
    annual_kwh: float
    peak_kw: float
    base_kw: float
    full_load_hours: float
    duration_curve_kw: list[float]


class ShavingOption(BaseModel):
    cap_kw: float
    power_kw: float
    energy_kwh: float
    events: int


class CommercialSystem(BaseModel):
    inverter: ProductRef
    inverter_units: int
    battery: ProductRef | None
    battery_units: int
    usable_kwh: float
    power_kw: float
    release: Release | None
    lines: list[Line]


class CommercialResult(BaseModel):
    publication: dict[str, Any] | None = None
    selection_fingerprint: str | None = None
    status: Literal["sized", "indicative"]
    load: LoadSummary | None
    options: list[ShavingOption]
    power_kw_range: Range | None
    energy_kwh_range: Range | None
    basis: list[str]
    systems: list[CommercialSystem]
    warnings: list[str]
    inquiry: str


class SelectionRequest(Strict):
    kind: Literal["residential", "commercial"]
    input: ResidentialInput | CommercialInput
    selection_fingerprint: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

"""Request and response bodies of the HTTP API.

The JSON Schemas of these models are exported to `schemas/` (see
`linker_engine.schema_export`); the configurator validates its form against
the exported request schema, so the rules of an input exist once.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Locale = Literal["en", "de"]
Backup = Literal["none", "needed", "needed_accessory_ok"]
Plz = Annotated[str, Field(pattern=r"^\d{5}$", description="German postcode (PLZ)")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class Location(Strict):
    latitude: Annotated[float, Field(ge=47.0, le=55.2)]
    longitude: Annotated[float, Field(ge=5.8, le=15.1)]


class ResidentialInput(Strict):
    locale: Locale = "en"
    plz: Plz
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
    quantity: float
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


class ReportSection(BaseModel):
    id: str
    title: str
    rows: list[ReportRow] = []
    paragraphs: list[str] = []
    table: ReportTable | None = None


class Report(BaseModel):
    title: str
    subtitle: str
    generated_at: str
    locale: Locale
    sections: list[ReportSection]


class ResidentialResult(BaseModel):
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


# Roof step --------------------------------------------------------------------------------


class RoofRequest(Strict):
    plz: Plz
    location: Location
    locale: Locale = "en"


class RoofPackRequest(Strict):
    """A roof plane drawn by hand where no official outline is available."""

    polygon: Annotated[
        list[tuple[float, float]], Field(min_length=3, max_length=200)
    ] = Field(description="Ring as [longitude, latitude] pairs")
    tilt_deg: Annotated[float, Field(ge=0, le=90)]
    azimuth_deg: Annotated[float, Field(ge=0, lt=360)]
    locale: Locale = "en"


class RoofPlaneResult(BaseModel):
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
    status: Literal["sized", "indicative"]
    load: LoadSummary | None
    options: list[ShavingOption]
    power_kw_range: Range | None
    energy_kwh_range: Range | None
    basis: list[str]
    systems: list[CommercialSystem]
    warnings: list[str]
    inquiry: str

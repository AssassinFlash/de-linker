"""Every number the engine decides with, in one place, each with its source.

A rule whose value is not backed by a source is marked
`verified=False`: it is an "unverified planning assumption" and the design
report lists it under assumptions (docs/specs/14-solution-configurator.md,
"常量集中 rules.py"). Sources were read through Apify on 2026-10-09; the
evidence records are the files named in `evidence`.
"""

from __future__ import annotations

from dataclasses import dataclass

PLANNER = "docs/research/2026-10-09/planner-methods.md"
TICKET = "docs/specs/14-solution-configurator.md"
# The Apify runs that read each source, with the passage each rule rests on.
SOURCES = "docs/acceptance/2026-10-09/14/sources.md"


@dataclass(frozen=True)
class Rule:
    id: str
    value: float
    unit: str
    source: str
    evidence: str
    verified: bool = True


# Storage sizing: HTW Berlin, Orth/Weniger/Meissner, "Empfehlungen zur Auslegung von
# Solarstromspeichern", Sonnenenergie 02/2022.
HTW_PAPER = (
    "https://solar.htw-berlin.de/publikationen/auslegung-von-solarstromspeichern/"
)
HTW_FAQ = "https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/"

HTW_MIN_KWP_PER_MWH = Rule(
    "htw_min_pv",
    0.5,
    "kWp per MWh/a",
    f"HTW Berlin storage sizing recommendations (rule: PV at least 0.5 kW per MWh/a, otherwise no storage), {HTW_PAPER}",
    f"{PLANNER} §2.2(b)",
)
HTW_MAX_KWH_PER_KWP = Rule(
    "htw_max_per_kwp",
    1.5,
    "kWh usable per kWp",
    f"HTW Berlin storage sizing recommendations (usable capacity at most 1.5 kWh per kW PV), {HTW_PAPER}",
    f"{PLANNER} §2.2(b)",
)
HTW_MAX_KWH_PER_MWH = Rule(
    "htw_max_per_mwh",
    1.5,
    "kWh usable per MWh/a",
    f"HTW Berlin storage sizing recommendations (usable capacity at most 1.5 kWh per MWh/a), {HTW_PAPER}",
    f"{PLANNER} §2.2(b)",
)
HTW_DISCHARGE_EFFICIENCY = Rule(
    "htw_discharge_efficiency",
    0.94,
    "fraction",
    f"HTW Unabhängigkeitsrechner battery model: charge and discharge 94 % each, {HTW_FAQ}",
    f"{PLANNER} §2.2(b)",
)

HTW_REFERENCE_YIELD = Rule(
    "htw_reference_yield",
    1024.0,
    "kWh per kWp and year",
    f"HTW Unabhängigkeitsrechner: PV yield behind its tables, 35° south, {HTW_FAQ}",
    SOURCES,
)
HTW_HOUSEHOLD_SPREAD_PP = Rule(
    "htw_household_spread",
    5.0,
    "percentage points",
    "HTW Berlin, Studie Dezentrale Solarstromspeicher (2015): most households deviate by less than "
    "5 percentage points from the mean self-sufficiency, "
    "https://solar.htw-berlin.de/wp-content/uploads/HTW-Studie-Dezentrale-Solarstromspeicher.pdf",
    SOURCES,
)
HEAT_PUMP_KWH_LOW = Rule(
    "heat_pump_low",
    2664.0,
    "kWh per year",
    "HTW Berlin, Stromspeicher-Inspektion 2021: four measured heat pumps used 2664 to 4011 kWh/a, "
    "https://solar.htw-berlin.de/wp-content/uploads/HTW-Stromspeicher-Inspektion-2021.pdf",
    SOURCES,
)
HEAT_PUMP_KWH_HIGH = Rule(
    "heat_pump_high",
    4011.0,
    "kWh per year",
    HEAT_PUMP_KWH_LOW.source,
    HEAT_PUMP_KWH_LOW.evidence,
)
EV_KWH_LOW = Rule(
    "ev_low",
    1551.0,
    "kWh per year",
    "HTW Berlin, Solares Laden von Elektrofahrzeugen (2025, 730 homes): half of the homes charge "
    "1551 to 3097 kWh/a at their own wallbox, "
    "https://solar.htw-berlin.de/wp-content/uploads/HTW-Solares-Laden-von-Elektrofahrzeugen.pdf",
    SOURCES,
)
EV_KWH_HIGH = Rule(
    "ev_high",
    3097.0,
    "kWh per year",
    EV_KWH_LOW.source,
    EV_KWH_LOW.evidence,
)
HTW_TABLE_MIN_KWH = Rule(
    "htw_table_min",
    2000.0,
    "kWh per year",
    f"HTW Unabhängigkeitsrechner: valid for 2000 to 10 000 kWh/a, no heat pump or electric car, {HTW_FAQ}",
    "services/engine/data/htw/source.json",
)
HTW_TABLE_MAX_KWH = Rule(
    "htw_table_max",
    10000.0,
    "kWh per year",
    HTW_TABLE_MIN_KWH.source,
    HTW_TABLE_MIN_KWH.evidence,
)

# Grid code: VDE-AR-N 4105 (energie-experten.org, solarzubau.de).
VDE_4105 = (
    "energie-experten.org (updated 2026-06-30), "
    "https://www.energie-experten.org/erneuerbare-energien/photovoltaik/planung/vde-ar-n-4105"
)
SINGLE_PHASE_MAX_KVA = Rule(
    "single_phase_limit",
    4.6,
    "kVA per phase",
    f"VDE-AR-N 4105: single-phase feed-in at most 4.6 kVA per phase (unbalance limit), {VDE_4105}",
    f"{PLANNER} §2.3(b)",
)
NA_PROTECTION_KVA = Rule(
    "na_protection",
    30.0,
    "kVA",
    f"VDE-AR-N 4105: central grid and system protection (NA-Schutz) above 30 kVA, {VDE_4105}",
    f"{PLANNER} §2.3(b)",
)
VDE_4110_KW = Rule(
    "vde_4110",
    135.0,
    "kW",
    f"VDE-AR-N 4105 applies up to 135 kW; above it VDE-AR-N 4110, {VDE_4105}",
    f"{PLANNER} §2.3(b)",
)

# Yield: PVGIS.
PVGIS_MANUAL = (
    "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/"
    "using-pvgis-5/pvgis-5-user-manual_en"
)
PVGIS_SYSTEM_LOSS_PCT = Rule(
    "pvgis_loss",
    14.0,
    "%",
    f"PVGIS 5 user manual: default system loss 14 % (cables, inverter, soiling, ageing), {PVGIS_MANUAL}",
    f"{PLANNER} §2.1(b)",
)
PVGIS_GRID_DEG = Rule(
    "pvgis_grid",
    0.05,
    "degree",
    "Cache cell of the PVGIS requests, as the ticket specifies",
    TICKET,
)
PVGIS_TIMEOUT_S = Rule(
    "pvgis_timeout",
    120.0,
    "s",
    "A full 2005-2023 hourly request took 19 s on 2026-10-09; the limit leaves room for a slow PVGIS",
    "services/engine/tests/fixtures/pvgis",
    verified=False,
)
DEFAULT_TILT_DEG = Rule(
    "default_tilt",
    35.0,
    "degree",
    f"HTW calculator default: 35° facing south, {HTW_FAQ}",
    f"{PLANNER} §2.1(b)",
)
DEFAULT_AZIMUTH_DEG = Rule(
    "default_azimuth",
    180.0,
    "degree (north 0, east 90, south 180)",
    f"HTW calculator default: 35° facing south, {HTW_FAQ}",
    f"{PLANNER} §2.1(b)",
)

# String layout with the reference module.
STRING_T_MIN_C = Rule(
    "string_t_min",
    -10.0,
    "°C",
    "Lowest cell temperature for the open-circuit voltage check",
    "",
    verified=False,
)
STRING_T_CELL_MAX_C = Rule(
    "string_t_cell_max",
    70.0,
    "°C",
    "Highest cell temperature for the MPP voltage check (Voc coefficient used for Vmpp)",
    "",
    verified=False,
)
IEC_712 = (
    "IEC 60364-7-712:2017 as applied in the BS 7671 section 712 calculation sheet "
    "(https://electricalom.com/site/dl/other/Section%20712%20-%20PVs%20Calculations.pdf) and "
    "Mitolo 2025 (https://journals.riverpublishers.com/index.php/DGAEJ/article/download/30737/22483/121041)"
)
STRING_FUSE_ISC_FACTOR = Rule(
    "string_fuse_isc_factor",
    1.25,
    "x Isc STC",
    f"Maximum string short-circuit current I_SC_MAX = 1.25 x Isc STC; {IEC_712}",
    SOURCES,
)
STRING_FUSE_OCPR_FACTOR = Rule(
    "string_fuse_ocpr_factor",
    1.35,
    "x module maximum series fuse rating",
    f"String protection is required when 1.35 x I_MOD_MAX_OCPR < (N - 1) x I_SC_MAX; {IEC_712}",
    SOURCES,
)
STRING_FUSE_POLES = Rule(
    "string_fuse_poles",
    2.0,
    "fuses per string",
    "Arrays without an earthed conductor are protected in both poles (Mitolo 2025, "
    "https://journals.riverpublishers.com/index.php/DGAEJ/article/view/30737/22485; Eaton Bussmann "
    "photovoltaic application guide: fuse links in both the positive and the negative cable)",
    SOURCES,
)
STRING_FUSE_GROUP = Rule(
    "string_fuse_group",
    1.0,
    "MPPT per protection group",
    "Only strings in parallel feed a string fault: two parallel strings never exceed one string's "
    "short-circuit current as reverse current (SMA SMC_RUECK-11), three or more need string protection "
    "(Eaton Bussmann photovoltaic application guide); an inverter's separate MPPT inputs are separate "
    "arrays (IEC 62548:2016, Figure 5)",
    SOURCES,
)
STRING_FUSE_RATING_MIN = Rule(
    "string_fuse_rating_min",
    1.5,
    "x Isc STC",
    f"gPV fuse rating window 1.5 x Isc < In < 2.4 x Isc; {IEC_712}",
    SOURCES,
)
STRING_FUSE_RATING_MAX = Rule(
    "string_fuse_rating_max",
    2.4,
    "x Isc STC",
    STRING_FUSE_RATING_MIN.source,
    STRING_FUSE_RATING_MIN.evidence,
)

# Installer-scope Stückliste lines.
DC_CABLE_M_PER_STRING = Rule(
    "dc_cable_length",
    15.0,
    "m per pole and string",
    "Placeholder DC route between array and inverter; the installer measures the real route",
    f"{PLANNER} §2.5(c)",
    verified=False,
)
CONNECTOR_PAIRS_PER_STRING = Rule(
    "connector_pairs",
    2.0,
    "pairs per string",
    "One mating pair at the array end and one at the inverter end of each string",
    "",
    verified=False,
)

# Roof step: module count on LoD2 roof planes.
ROOF_FLAT_TILT_DEG = Rule(
    "roof_flat",
    10.0,
    "degree",
    "Planes flatter than this count as flat roofs; their rows face south",
    "",
    verified=False,
)
ROOF_MAX_TILT_DEG = Rule(
    "roof_max_tilt",
    60.0,
    "degree",
    "Steeper planes (mansard flanks, towers) are not counted for modules",
    "",
    verified=False,
)
ROOF_NORTH_EXCLUSION_DEG = Rule(
    "roof_north",
    45.0,
    "degree either side of north",
    "Pitched planes facing within this angle of north are not counted for modules",
    "",
    verified=False,
)
ROOF_EDGE_INSET_M = Rule(
    "roof_edge_inset",
    0.3,
    "m",
    "Clearance from every plane edge (ridge, eaves, verges, valleys)",
    "",
    verified=False,
)
MODULE_GAP_M = Rule(
    "module_gap",
    0.02,
    "m",
    "Gap between neighbouring modules for clamps",
    "",
    verified=False,
)

# Commercial and industrial (C&I) sizing.
LOAD_INTERVAL_H = Rule(
    "load_interval",
    0.25,
    "h",
    "Load profiles in 15-minute intervals, as metered for RLM customers",
    TICKET,
)
RLM_THRESHOLD_KWH = Rule(
    "rlm_threshold",
    100000.0,
    "kWh per year",
    "Consumers above 100,000 kWh/a are metered with a registering load profile (MsbG § 55 (1) Nr. 1, "
    "https://www.gesetze-im-internet.de/messbg/__55.html)",
    SOURCES,
)
CI_HOURS_PEAK = Rule(
    "ci_hours_peak",
    1.0,
    "h of storage per kW of peak reduction",
    "Intilion: peak shaving runs batteries at about 1C "
    "(https://intilion.com/blog/stromspeicher-fur-gewerbe-und-industrie/)",
    SOURCES,
)
CI_HOURS_SELF_CONSUMPTION = Rule(
    "ci_hours_self_consumption",
    2.0,
    "h of storage per kW",
    "Intilion: self-consumption storage runs at about 0.5C, 100 kWh for 50 kW "
    "(https://intilion.com/blog/stromspeicher-fur-gewerbe-und-industrie/)",
    SOURCES,
)
CI_KWH_PER_KWP = Rule(
    "ci_kwh_per_kwp",
    1.0,
    "kWh usable per kWp",
    "Voltfang (2026-02-18): about 1 kWh of usable storage per kWp of PV for C&I self-consumption "
    "(https://voltfang.de/2026/02/18/wie-gross-muss-eine-pv-anlage-fuer-einen-gewerbespeicher-sein/)",
    SOURCES,
)
CI_KWP_PER_MWH_LOW = Rule(
    "ci_kwp_per_mwh_low",
    0.8,
    "kWp per MWh/a",
    "Voltfang (2026-02-18): 0.8 to 1.0 kWp of PV per MWh/a for a C&I storage system "
    "(https://voltfang.de/2026/02/18/wie-gross-muss-eine-pv-anlage-fuer-einen-gewerbespeicher-sein/)",
    SOURCES,
)
CI_KWP_PER_MWH_HIGH = Rule(
    "ci_kwp_per_mwh_high",
    1.0,
    "kWp per MWh/a",
    CI_KWP_PER_MWH_LOW.source,
    CI_KWP_PER_MWH_LOW.evidence,
)


def _all() -> tuple[Rule, ...]:
    """Every Rule this module defines, in definition order."""
    return tuple(value for value in globals().values() if isinstance(value, Rule))


ALL = _all()

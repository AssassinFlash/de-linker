"""Expand a published BDEW/VDEW standard load profile into a real year of 15-minute means.

The coefficient tables are published data, not a model of a customer. This
module only turns one of them into an interval series under the edition's own
published rules, and reports the annual integral it produced instead of
silently rescaling it. Two editions exist and they are deliberately separate
files: the 1999 tables are quarter-hour average power in W normalised to
1,000 kWh/a, the 2025 tables are quarter-hour energy in kWh normalised to
1 Mio kWh/a.

Which profile belongs in which engine role is decided by what the publisher
says the numbers are, not by their magnitude. H0/H25/G*/L* are gross customer
load. P25/S25 are net household import after PV (and battery) self-consumption
has already been netted out; BDEW requires the self-consumption to be accounted
for separately on the supplier side. Feeding P25/S25 into a gross-load role
would count that PV twice, so `role()` returns the boundary each one belongs to
and the caller has to match it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from .errors import InvalidInput
from .interval import Interval, utc

type Edition = Literal[1999, 2025]

DATA = Path(__file__).resolve().parents[3] / "data" / "load-profiles"

# Quarter-hour slots per day. Both editions publish exactly 96 rows.
SLOTS = 96
SLOT_MINUTES = 15

# 1999 seasons, verbatim from the primary document's season table.
WINTER = "Winter"
SOMMER = "Sommer"
UEBERGANG = "Übergangszeit"

DAYTYPE_WERKTAG = "Werktag"
DAYTYPE_SAMSTAG = "Samstag"
DAYTYPE_SONNTAG = "Sonntag"

# The engine role each published profile actually measures. A gross-load role
# needs the customer's own consumption; the PV/battery combinations publish the
# residual import after self-consumption, which the engine models as net_import.
GROSS_LOAD_PROFILES = frozenset(
    {"H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "H25", "G25", "L25"}
)
NET_IMPORT_PROFILES = frozenset({"P25", "S25"})
# Profiles the publisher ships dynamisation-free and therefore require the
# fourth-order factor to produce a typical annual course.
DYNAMISED_PROFILES = frozenset({"H0", "H25", "P25", "S25"})


def role(profile: str) -> str:
    """The energy-domain boundary this published profile measures."""
    if profile in GROSS_LOAD_PROFILES:
        return "gross_load"
    if profile in NET_IMPORT_PROFILES:
        return "net_import"
    raise InvalidInput(f"unknown standard load profile: {profile}")


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (anonymous algorithm, valid for all years >= 1583)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    leap = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * leap) // 451
    month = (h + leap - 7 * m + 114) // 31
    day = ((h + leap - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def nationwide_holidays(year: int) -> frozenset[date]:
    """The nine holidays the Länder statutes protect nationwide (BMI).

    State-specific holidays are deliberately absent: BDEW's own calendar is per
    Bundesland and this repository holds no first-hand Land statute. A caller
    that knows its Bundesland passes the extra dates explicitly.
    """
    easter = easter_sunday(year)
    return frozenset(
        {
            date(year, 1, 1),
            easter - timedelta(days=2),
            easter + timedelta(days=1),
            easter + timedelta(days=39),
            easter + timedelta(days=50),
            date(year, 5, 1),
            date(year, 10, 3),
            date(year, 12, 25),
            date(year, 12, 26),
        }
    )


def season_1999(day: date) -> str:
    month_day = (day.month, day.day)
    if month_day >= (11, 1) or month_day <= (3, 20):
        return WINTER
    if (5, 15) <= month_day <= (9, 14):
        return SOMMER
    return UEBERGANG


def daytype_1999(day: date, holidays: frozenset[date]) -> str:
    if day.weekday() == 6 or day in holidays:
        return DAYTYPE_SONNTAG
    # The primary document puts 24.12. and 31.12. on the Saturday profile
    # unless they already fall on a Sunday, which the branch above settles.
    if (day.month, day.day) in ((12, 24), (12, 31)):
        return DAYTYPE_SAMSTAG
    if day.weekday() == 5:
        return DAYTYPE_SAMSTAG
    return DAYTYPE_WERKTAG


def daytype_2025(day: date, holidays: frozenset[date]) -> str:
    if day.weekday() == 6 or day in holidays:
        return "FT"
    if day.weekday() == 5:
        return "SA"
    return "WT"


def dynamisation_factor(t: int) -> float:
    """Fourth-order polynomial published with both editions, t = day of year."""
    return -3.92e-10 * t**4 + 3.20e-07 * t**3 - 7.02e-05 * t**2 + 2.10e-03 * t + 1.24


def _slot_instants(naive: datetime, zone: ZoneInfo) -> tuple[datetime, ...]:
    """Every real instant a wall-clock time occurs at: none, one, or twice.

    A time is real only if converting it to UTC and back reproduces both the
    wall clock and its fold. Across a spring-forward jump the skipped hour
    yields no instant; across a fall-back jump the repeated hour yields two,
    ordered.
    """
    instants: list[datetime] = []
    for fold in (0, 1):
        aware = naive.replace(tzinfo=zone, fold=fold)
        try:
            instant = utc(aware)
            back = instant.astimezone(zone)
        except (OverflowError, ValueError):
            continue
        if back.replace(tzinfo=None) == naive and back.fold == fold:
            instants.append(instant)
    return tuple(instants)


@dataclass(frozen=True)
class CoeffTable:
    edition: Edition
    profile: str
    normalisation_kwh_per_year: float
    # 1999: series[season][daytype][slot]; 2025: series[month][daytype][slot]
    series: dict[str, dict[str, tuple[float, ...]]]
    monthly: bool

    def slots(self, day: date, holidays: frozenset[date]) -> tuple[float, ...]:
        if self.monthly:
            return self.series[str(day.month)][daytype_2025(day, holidays)]
        return self.series[season_1999(day)][daytype_1999(day, holidays)]


def _load(document: dict[str, object], edition: Edition, profile: str) -> CoeffTable:
    normalisation = document["normalisation_kwh_per_year"]
    if not isinstance(normalisation, int | float):
        raise InvalidInput("published normalisation basis must be a number")
    profiles = document["profiles"]
    if not isinstance(profiles, dict) or profile not in profiles:
        available = ", ".join(sorted(profiles)) if isinstance(profiles, dict) else ""
        raise InvalidInput(
            f"unknown {edition} standard load profile: {profile} ({available})"
        )
    entry = profiles[profile]
    if not isinstance(entry, dict):
        raise InvalidInput("published profile entry must be an object")
    raw = entry["series"]
    if not isinstance(raw, dict):
        raise InvalidInput("published profile series must be an object")
    # The calendar asks for a fixed set of combinations; a table missing one
    # must fail here rather than surface as a KeyError mid-year.
    expected_outer = (
        {str(month) for month in range(1, 13)} if edition == 2025 else set()
    )
    expected_inner = {"WT", "SA", "FT"} if edition == 2025 else set()
    if edition == 1999:
        expected_inner = {DAYTYPE_WERKTAG, DAYTYPE_SAMSTAG, DAYTYPE_SONNTAG}
    series: dict[str, dict[str, tuple[float, ...]]] = {}
    for outer, inner in raw.items():
        if not isinstance(inner, dict):
            raise InvalidInput("published profile day-type block must be an object")
        block: dict[str, tuple[float, ...]] = {}
        for key, values in inner.items():
            if not isinstance(values, list) or len(values) != SLOTS:
                raise InvalidInput(
                    f"{profile} {outer}/{key}: 96 quarter-hour values required"
                )
            if any(not isinstance(value, int | float) for value in values):
                raise InvalidInput(f"{profile} {outer}/{key}: numeric values required")
            block[key] = tuple(float(value) for value in values)
        if set(block) != expected_inner:
            missing = sorted(expected_inner - set(block))
            raise InvalidInput(f"{profile} {outer}: missing day types {missing}")
        series[outer] = block
    if edition == 2025:
        if set(series) != expected_outer:
            missing = sorted(expected_outer - set(series))
            raise InvalidInput(f"{profile}: missing months {missing}")
    else:
        if set(series) != {WINTER, SOMMER, UEBERGANG}:
            raise InvalidInput(f"{profile}: the three published seasons are required")
    return CoeffTable(edition, profile, float(normalisation), series, edition == 2025)


def coefficient_table(edition: Edition, profile: str) -> CoeffTable:
    name = f"coefficients-{edition}-{'vdew' if edition == 1999 else 'bdew'}.json"
    path = DATA / name
    try:
        document = json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise InvalidInput(
            f"published {edition} coefficient table is unavailable"
        ) from error
    if not isinstance(document, dict):
        raise InvalidInput("published coefficient table must be an object")
    return _load(document, edition, profile)


@dataclass(frozen=True)
class LoadProfile:
    """A real interval series plus the published basis it was expanded from."""

    edition: Edition
    profile: str
    year: int
    intervals: tuple[Interval, ...]
    values_kw: tuple[float, ...]
    annual_kwh: float
    design_national_kwh_per_year: float
    extra_holidays: tuple[date, ...]
    interval_count: int
    dynamised: bool

    @property
    def measurement_role(self) -> str:
        """The engine measurement boundary this profile belongs to."""
        return role(self.profile)

    @property
    def normalisation_gap(self) -> float:
        """Expanded annual energy over the published normalisation basis."""
        if self.design_national_kwh_per_year <= 0:
            raise InvalidInput("published normalisation basis must be positive")
        return self.annual_kwh / self.design_national_kwh_per_year

    def provenance(self) -> dict[str, object]:
        return {
            "label": (
                f"BDEW/VDEW Standardlastprofil {self.profile} ({self.edition} edition), "
                f"expanded to {self.year} under the edition's published calendar rules"
            ),
            "basis": "published_load_profile",
            "rights_basis": (
                "BDEW/VDEW publishes these profiles for unrestricted industry use; "
                "the coefficient tables are retained with their SHA-256"
            ),
            "edition": self.edition,
            "profile": self.profile,
            "year": self.year,
            "measurement_role": self.measurement_role,
            "dynamised": self.dynamised,
            "published_normalisation_kwh_per_year": self.design_national_kwh_per_year,
            "expanded_annual_kwh": self.annual_kwh,
            "extra_holidays": [day.isoformat() for day in self.extra_holidays],
        }


def expand(
    edition: Edition,
    profile: str,
    *,
    year: int,
    annual_kwh: float,
    timezone: str = "Europe/Berlin",
    extra_holidays: tuple[date, ...] = (),
    dynamise: bool | None = None,
) -> LoadProfile:
    """Expand one published profile to a whole year of 15-minute means in kW.

    ``annual_kwh`` is the customer's stated annual consumption. The published
    tables are normalised to their own basis, so the scale factor is that ratio;
    the resulting annual integral is returned rather than forced to match.
    """
    if annual_kwh <= 0:
        raise InvalidInput("annual consumption must be positive")
    if not 2000 <= year <= 2100:
        raise InvalidInput("expanded calendar year out of range")
    table = coefficient_table(edition, profile)
    zone = ZoneInfo(timezone)
    holidays = nationwide_holidays(year) | frozenset(extra_holidays)
    apply_dynamisation = profile in DYNAMISED_PROFILES if dynamise is None else dynamise
    scale = annual_kwh / table.normalisation_kwh_per_year
    # The published day is a 96-slot wall-clock day. Each slot is resolved to
    # every real instant it occurs at, then the whole year is ordered by real
    # time: a spring-forward hour yields no slot at all (it never happens) and
    # a fall-back hour yields each of its slots twice. Nothing is interpolated
    # and no slot is zero-filled.
    slots: list[tuple[datetime, float]] = []
    day = date(year, 1, 1)
    t = 1
    while day.year == year:
        published = table.slots(day, holidays)
        factor = dynamisation_factor(t) if apply_dynamisation else 1.0
        midnight = datetime(day.year, day.month, day.day)
        for slot, value in enumerate(published):
            naive = midnight + timedelta(minutes=SLOT_MINUTES * slot)
            if table.monthly:
                # kWh per quarter hour at the published basis.
                power = value * scale * factor / (SLOT_MINUTES / 60.0)
            else:
                # Quarter-hour average power in W at the published basis.
                power = value * scale * factor / 1000.0
            for start in _slot_instants(naive, zone):
                slots.append((start, power))
        day += timedelta(days=1)
        t += 1
    slots.sort(key=lambda item: item[0])
    intervals: list[Interval] = []
    values: list[float] = []
    step = timedelta(minutes=SLOT_MINUTES)
    for start, power in slots:
        end = start + step
        if intervals and intervals[-1].end != start:
            # An out-of-order or missing slot would silently distort the year.
            raise InvalidInput("published profile does not tile the calendar year")
        intervals.append(Interval(start, end))
        values.append(power)
    annual = sum(
        power * interval.hours
        for power, interval in zip(values, intervals, strict=True)
    )
    return LoadProfile(
        edition,
        profile,
        year,
        tuple(intervals),
        tuple(values),
        annual,
        table.normalisation_kwh_per_year,
        tuple(extra_holidays),
        len(intervals),
        apply_dynamisation,
    )


def to_csv(profile: LoadProfile, timezone: str = "Europe/Berlin") -> bytes:
    """Render the expanded series as the engine's own `csv_profile_v1` input.

    Timestamps carry their explicit UTC offset: a fall-back day contains the
    same wall clock twice, and an offset is what distinguishes the two
    occurrences without a separate fold column.
    """
    zone = ZoneInfo(timezone)
    lines = ["time,power"]
    for interval, power in zip(profile.intervals, profile.values_kw, strict=True):
        local = interval.start.astimezone(zone)
        lines.append(f"{local.isoformat(timespec='seconds')},{power:.10f}")
    return ("\n".join(lines) + "\n").encode()

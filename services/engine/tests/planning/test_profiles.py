"""Independent unit/time expectations at the real CSV import boundary."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from linker_engine.planning import timezone_rules
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.errors import InvalidInput, VersionUnavailable
from linker_engine.planning.interval import Interval, regular_intervals
from linker_engine.planning.profiles import read_profile
from linker_engine.planning.regrid import align, regrid
from linker_engine.planning.timezone_rules import TimezoneRules, load_timezone


@pytest.fixture
def rules() -> TimezoneRules:
    return load_timezone("Europe/Berlin")


@pytest.fixture
def mapping() -> CsvMapping:
    return CsvMapping(
        timestamp_column="time",
        value_column="value",
        measurement="gross_load",
        value_kind="interval_average_kw",
        timestamp_role="start",
        timezone="Europe/Berlin",
        origin="measured",
        interval_seconds=900,
        delimiter=";",
        decimal=",",
    )


def test_quarter_hour_energy_and_power_are_not_interchangeable(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    raw = b"time;value\n2024-01-01T00:00:00Z;0,75\n2024-01-01T00:15:00Z;1,25\n"
    energy = read_profile(
        raw, replace(mapping, value_kind="interval_energy_kwh"), rules
    )
    assert energy.values_kw == (3.0, 5.0)
    assert energy.total_kwh == 2.0
    power = read_profile(raw, mapping, rules)
    assert power.total_kwh == 0.5
    assert energy.source.raw_sha256 == power.source.raw_sha256 == digest(raw)
    assert energy.source.details_json != power.source.details_json
    details = energy.source.document()["details"]
    assert isinstance(details, dict)
    assert details["timezone_rules_sha256"] == rules.sha256


def test_interval_end_is_not_silently_read_as_start(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    profile = read_profile(
        b"time;value\n2024-01-01T00:15:00Z;4\n",
        replace(mapping, timestamp_role="end"),
        rules,
    )
    assert profile.intervals == (
        Interval(
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
        ),
    )
    assert profile.total_kwh == 1.0


def test_both_fall_occurrences_are_preserved_with_explicit_folds(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    profile = read_profile(
        b"time;value;fold\n2024-10-27T02:00:00;4;0\n2024-10-27T02:00:00;6;1\n",
        replace(mapping, interval_seconds=3600, fold_column="fold"),
        rules,
    )
    assert tuple(interval.start.hour for interval in profile.intervals) == (0, 1)
    assert profile.total_kwh == 10.0


def test_both_fall_offsets_are_distinct_real_hours(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    profile = read_profile(
        b"time;value\n2024-10-27T02:00:00+02:00;4\n2024-10-27T02:00:00+01:00;6\n",
        replace(mapping, interval_seconds=3600),
        rules,
    )
    assert tuple(interval.start.hour for interval in profile.intervals) == (0, 1)
    assert profile.total_kwh == 10.0


@pytest.mark.parametrize(
    "timestamp,reason",
    [
        ("2024-03-31T02:30:00", "does not exist"),
        ("2024-10-27T02:30:00", "requires offset or fold"),
    ],
)
def test_dst_uncertainty_is_not_guessed(
    mapping: CsvMapping, rules: TimezoneRules, timestamp: str, reason: str
) -> None:
    with pytest.raises(InvalidInput, match=reason):
        read_profile(f"time;value\n{timestamp};4\n".encode(), mapping, rules)


def test_calendar_days_have_their_actual_23_or_25_hours(rules: TimezoneRules) -> None:
    zone = rules.zone()
    spring = regular_intervals(
        datetime(2024, 3, 31, tzinfo=zone),
        datetime(2024, 4, 1, tzinfo=zone),
        timedelta(hours=1),
    )
    fall = regular_intervals(
        datetime(2024, 10, 27, tzinfo=zone),
        datetime(2024, 10, 28, tzinfo=zone),
        timedelta(hours=1),
    )
    assert len(spring) == 23 and len(fall) == 25
    assert all(interval.hours == 1 for interval in (*spring, *fall))


def test_explicit_variable_intervals_preserve_energy(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    profile = read_profile(
        b"time;end;value\n2024-01-01T00:00Z;2024-01-01T00:45Z;3\n"
        b"2024-01-01T00:45Z;2024-01-01T01:30Z;6\n",
        replace(
            mapping,
            end_timestamp_column="end",
            interval_seconds=None,
            value_kind="interval_energy_kwh",
        ),
        rules,
    )
    target = regular_intervals(
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 1, 1, 30, tzinfo=UTC),
        timedelta(minutes=30),
    )
    regridded = regrid(profile, target)
    assert regridded.values_kw == (4.0, 6.0, 8.0)
    assert regridded.total_kwh == profile.total_kwh == 9.0
    assert regridded.source.native_max_interval_seconds == 2700


def test_missing_quarter_is_not_filled_with_zero(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    profile = read_profile(
        b"time;value\n2024-01-01T00:00Z;4\n2024-01-01T00:30Z;4\n", mapping, rules
    )
    assert profile.total_kwh == 2.0
    target = (
        Interval(
            datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, 0, 45, tzinfo=UTC)
        ),
    )
    with pytest.raises(InvalidInput, match="does not cover"):
        regrid(profile, target)
    with pytest.raises(InvalidInput, match="does not cover"):
        align(profile)


@pytest.mark.parametrize(
    "rows",
    [
        "2024-01-01T00:00Z;4\n2024-01-01T00:00Z;5\n",
        "2024-01-01T00:00Z;4\n2024-01-01T00:10Z;5\n",
        "2024-01-01T01:00Z;4\n2024-01-01T00:00Z;5\n",
    ],
)
def test_duplicates_overlap_and_reverse_order_are_rejected(
    mapping: CsvMapping, rules: TimezoneRules, rows: str
) -> None:
    with pytest.raises(InvalidInput, match="ordered.*overlap"):
        read_profile(("time;value\n" + rows).encode(), mapping, rules)


@pytest.mark.parametrize("value", ["NaN", "inf", "1.234,5", "1,234.5", "", "1e999"])
def test_invalid_numbers_are_not_coerced_to_zero(
    mapping: CsvMapping, rules: TimezoneRules, value: str
) -> None:
    with pytest.raises(InvalidInput):
        read_profile(
            f"time;value\n2024-01-01T00:00Z;{value}\n".encode(), mapping, rules
        )


def test_negative_net_import_is_not_claimed_as_gross_consumption(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    raw = b"time;value\n2024-01-01T00:00Z;-4\n"
    net = read_profile(raw, replace(mapping, measurement="net_import"), rules)
    assert net.measurement == "net_import" and net.total_kwh == -1.0
    with pytest.raises(InvalidInput, match="valid sign"):
        read_profile(raw, mapping, rules)


def test_unknown_last_interval_is_never_inferred_from_row_count(
    mapping: CsvMapping,
) -> None:
    with pytest.raises(InvalidInput, match="duration"):
        replace(mapping, interval_seconds=None)


def test_source_timezone_is_pinned_and_cannot_be_substituted(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    with pytest.raises(InvalidInput, match="do not match"):
        read_profile(
            b"time;value\n2024-01-01T00:00Z;4\n", mapping, load_timezone("UTC")
        )
    with pytest.raises(VersionUnavailable):
        TimezoneRules(rules.name, b"invalid TZif")
    with pytest.raises(InvalidInput):
        load_timezone("../../etc/passwd")


@pytest.mark.parametrize(
    "timestamp",
    [
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:59:59-01:00",
    ],
)
def test_offset_conversion_outside_utc_domain_is_a_named_input_error(
    mapping: CsvMapping, rules: TimezoneRules, timestamp: str
) -> None:
    with pytest.raises(InvalidInput, match="supported UTC"):
        read_profile(f"time;value\n{timestamp};1\n".encode(), mapping, rules)


def test_truncated_tzif_with_valid_magic_is_a_named_version_error() -> None:
    with pytest.raises(VersionUnavailable, match="TZif"):
        TimezoneRules("UTC", b"TZif" + b"\0" * 10)


@pytest.mark.parametrize(
    "name", ["posixrules", "localtime", "right/UTC", "posix/Europe/Berlin"]
)
def test_timezone_intake_rejects_host_special_files(name: str) -> None:
    with pytest.raises(InvalidInput, match="known IANA"):
        load_timezone(name)


def test_special_tzif_files_stay_invalid_when_an_installed_host_lists_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aliases = frozenset({"localtime", "posixrules", "right/UTC", "posix/Europe/Oslo"})
    monkeypatch.setattr(timezone_rules, "installed_iana_names", lambda: aliases)
    for name in aliases:
        with pytest.raises(InvalidInput, match="known IANA"):
            timezone_rules.require_iana_timezone(name)


def test_pinned_timezone_replay_does_not_require_a_current_host_name() -> None:
    # A captured, valid TZif remains replayable even after an installed alias
    # has disappeared. Only new intake depends on the current IANA name set.
    rules = TimezoneRules("Historical/Zone", load_timezone("UTC").content)
    assert rules.zone().utcoffset(None) is not None


def test_averaging_then_refining_does_not_recover_measured_peaks(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    raw = read_profile(
        b"time;value\n2024-01-01T00:00Z;100\n2024-01-01T00:15Z;0\n"
        b"2024-01-01T00:30Z;100\n2024-01-01T00:45Z;0\n",
        mapping,
        rules,
    )
    coarse_axis = (Interval(raw.intervals[0].start, raw.intervals[-1].end),)
    coarse = regrid(raw, coarse_axis)
    refined = regrid(coarse, raw.intervals)
    assert refined.values_kw == (50, 50, 50, 50)
    assert refined.total_kwh == raw.total_kwh == 50
    assert refined.source.native_max_interval_seconds == 900
    assert refined.effective_max_interval_seconds == 3600
    assert refined.reconstructed_means and not raw.reconstructed_means
    assert refined.transformations[0].input_document_sha256 == digest(
        encode(raw.document())
    )
    assert refined.transformations[1].input_document_sha256 == digest(
        encode(coarse.document())
    )
    assert all(not item.exact_interval_copy for item in refined.transformations)
    copied = regrid(raw, raw.intervals)
    assert not copied.reconstructed_means
    assert copied.effective_max_interval_seconds == 900


def test_leap_year_and_refinement_keep_original_energy_and_resolution(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    # 2024 has 366 real UTC days: an exact 1 kW interval mean is 8784 kWh.
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)
    hours = regular_intervals(start, end, timedelta(hours=1))
    raw = (
        "time;value\n" + "".join(f"{item.start.isoformat()};1\n" for item in hours)
    ).encode()
    hourly = read_profile(raw, replace(mapping, interval_seconds=3600), rules)
    quarters = regrid(hourly, regular_intervals(start, end, timedelta(minutes=15)))
    assert len(hourly.values_kw) == 8784
    assert len(quarters.values_kw) == 35136
    assert hourly.total_kwh == quarters.total_kwh == 8784.0
    assert quarters.source.native_max_interval_seconds == 3600
    assert len(quarters.transformations) == 1
    assert (
        quarters.transformations[0].method
        == "energy_preserving_overlap_of_interval_means"
    )
    assert quarters.reconstructed_means
    assert quarters.effective_max_interval_seconds == 3600


def test_pv_and_load_align_without_claiming_finer_native_observations(
    mapping: CsvMapping, rules: TimezoneRules
) -> None:
    load = read_profile(
        b"time;value\n2024-01-01T00:00Z;4\n2024-01-01T00:15Z;8\n"
        b"2024-01-01T00:30Z;12\n2024-01-01T00:45Z;16\n",
        mapping,
        rules,
    )
    pv = read_profile(
        b"time;value\n2024-01-01T00:00Z;10\n",
        replace(
            mapping,
            interval_seconds=3600,
            measurement="pv_available_ac",
            origin="modelled",
        ),
        rules,
    )
    aligned_load, aligned_pv = align(load, pv)
    assert aligned_load.intervals == aligned_pv.intervals == load.intervals
    assert aligned_pv.values_kw == (10, 10, 10, 10)
    assert aligned_load.total_kwh == aligned_pv.total_kwh == 10.0
    assert aligned_pv.source.native_max_interval_seconds == 3600

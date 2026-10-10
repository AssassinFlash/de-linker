"""POST /design/residential: from a household to a complete, released system.

The steps: position and yield (PVGIS), storage limits (HTW Berlin), then for
every inverter the eligibility rules, a reference string layout and the
released battery that fits the limit best. The best-ranked inverter carries
the proposal; the others stay available as alternatives. The Stückliste lists
our products with their release basis and, as the installer's scope, the
parts we do not supply.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import eligibility, geo, htw, rules, stacking, strings
from .catalog import Catalog, Product
from .compatibility import (
    Accessory,
    Requirement,
)
from .explain import value_text
from .models import (
    BatteryChoice,
    CandidateInverter,
    Candidates,
    Excluded,
    Line,
    MetricsResult,
    PlaneInput,
    ProductRef,
    Range,
    Report,
    ResidentialInput,
    ResidentialResult,
    Role,
    RuleResult,
    Selection,
    StorageResult,
    StringGroup,
    StringLayoutResult,
    YieldResult,
)
from .products import Engine, docs, documents_of, ref, release
from .pvgis import Pvgis
from .texts import Locale, fmt, t, tn

INVERTER_CLASSES = ("inverters",)
BATTERY_CLASSES = ("home-storage", "battery-systems")


class DesignInputError(ValueError):
    """The request names something the engine cannot design with."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def rule_result(check: eligibility.Check, locale: Locale) -> RuleResult:
    return RuleResult(
        id=check.id,
        passed=check.passed,
        value=check.value,
        limit=check.limit,
        label=t(f"rule.{check.id}", locale),
        text=value_text(check.id, check.value, check.limit, locale),
    )


# Yield -----------------------------------------------------------------------------


def planes_of(request: ResidentialInput) -> list[PlaneInput]:
    if request.planes:
        return request.planes
    return [
        PlaneInput(
            kwp=request.pv_kwp,
            tilt_deg=rules.DEFAULT_TILT_DEG.value,
            azimuth_deg=rules.DEFAULT_AZIMUTH_DEG.value,
        )
    ]


def estimate_yield(
    pvgis: Pvgis,
    latitude: float,
    longitude: float,
    planes: list[PlaneInput],
    locale: Locale,
) -> YieldResult:
    """Yearly yield of all planes over the years PVGIS covers for every plane."""
    profiles = [
        pvgis.per_kwp(latitude, longitude, p.tilt_deg, p.azimuth_deg) for p in planes
    ]
    years = sorted(set.intersection(*(set(p.annual_kwh_per_kwp) for p in profiles)))
    pairs = list(zip(planes, profiles, strict=True))
    totals = [
        sum(plane.kwp * profile.annual_kwh_per_kwp[year] for plane, profile in pairs)
        for year in years
    ]
    kwp = sum(plane.kwp for plane in planes)
    first = profiles[0]
    return YieldResult(
        kwh_year_range=Range(low=round(min(totals)), high=round(max(totals))),
        kwh_per_kwp_range=Range(
            low=round(min(totals) / kwp), high=round(max(totals) / kwp)
        ),
        kwh_year_mean=round(sum(totals) / len(totals)),
        monthly_kwh=[
            round(
                sum(
                    plane.kwp * profile.monthly_kwh_per_kwp[month]
                    for plane, profile in pairs
                ),
                1,
            )
            for month in range(12)
        ],
        years=(years[0], years[-1]),
        planes=planes,
        latitude=latitude,
        longitude=longitude,
        source=t("yield.source", locale, db=first.radiation_db, loss=first.loss_pct),
    )


# Batteries --------------------------------------------------------------------------


@dataclass(frozen=True)
class BatteryFit:
    config: stacking.BatteryConfig
    above: bool


def battery_options(
    engine: Engine, inverter: Product, upper_kwh: float
) -> list[BatteryFit]:
    """The best configuration of every released battery for the inverter, best first.

    Within the limit the largest configuration ranks first, above it the
    smallest; then a plain release before one that needs an accessory, then
    fewer pieces, then the product id, so the order is stable.
    """
    fits: list[BatteryFit] = []
    for battery in engine.catalog.in_class(*BATTERY_CLASSES):
        pair = engine.compatibility.pair(inverter.model, battery.model)
        picked = stacking.pick(
            stacking.configurations(inverter, battery, pair), upper_kwh
        )
        if picked:
            fits.append(BatteryFit(*picked))

    def key(fit: BatteryFit) -> tuple[bool, float, bool, int, int]:
        config = fit.config
        size = config.usable_kwh if fit.above else -config.usable_kwh
        return (
            fit.above,
            size,
            config.pair.verdict != "released",
            config.quantity,
            config.battery.id,
        )

    return sorted(fits, key=key)


def battery_choice(fit: BatteryFit, locale: Locale) -> BatteryChoice:
    config = fit.config
    return BatteryChoice(
        product=ref(config.battery),
        quantity=config.quantity,
        stacks=config.stacks,
        usable_kwh=config.usable_kwh,
        above_upper_limit=fit.above,
        release=release(config.pair, locale),
    )


# Inverters -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Evaluation:
    inverter: Product
    checks: list[eligibility.Check]
    layout: strings.StringLayout | None
    backup_parts: list[Requirement]
    batteries: list[BatteryFit]

    @property
    def eligible(self) -> bool:
        return all(check.passed for check in self.checks)


def evaluate(
    engine: Engine,
    inverter: Product,
    request: ResidentialInput,
    sizing: htw.Sizing,
    existing: bool,
) -> Evaluation:
    kwp = request.pv_kwp
    checks: list[eligibility.Check] = []
    backup_check, backup_parts = eligibility.backup(
        inverter, request.backup, engine.compatibility
    )
    layout: strings.StringLayout | None = None
    if existing:
        # A retrofit keeps the installed inverter and its array; only the battery is new.
        checks.append(eligibility.phase(inverter, request.phase))
        if backup_check:
            checks.append(backup_check)
    else:
        checks.append(eligibility.application(inverter))
        checks.append(eligibility.phase(inverter, request.phase))
        limit = eligibility.single_phase_limit(inverter)
        if limit:
            checks.append(limit)
        checks += [
            eligibility.pv_input(inverter, kwp),
            eligibility.dc_ac_ratio(inverter, kwp),
        ]
        if backup_check:
            checks.append(backup_check)
        result = strings.layout(
            inverter, [p.kwp for p in planes_of(request)], engine.catalog.module
        )
        layout = result.layout
        checks.append(
            eligibility.Check(
                result.reason or "string_count",
                layout is not None,
                layout.module_count if layout else None,
            )
        )
    batteries: list[BatteryFit] = []
    if sizing.recommended or existing:
        batteries = battery_options(engine, inverter, sizing.high_kwh)
        checks.append(
            eligibility.Check("battery_release", bool(batteries), len(batteries))
        )
    return Evaluation(inverter, checks, layout, backup_parts, batteries)


def related_accessories(engine: Engine, evaluation: Evaluation) -> list[ProductRef]:
    """Products the documents name around the chosen inverter and its released batteries."""
    accessories: list[Accessory] = [
        accessory
        for kind in ("meter", "backup", "parallel_controller")
        for requirement in engine.compatibility.requirements(
            evaluation.inverter.model, kind
        )
        for accessory in requirement.accessories
    ]
    accessories += [
        a for fit in evaluation.batteries for a in fit.config.pair.accessories
    ]
    found: dict[int, ProductRef] = {}
    for accessory in accessories:
        product = _accessory_product(engine, accessory)
        if product:
            found.setdefault(product.id, ref(product))
    return list(found.values())


def system_key(
    evaluation: Evaluation, kwp: float
) -> tuple[float, bool, float, bool, int, int]:
    """Rank whole systems: AC power closest to the array (to 0.1 kW), then the battery.

    The battery ranks as in `battery_options`: within the HTW limit the
    largest, above it the smallest; a plain release before one with an
    accessory; fewer pieces; finally the inverter's product id for a stable order.
    """
    ac = evaluation.inverter.ac_power_kw
    gap = round(abs(ac - kwp), 1) if ac is not None else math.inf
    if not evaluation.batteries:
        return (gap, False, 0.0, False, 0, evaluation.inverter.id)
    fit = evaluation.batteries[0]
    config = fit.config
    size = config.usable_kwh if fit.above else -config.usable_kwh
    return (
        gap,
        fit.above,
        size,
        config.pair.verdict != "released",
        config.quantity,
        evaluation.inverter.id,
    )


def find_existing(engine: Engine, model: str) -> Product | None:
    wanted = model.strip().upper().replace(" ", "")
    for product in engine.catalog.in_class(*INVERTER_CLASSES):
        if product.model.upper().replace(" ", "") == wanted:
            return product
    return None


# Stückliste ----------------------------------------------------------------------------


def _accessory_product(engine: Engine, accessory: Accessory) -> Product | None:
    matches = engine.catalog.by_model_pattern(accessory.model)
    return matches[0] if matches else None


def stueckliste(
    engine: Engine,
    evaluation: Evaluation,
    fit: BatteryFit | None,
    request: ResidentialInput,
    upper_kwh: float,
    existing: bool,
) -> list[Line]:
    locale = request.locale
    inverter = evaluation.inverter
    lines: list[Line] = []
    if not existing:
        chosen = request.inverter_id == inverter.id
        lines.append(
            Line(
                role="inverter",
                product=ref(inverter),
                quantity=1,
                unit="pcs",
                label=t("line.inverter", locale),
                basis=[
                    t("basis.chosen", locale)
                    if chosen
                    else t("basis.ranked", locale, kwp=request.pv_kwp)
                ]
                + [
                    t("basis.meter_in_box", locale, text=condition.get(locale))
                    for requirement in engine.compatibility.requirements(
                        inverter.model, "meter"
                    )
                    if requirement.included
                    for condition in requirement.conditions
                ],
                documents=documents_of(inverter, "datasheet", locale),
            )
        )
    if fit:
        lines += _battery_lines(engine, fit, locale, upper_kwh)
    if not existing:
        lines += _requirement_lines(engine, inverter, request, evaluation.backup_parts)
        if evaluation.layout:
            lines += installer_lines(evaluation.layout, engine.catalog, locale)
    return lines


def _battery_lines(
    engine: Engine, fit: BatteryFit, locale: Locale, upper_kwh: float
) -> list[Line]:
    config = fit.config
    basis = [
        t(
            "basis.battery_above" if fit.above else "basis.battery_fit",
            locale,
            upper=upper_kwh,
        )
    ]
    if config.modular:
        if config.quantity == 1:
            basis.append(t("basis.module.one", locale))
        else:
            basis.append(
                tn(
                    "basis.stacks",
                    config.stacks,
                    locale,
                    quantity=config.quantity,
                    stacks=config.stacks,
                )
            )
    basis += [condition.get(locale) for condition in config.pair.conditions]
    lines = [
        Line(
            role="battery",
            product=ref(config.battery),
            quantity=config.quantity,
            unit="pcs",
            label=t(
                "line.battery_modules" if config.modular else "line.battery_units",
                locale,
            ),
            basis=basis,
            documents=docs(config.pair.documents),
        )
    ]
    for accessory in config.pair.accessories:
        product = _accessory_product(engine, accessory)
        if not product:
            continue
        per = {"system": 1, "stack": config.stacks, "unit": 1}[accessory.per]
        lines.append(
            Line(
                role="accessory",
                product=ref(product),
                quantity=accessory.quantity * per,
                unit="pcs",
                label=t("line.accessory", locale),
                basis=[
                    t("basis.accessory_per_stack", locale, quantity=accessory.quantity)
                ]
                if accessory.per == "stack"
                else [],
                documents=docs(config.pair.documents),
            )
        )
    return lines


def _requirement_lines(
    engine: Engine,
    inverter: Product,
    request: ResidentialInput,
    backup_parts: list[Requirement],
) -> list[Line]:
    locale = request.locale
    lines: list[Line] = []
    meters = [
        r
        for r in engine.compatibility.requirements(inverter.model, "meter")
        if not r.included and (r.phase is None or r.phase == request.phase)
    ]
    groups: tuple[tuple[Role, str, list[Requirement]], ...] = (
        ("meter", "basis.meter_documented", meters),
        ("backup", "basis.backup_accessory", backup_parts),
    )
    for role, basis_key, requirements in groups:
        for requirement in requirements:
            for accessory in requirement.accessories:
                product = _accessory_product(engine, accessory)
                if not product:
                    continue
                lines.append(
                    Line(
                        role=role,
                        product=ref(product),
                        quantity=accessory.quantity,
                        unit="pcs",
                        label=t(f"line.{role}", locale),
                        basis=[t(basis_key, locale)]
                        + [c.get(locale) for c in requirement.conditions],
                        documents=docs(requirement.documents),
                    )
                )
    return lines


def installer_lines(
    layout: strings.StringLayout, catalog: Catalog, locale: Locale
) -> list[Line]:
    """What the installer supplies, sized from the reference layout."""
    module = catalog.module
    total = layout.total_strings
    fused = [g for g in layout.strings if g.fuses]
    module_basis = [
        tn(
            "basis.modules",
            total,
            locale,
            count=layout.module_count,
            wp=module.pmax_w,
            strings=total,
            length=layout.modules_per_string,
        ),
        t("basis.no_fuses", locale)
        if not fused
        else t(
            "basis.fuses",
            locale,
            fuses=layout.fuses,
            mppts=", ".join(str(g.mppt) for g in fused),
        ),
    ]
    module_docs = documents_of(module, "datasheet", locale)
    cable_m = rules.DC_CABLE_M_PER_STRING.value
    pairs = rules.CONNECTOR_PAIRS_PER_STRING.value
    lines = [
        Line(
            role="pv_module",
            product=None,
            quantity=layout.module_count,
            unit="pcs",
            label=t("line.pv_module", locale, model=f"{module.brand} {module.model}"),
            basis=module_basis,
            documents=module_docs,
        ),
        Line(
            role="mounting",
            product=None,
            quantity=1,
            unit="set",
            label=t("line.mounting", locale, count=layout.module_count),
            basis=[],
            documents=[],
        ),
        Line(
            role="dc_cable",
            product=None,
            quantity=total * 2 * cable_m,
            unit="m",
            label=t("line.dc_cable", locale),
            basis=[tn("basis.cable", total, locale, strings=total, length=cable_m)],
            documents=[],
        ),
        Line(
            role="connector",
            product=None,
            quantity=total * pairs,
            unit="pairs",
            label=t("line.connector", locale),
            basis=[tn("basis.connectors", pairs, locale, pairs=pairs)],
            documents=[],
        ),
    ]
    if fused:
        low = math.ceil(rules.STRING_FUSE_RATING_MIN.value * module.isc_a)
        high = math.floor(rules.STRING_FUSE_RATING_MAX.value * module.isc_a)
        lines.append(
            Line(
                role="string_fuse",
                product=None,
                quantity=layout.fuses,
                unit="pcs",
                label=t("line.string_fuse", locale, low=low, high=high),
                basis=[
                    t(
                        "basis.fuses",
                        locale,
                        fuses=layout.fuses,
                        mppts=", ".join(str(g.mppt) for g in fused),
                    )
                ],
                documents=[],
            )
        )
    lines.append(
        Line(
            role="ac_protection",
            product=None,
            quantity=1,
            unit="set",
            label=t("line.ac_protection", locale),
            basis=[],
            documents=[],
        )
    )
    return lines


def string_result(layout: strings.StringLayout, catalog: Catalog) -> StringLayoutResult:
    module = catalog.module
    return StringLayoutResult(
        module=f"{module.brand} {module.model}",
        module_wp=module.pmax_w,
        modules_per_string=layout.modules_per_string,
        module_count=layout.module_count,
        array_kwp=layout.array_kwp,
        voc_cold_v=layout.voc_cold_v,
        vmp_hot_v=layout.vmp_hot_v,
        groups=[
            StringGroup(
                mppt=g.mppt,
                strings=g.strings,
                modules_per_string=g.modules_per_string,
                fuses=g.fuses,
            )
            for g in layout.strings
        ],
    )


# Design -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Design:
    """Everything the response and the report are written from."""

    request: ResidentialInput
    place: geo.Place
    yield_: YieldResult
    use: htw.ConsumptionRange
    sizing: htw.Sizing
    sizing_rules: list[RuleResult]
    metrics: MetricsResult | None
    selected: Selection | None
    candidates: Candidates
    rules: list[RuleResult]
    warnings: list[str]
    relaxations: list[str]


def _sizing_rules(
    sizing: htw.Sizing, request: ResidentialInput, use: htw.ConsumptionRange
) -> list[RuleResult]:
    locale = request.locale
    single = use.low_kwh == use.high_kwh
    per_mwh: float | str = (
        sizing.cap_per_mwh_low
        if single
        else f"{sizing.cap_per_mwh_low}–{sizing.cap_per_mwh_high}"
    )
    mwh = (
        fmt(use.low_kwh / 1000, locale)
        if single
        else (f"{fmt(use.low_kwh / 1000, locale)}–{fmt(use.high_kwh / 1000, locale)}")
    )
    out = [
        RuleResult(
            id=rules.HTW_MIN_KWP_PER_MWH.id,
            passed=sizing.recommended,
            value=sizing.kwp_per_mwh,
            limit=rules.HTW_MIN_KWP_PER_MWH.value,
            label=t("rule.htw_min_pv", locale),
            text=value_text(
                "htw_min_pv",
                sizing.kwp_per_mwh,
                rules.HTW_MIN_KWP_PER_MWH.value,
                locale,
            ),
        ),
        RuleResult(
            id=rules.HTW_MAX_KWH_PER_KWP.id,
            passed=None,
            value=sizing.cap_per_kwp,
            limit=rules.HTW_MAX_KWH_PER_KWP.value,
            label=t("rule.htw_max_per_kwp", locale),
            text=value_text(
                "htw_max_per_kwp", sizing.cap_per_kwp, None, locale, kwp=request.pv_kwp
            ),
        ),
        RuleResult(
            id=rules.HTW_MAX_KWH_PER_MWH.id,
            passed=None,
            value=per_mwh,
            limit=rules.HTW_MAX_KWH_PER_MWH.value,
            label=t("rule.htw_max_per_mwh", locale),
            text=value_text(
                "htw_max_per_mwh",
                fmt(sizing.cap_per_mwh_low, locale)
                if single
                else f"{fmt(sizing.cap_per_mwh_low, locale)}–{fmt(sizing.cap_per_mwh_high, locale)}",
                None,
                locale,
                mwh=mwh,
            ),
        ),
    ]
    if sizing.reserve_kwh:
        out.append(
            RuleResult(
                id="backup_reserve",
                passed=None,
                value=sizing.reserve_kwh,
                limit=None,
                label=t(
                    "rule.backup_reserve",
                    locale,
                    load=request.backup_load_kw or 0,
                    hours=request.backup_hours or 0,
                ),
                text=value_text("backup_reserve", sizing.reserve_kwh, None, locale),
            )
        )
    return out


def _relaxations(
    evaluations: list[Evaluation], request: ResidentialInput, existing: bool
) -> list[str]:
    locale = request.locale
    failed = {check.id for e in evaluations for check in e.checks if not check.passed}
    out: list[str] = []
    if existing:
        out.append(t("relax.existing", locale))
    if request.phase == 1 and failed & {"phase", "single_phase_limit"}:
        out.append(t("relax.phase", locale))
    if request.backup == "needed" and "backup" in failed:
        out.append(t("relax.backup", locale))
    if request.backup != "none" and "backup" in failed:
        out.append(t("relax.backup_none", locale))
    if "pv_input" in failed:
        inputs = [
            e.inverter.pv_input_kw
            for e in evaluations
            if e.inverter.pv_input_kw is not None
            and all(c.passed for c in e.checks if c.id in ("application", "phase"))
        ]
        if inputs:
            out.append(t("relax.kwp", locale, kwp=max(inputs)))
    return out


def design(engine: Engine, request: ResidentialInput) -> Design:
    locale = request.locale
    place = geo.lookup(request.plz)
    if place is None:
        raise DesignInputError("plz", f"unknown postcode {request.plz}")
    latitude = request.location.latitude if request.location else place.latitude
    longitude = request.location.longitude if request.location else place.longitude
    planes = planes_of(request)
    yield_ = estimate_yield(engine.pvgis, latitude, longitude, planes, locale)

    use = htw.consumption(
        request.annual_kwh, request.heat_pump, request.electric_vehicle
    )
    reserve = (
        htw.backup_reserve(request.backup_load_kw, request.backup_hours)
        if request.backup != "none"
        else 0.0
    )
    sizing = htw.size(request.pv_kwp, use, reserve)
    warnings: list[str] = []
    if not sizing.recommended:
        warnings.append(t("warn.no_storage", locale))
    if request.backup != "none" and not reserve:
        warnings.append(t("warn.backup_reserve_missing", locale))

    existing_product: Product | None = None
    if request.existing_inverter:
        existing_product = find_existing(engine, request.existing_inverter)
        if existing_product is None:
            warnings.append(
                t("warn.existing_unknown", locale, model=request.existing_inverter)
            )
    existing = request.existing_inverter is not None

    if existing:
        pool = [existing_product] if existing_product else []
    else:
        pool = engine.catalog.in_class(*INVERTER_CLASSES)
    if request.inverter_id is not None and not existing:
        if request.inverter_id not in engine.catalog.by_id:
            raise DesignInputError(
                "inverter_id", f"unknown product {request.inverter_id}"
            )
    evaluations = [
        evaluate(engine, inverter, request, sizing, existing) for inverter in pool
    ]
    eligible = sorted(
        (e for e in evaluations if e.eligible),
        key=lambda e: system_key(e, request.pv_kwp),
    )
    chosen = next(
        (e for e in eligible if e.inverter.id == request.inverter_id), None
    ) or (eligible[0] if eligible else None)

    candidates = Candidates(
        inverters=[
            CandidateInverter(
                product=ref(e.inverter),
                ac_power_kw=e.inverter.ac_power_kw,
                battery=battery_choice(e.batteries[0], locale) if e.batteries else None,
            )
            for e in eligible
        ],
        batteries=[battery_choice(fit, locale) for fit in chosen.batteries]
        if chosen
        else [],
        accessories=related_accessories(engine, chosen) if chosen else [],
        excluded=[
            Excluded(
                product=ref(e.inverter),
                failed=[rule_result(c, locale) for c in e.checks if not c.passed],
            )
            for e in evaluations
            if not e.eligible
        ],
    )

    selected: Selection | None = None
    metrics: MetricsResult | None = None
    if chosen and (chosen.layout or existing):
        fit = None
        if chosen.batteries:
            fit = next(
                (
                    b
                    for b in chosen.batteries
                    if b.config.battery.id == request.battery_id
                ),
                chosen.batteries[0],
            )
            if fit.above:
                warnings.append(
                    t(
                        "warn.battery_above",
                        locale,
                        upper=sizing.high_kwh,
                        usable=fit.config.usable_kwh,
                    )
                )
        selected = Selection(
            inverter=ref(chosen.inverter),
            inverter_rules=[rule_result(c, locale) for c in chosen.checks],
            battery=battery_choice(fit, locale) if fit else None,
            strings=string_result(chosen.layout, engine.catalog)
            if chosen.layout
            else None,
            lines=stueckliste(engine, chosen, fit, request, sizing.high_kwh, existing),
        )
        usable = fit.config.usable_kwh if fit else 0.0
        # A backup reserve is held back in daily operation (HTW Berlin's storage
        # sizing recommendations, rules.HTW_PAPER; planner-methods.md section 2.2(b)).
        cycling = max(0.0, usable - sizing.reserve_kwh)
        figures = htw.metrics(request.pv_kwp, use, cycling)
        outside = (
            figures.outside_table
            or use.low_kwh < rules.HTW_TABLE_MIN_KWH.value
            or use.high_kwh > rules.HTW_TABLE_MAX_KWH.value
            or request.heat_pump
            or request.electric_vehicle
        )
        if outside:
            warnings.append(t("warn.outside_table", locale))
        metrics = MetricsResult(
            usable_kwh=cycling,
            autarky_range=Range(low=figures.autarky[0], high=figures.autarky[1]),
            self_consumption_range=Range(
                low=figures.self_consumption[0], high=figures.self_consumption[1]
            ),
            without_storage_autarky_range=Range(
                low=figures.autarky_without[0], high=figures.autarky_without[1]
            ),
            without_storage_self_consumption_range=Range(
                low=figures.self_consumption_without[0],
                high=figures.self_consumption_without[1],
            ),
            basis=t("metrics.basis", locale),
        )
        ac = chosen.inverter.ac_power_kw or 0.0
        if ac > rules.NA_PROTECTION_KVA.value:
            warnings.append(t("warn.na_protection", locale))
    elif existing_product and not any(e.batteries for e in evaluations):
        warnings.append(
            t("warn.no_battery_release", locale, model=existing_product.model)
        )

    sizing_rules = _sizing_rules(sizing, request, use)
    all_rules = sizing_rules + (selected.inverter_rules if selected else [])
    return Design(
        request=request,
        place=place,
        yield_=yield_,
        use=use,
        sizing=sizing,
        sizing_rules=sizing_rules,
        metrics=metrics,
        selected=selected,
        candidates=candidates,
        rules=all_rules,
        warnings=warnings,
        relaxations=[] if selected else _relaxations(evaluations, request, existing),
    )


def storage_result(design: Design) -> StorageResult:
    sizing = design.sizing
    return StorageResult(
        recommended=sizing.recommended,
        usable_kwh_range=Range(low=sizing.low_kwh, high=sizing.high_kwh)
        if sizing.recommended
        else None,
        upper_kwh=sizing.high_kwh,
        backup_reserve_kwh=sizing.reserve_kwh,
        basis=design.sizing_rules,
    )


def result(design: Design, written: Report) -> ResidentialResult:
    """The response body: the design and its report."""
    return ResidentialResult(
        status="solution" if design.selected else "no_candidate",
        yield_=design.yield_,
        storage=storage_result(design),
        metrics=design.metrics,
        selected=design.selected,
        candidates=design.candidates,
        rules=design.rules,
        warnings=design.warnings,
        relaxations=design.relaxations,
        report=written,
    )

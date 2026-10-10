"""Battery quantities a released pair allows, by the stacking figures of the datasheets.

A battery product is either a module that stacks (its datasheet gives a
smaller minimum than maximum modules per stack: BU2-5.0 1-5, GW6.0-BAT-D 1-6)
or a complete unit (B2-10.0 is two modules in one set, so its minimum equals
its maximum). Modules are ordered one by one; complete units by the unit. The
release can narrow the module range (Pylontech lists a Force-H3 stack of 3 to
7 modules for one inverter), and an inverter or system maximum caps the total.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .catalog import Product
from .compatibility import PairResult


@dataclass(frozen=True)
class BatteryConfig:
    battery: Product
    quantity: int
    stacks: int
    usable_kwh: float
    pair: PairResult
    modular: bool


def _module_range(battery: Product, pair: PairResult) -> tuple[int, int] | None:
    low, high = battery.modules_per_stack or (1, 1)
    if pair.modules:
        low, high = max(low, pair.modules[0]), min(high, pair.modules[1])
    return (low, high) if low <= high else None


def configurations(
    inverter: Product, battery: Product, pair: PairResult
) -> list[BatteryConfig]:
    """Every quantity of `battery` the datasheets and the release allow on `inverter`."""
    usable = battery.usable_kwh
    if usable is None or not pair.released:
        return []
    stack_range = _module_range(battery, pair)
    if stack_range is None:
        return []
    low, high = stack_range
    stacks_max = battery.stacks_parallel_max or 1
    modular = (
        battery.modules_per_stack is not None
        and battery.modules_per_stack[0] < (battery.modules_per_stack[1])
    )
    if not modular:
        return [
            BatteryConfig(battery, units, units, round(units * usable, 2), pair, False)
            for units in range(1, stacks_max + 1)
        ]
    caps = [high * stacks_max]
    for cap in (battery.modules_per_system_max, _inverter_module_cap(inverter)):
        if cap:
            caps.append(cap)
    total_max = min(caps)
    out = []
    for modules in range(low, total_max + 1):
        stacks = math.ceil(modules / high)
        if modules < stacks * low or stacks > stacks_max:
            continue
        out.append(
            BatteryConfig(
                battery, modules, stacks, round(modules * usable, 2), pair, True
            )
        )
    return out


def _inverter_module_cap(inverter: Product) -> int | None:
    from . import units

    return units.count(inverter.value("max_battery_modules"))


def pick(
    configs: list[BatteryConfig], upper_kwh: float
) -> tuple[BatteryConfig, bool] | None:
    """The largest configuration within `upper_kwh`, else the smallest above it (flagged True)."""
    if not configs:
        return None
    within = [c for c in configs if c.usable_kwh <= upper_kwh + 1e-9]
    if within:
        return max(within, key=lambda c: (c.usable_kwh, -c.quantity)), False
    return min(configs, key=lambda c: (c.usable_kwh, c.quantity)), True

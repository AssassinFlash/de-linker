"""Execute the separately installed official PySAM physical module.

Only checks Coulomb integration, VI power, retained state and SOC clamping.
It does not compare/validate the complete custom MILP dispatch model.
"""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / ".runtime"))
import PySAM.BatteryStateful as BatteryStateful


def model(mode: int = 0):
    value = BatteryStateful.default("LFPGraphite")
    value.Controls.assign({"control_mode": mode, "dt_hr": .25, "input_current": 0, "input_power": 0})
    value.ParamsCell.assign({"initial_SOC": 50, "minimum_SOC": 15, "maximum_SOC": 95})
    value.setup()
    # setup() outputs zero placeholders for Q/V. A zero-current initialization
    # step yields an actual physical state before comparing deltas.
    value.execute()
    return value


def main() -> None:
    rows = []
    m = model()
    before = m.StatePack.export()
    m.Controls.input_current = 1
    m.execute()
    after = m.StatePack.export()
    expected_q = before["Q"] - after["I"] * .25
    expected_power = after["V"] * after["I"] / 1000
    assert abs(after["Q"] - expected_q) < 1e-7
    assert abs(after["P"] - expected_power) < 1e-7
    rows.append({"name": "official_current_charge_and_vi_power", "before": before, "after": after,
                 "expected_q_ah": expected_q, "expected_power_kw": expected_power,
                 "charge_residual_ah": after["Q"] - expected_q,
                 "power_residual_kw": after["P"] - expected_power})

    m = model()
    before = m.StatePack.export()
    m.Controls.input_current = .01
    states = []
    for _ in range(100):
        m.execute()
        states.append(m.StatePack.export())
    after = states[-1]
    integrated_ah = sum(s["I"] * .25 for s in states)
    expected = before["Q"] - integrated_ah
    assert abs(after["Q"] - expected) < 1e-7
    assert after["last_idx"] > 96
    rows.append({"name": "official_25h_state_continuity", "before": before, "after": after,
                 "current_integral_ah": integrated_ah, "expected_q_ah": expected,
                 "residual_ah": after["Q"] - expected,
                 "states": states})

    m = model(mode=1)
    before = m.StatePack.export()
    m.Controls.input_power = 1000  # deliberately impossible request, kW DC
    m.execute()
    after = m.StatePack.export()
    assert 0 <= after["P"] < 1000
    assert after["SOC"] >= 15 - 1e-7
    rows.append({"name": "official_command_is_not_delivered_power", "before": before,
                 "request_power_kw": 1000, "after": after,
                 "actual_power_is_clamped": True,
                 "note": "The physical model enforces its SOC/current/voltage state. This is not an actual commercial SKU power rating."})

    # Capture nominal input parameters alongside effective physical state.
    # ParamsPack nominal fields remain model inputs; they must not be mistaken
    # for a measurement of delivered energy or the live SOC denominator.
    m = model()
    rows.append({"name": "official_configuration_readback", "params_pack": m.ParamsPack.export(),
                 "state": m.StatePack.export(), "cell_state": m.StateCell.export(),
                 "note": "Nominal input fields and effective Q/Q_max/temperature state have distinct meanings. Do not treat nominal kWh × SOC as a measured deliverable-energy guarantee."})
    library = Path(BatteryStateful.__file__)
    result = {"distribution": "nlr-pysam", "version": version("nlr-pysam"),
              "module": "PySAM.BatteryStateful", "default_config": "LFPGraphite",
              "platform": platform.platform(), "python": platform.python_version(),
              "module_binary_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
              "scope": "four physical-module checks only; no SAM dispatch, no complete MILP equivalence, no SKU/field acceptance",
              "power_boundary": "battery DC terminals; no PCS or AC conversion in BatteryStateful",
              "checks": rows}
    (BASE / "official-crosscheck-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"version": result["version"], "checks": [r["name"] for r in rows],
                      "first_charge_residual_ah": rows[0]["charge_residual_ah"],
                      "25h_residual_ah": rows[1]["residual_ah"],
                      "requested_kw": 1000, "actual_kw": rows[2]["after"]["P"],
                      "actual_soc": rows[2]["after"]["SOC"]}, indent=2))


if __name__ == "__main__":
    main()

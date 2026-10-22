# Unified planner: continuous single-AC-bus replay

2026-10-23. Implements the explicitly bounded physical replay in
`docs/research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md` §§5–8.
This is an internal component of the full planner, not a second customer tool
or a reduced end-to-end delivery. It is not yet mounted as a public API.

## Input and model boundary

1. Interval-average gross/critical load, available AC PV and separate system
   auxiliary demand have the exact same real-time axis and mode schedule.
   Net import cannot substitute for gross load. Measured PV after curtailment
   cannot silently substitute for available generation potential. Each frame
   retains gross/critical measurement scope; that identity cannot disappear
   when profiles become numeric frames.
2. The named `constant_window_single_ac_bus_v1` model consumes an explicit usable
   internal kWh window, AC charge/discharge kW, separate directional efficiencies,
   internal auxiliary kW, standing-loss rate per hour, and a pinned parameter
   asset hash. Zero-valued losses are explicit scenario parameters, not facts
   silently assigned to every SKU. No DOD is applied twice to usable capacity.
3. This domain is a single AC bus and one battery with fixed window/power and
   efficiencies. It excludes battery export and does not release unmodeled
   DC/shared-port, thermal, phase, switching, black-start or controller behaviour.
   The capability compiler and applicable-country/model assessments must prove
   the actual configuration is within this domain before product release.

## Physical and control behaviour

4. State is continuous across all intervals, dates and mode changes. No midnight
   or outage full-battery reset exists. A gap/reversed horizon is rejected.
5. Standing internal loss is `E*(1-exp(-rate*dt))`, followed by constant internal
   auxiliary demand, before AC flow in this model. Actual withdrawal is bounded
   by available energy; missing internal auxiliary supply is reported. This
   explicit simplified loss ordering is not a universal electrochemical model.
6. Simultaneous charge/discharge commands on this device are invalid. The
   actuator bounds delivery by power, usable energy/headroom, efficiency,
   reserve and real load/PV/grid availability before advancing state. Requested
   but undelivered power remains visible; no post-state clamp claims supply.
7. Allocation priority is declared: PV serves customer load, then separate AC
   auxiliary demand; battery discharge serves remaining load then auxiliary;
   grid serves remaining load, auxiliary, then explicitly allowed grid charging.
   Surplus PV charges, exports within the cap, then curtails. There is no
   battery-to-export path. Every source/sink is recorded separately.
8. Import/export limits and reserve are mode-specific, explicit inputs. Outage
   has zero grid import/export; PV is available only when that mode is explicitly
   enabled. A normal dispatch state is inherited by the next outage interval.
9. `self_consumption_with_reserve` is a local executable baseline using this
   same state, headroom, direction efficiencies and reserve. It does not promise
   future peak feasibility. A provided feasible schedule and a greedy policy's
   replay are different evidence; ideal feasibility and real EMS support must
   be separately established.
10. Terminal inventory requirements are explicit. A one-off event may consume
    its stated initial inventory; a repeatable/cyclic task must satisfy its
    required terminal inventory. Capacity cannot stand in for discharge power
    or conversion losses/recharge time.

## Sources, metrics and verification

11. Internal PV/grid/initial-unknown inventories use declared proportional
    mixing. Standing loss, internal auxiliaries and discharge consume those
    same sources proportionally. Charge adds its actual source after charge
    efficiency; PV-origin discharge to load is reduced by discharge efficiency.
    Grid/unknown energy never becomes solar contribution.
12. Solar autarky is `(PV direct load + PV-origin battery to load)/gross customer
    load demand`, including unserved demand in that denominator. Input-side PV
    self-use is `(PV direct load + direct system auxiliaries + PV charge input)/
    generated PV after curtailment`. It includes storage conversion losses and
    inventory input, not just solar energy eventually delivered to load.
    Available-PV onsite share uses available generation before curtailment as
    its separate denominator. No battery export is in this metric domain.
    Critical-only or mixed gross/critical periods expose their requested-demand
    solar share, but return whole-site gross load/autarky as undefined with a
    scope reason. Critical-circuit performance is not whole-site self-sufficiency.
13. Metrics expose import/export/curtailment, initial/final source inventories,
    conversion/standing/auxiliary losses and shortages. Zero denominators return
    a named undefined reason, not NaN or invented 0/100%. Maximum interval mean
    import is labelled as such, not as a verified instantaneous/meter-window peak.
14. A separate verifier must not call the policy/actuator/source-withdraw
    implementation. It checks AC and internal energy balance, source balances
    and proportional allocations, discharge conversion, nonnegative flows,
    load/aux supply, usable window, power, charge/discharge exclusivity, reserve,
    mode limits, command delivery, continuity and terminal requirements. It
    retains residuals/violations, thresholds and witness interval indices.
    Command checks independently verify `actual+unmet=requested` and actual
    not above requested. Internal shortage must be nonnegative, and actual
    internal auxiliary supply equals the smaller of its demand and inventory
    after standing loss; a reported shortage cannot cancel fictitious use.
    Independently reconstructed `min` equations enforce the fixed allocation
    priority in §7 at the actual delivery already constrained by independent
    energy/power/reserve/source/command checks, including PV and
    battery load/auxiliary order, grid load/auxiliary/charge order, and PV
    charge/export/curtail order. Energy balance alone cannot certify this model.
    Short-interval delivery is checked in kW as well as kWh: actual discharge
    must correspond to removed source energy, source withdrawal must fit local
    post-loss stock above reserve, per-source transitions must not manufacture
    future inventory, and internal auxiliary shortage retains its power meaning.
    Absolute kWh tolerance cannot authorize a high-power supply from zero stock.
    Local float64 ULP budgets are propagated through those comparisons, exposed
    separately in each check's arithmetic allowance, and never added as a
    physical capacity/power margin or a minimum time interval.
    The three pre-charge proportional withdrawals also retain their source
    mixing meaning in kW; a small amount cannot be relabelled from grid to PV
    merely because its kWh residual is small. Charging requires actual local
    headroom at its interval power. Auxiliary shortage has independent signed
    account and nonnegative power checks. The first state must exactly match
    the separately supplied frozen initial input, and each subsequent source
    state exactly inherits the previous after-state: assignment/JSON round-trip
    introduces no new arithmetic and receives no energy tolerance budget.
    The verifier independently rejects an over-capacity frozen initial input.
    Capacity, reserve and terminal inventory are hard physical/task boundaries;
    a generic absolute kWh or relative-times-capacity allowance is not usable
    there. An exact rational net-flow witness tracks recorded transfers without
    accumulating stock ULPs from idle frames or exact cycles. Tracked-state
    checks expose their actual deviation from this witness. The conserved
    terminal witness has a final representation ULP, independent of prefix
    length; no estimated roundoff pool can restore an uncharged cycle. A small
    real energy deficit cannot be called restored reserve or a repeatable cycle.
15. Numerical tolerances are explicit, serialized software parameters. They do
    not represent field precision or engineering safety margins. Task execution,
    replay constraint satisfaction, equipment evidence and model applicability
    remain separate judgements. A failing policy replay is no proof that every
    possible policy/configuration is infeasible. Initial inventory is strictly
    bounded by the physical window. Intermediate states may carry float64
    residuals within the same explicit tolerance used by the verifier; their
    inventory/sources are not clamped away, and capacity residuals remain visible.

## Independent acceptance cases

The fixed numerical reference includes cross-midnight 80 AC kWh/85.1063829787
internal kWh at .94, recharge 11.3173381621 AC kWh for 10 delivered with .94
both ways, PV-limited 55.2% solar contribution, 20 kWh with insufficient 5 kW
outage power, grid/unknown source exclusion, greedy-vs-feasible dispatch and
non-reusable backup reserve. The implementation tests preserve these expected
values rather than importing previous sizing algorithms.

A clearly marked synthetic 8760-interval volume fixture independently expects
8760 customer kWh, 2007.5 solar-load kWh and 6752.5 grid kWh. It is an analytic
volume test, not European weather, SKU validation or a production load test.
500 irregular intervals verify continuous energy/source constraints. Tampered
supply/reset traces must fail the independent verifier. Full native-resolution
peak tasks, ideal optimization, PV/electrical/geometry/equipment/country facts
and site/HTTP consumers remain in the same active delivery and are required
before overall production acceptance.

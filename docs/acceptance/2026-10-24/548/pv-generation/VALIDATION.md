# Explicit roof/weather PV reference and durable energy integration

This is a backend increment of the still-active unified-workbench goal. It is
not complete planner, engineering-accuracy, equipment/country release, native
workflow or production acceptance. The local p548 page keeps its previous
runtime; this increment has not been installed into that running instance.

## Reviewed source and retained facts

The fixed base is `b5b89ee387fb55d85ad57ae7b4a0b9f8de65ea03`; source pin
`94d4b31c169a4e04197b9b33d6dcadd70d54e3a1` implements
[the PV-generation specification](../../../../specs/548-pv-generation.md).
The independent axes and any corrections are recorded in `REVIEWS.md`.

The only new full-year weather original is the 1,268,118-byte JRC TMY acquired
through Apify, SHA-256
`5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`.
[Primary research and acquisition provenance](../../../../research/2026-10-24-pv-generation/WEATHER-AND-MODELS.md)
retain the provider response, month-year choices, meteorology and reported
irradiance-time offset. These are actual weather bytes; the roof, component
ratings, thermal/conversion parameters and load/battery scenarios in the tests
are explicit fixtures, not customer or manufacturer-qualified designs.

## Verification

`source-pin.json` binds the final checks to the source. `commands.json` records
the actual command, working directory, exit status and elapsed time. Exact
stdout and the complete JUnit case list are retained. `initial-checks/` keeps
the earlier cbadc619 run separately; it is not relabelled as the final source.

| Check | Result at the source pin |
| --- | --- |
| Complete engine test suite | 672 passed, 50.31 seconds reported by pytest |
| Planning source and tests lint | Passed |
| Planning source and tests format | 121 files already formatted |
| Strict planning source types | No issues in 92 source files |

The 57 new focused cases cover the pure generation chain, TMY adapter and
owned-profile/actual-worker integration. Independent Spec review reran those
57 cases; it does not replace the full regression above.

The independent analytic checks include horizontal POA = 500 W/m²,
PVWatts DC = 2,944 W for ten 400 W modules at 800 W/m² and 45 °C with
gamma = −0.004/°C, SAPM cell temperature = 44.11703066106086 °C,
and shared-converter AC = 960 W for two 1,000 W DC arrays against a
1,000 W conversion reference. Explicit 2% and 3% DC losses leave factor
0.9506. Numeric examples and the pinned model contracts are sourced by
the specification and research; none defines a site-accuracy tolerance.

The original complete TMY runs through actual included panel poses, POA,
optical factors, SAPM, PVWatts DC and one conversion curve per shared group.
All 8,760 output values are finite and nonnegative. The original selected-year
source dates plus exactly 661.68 seconds determine solar geometry; the
separate synthetic 2023 UTC energy axis retains an explicit reconstruction.
This is a typical-weather scenario, not observed 2023 generation.

One integration case uses real private SQLite/CAS, owned assets, the actual
durable Worker and the complete 8,760-interval continuous-energy kernel.
Its synthetic 10 kW load is above the explicit 9.6 kW conversion cap, with
zero auxiliary demand and no battery: 87,600 kWh total load is independently
known; all modelled solar goes directly to load and grid import is the exact
remainder. The fixture verifies the energy ledger and all four PV dependency
roles, without promoting the scenario into equipment or country approval.

The same case queues a run, edits/saves the roof, rejects a new calculation
using its stale profile, then completes the already frozen run as historical.
Further cases cover real load-source replacement without PV invalidation,
parameter invalidation, ownership before byte publication, first-receipt
idempotency under a changed resource policy, wrong consumption roles, altered
model bundles despite unchanged metadata stamps, and missing witness bytes.

The all-zero-irradiance branch is evaluated before Perez's undefined clearness
ratio; nonzero invalid weather still fails rather than receiving NaN-to-zero
repair. The actual initial undefined-ratio diagnosis led to this explicit
physical branch. Original individual zero weather values remain intact.

## Runtime and resource preservation

`preservation.json` compares the previous accepted baseline against a read-only
current database query: all 164 baseline project rows remain unchanged. The
one additional synthetic energy project already belongs to the previous
increment. The protected roof is still saved revision 14 with the exact prior
input hash. Runtime policy and the live worker's complete ready record match
the previous acceptance. No source install, restart, live project write,
inquiry, mail, new site instance, worktree or full backup was performed.

Tests use temporary isolated databases and the existing locked engine
environment. One new raw weather body is retained; earlier primary manuals
and library originals are referenced rather than cloned. Current p548 and its
owned worktree remain necessary for the active full goal.

## Remaining full-goal work

The pure unshaded reference is a checkable baseline, not a substitute for the
required detailed near/inter-row shading and electrical methods. Trusted
managed weather/model intake and native source/task presentation still need
integration and EN/DE desktop/mobile proof. Equipment and country packages,
complete BOM/report/PDF, site/Genie/Woo/draft/inquiry consumers, migration,
review-site release and production readback remain in the same goal.

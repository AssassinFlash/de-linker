# PVGIS input component: independent acceptance

2026-10-23. Base `029f51752821079404e8d9672cf5ec0730515f6d`;
implementation `4555b623a13851c16893223ce3344e1410baa29d`;
accepted fix `37198e86d3bb93c41a06360d8d34bbb15a1ded2b`.
This is component acceptance within the still-active complete planner delivery.
No public HTTP, UI, hardware, country or production acceptance is claimed.

Spec: [548-pvgis-inputs.md](../../../specs/548-pvgis-inputs.md),
[numerical contract](../../../research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md)
sections 3–4, and [the primary-source dossier](../../../research/2026-10-23-pv-inputs/PVGIS-SERIES.md).
Research used Apify; both complete 2020 provider originals, source identifiers,
HTTP/MIME evidence, explicit queries and exact SHA-256 are retained. No borrowed
API key or new account permission was used.

## Standards

The independent reviewer archived the fixed commits, rather than testing the
parent's evolving worktree. The initial `4555b623` review found one P2: a legal
JSON integer `10**400` in `P` or `Int` could escape as a raw `OverflowError`.
The parser now performs a protected float conversion, converts overflow to
`InvalidInput`, and then checks finiteness. Two regressions were added.

At final `37198e86`, the reviewer independently tested positive and negative
out-of-range integers in both fields. All four returned the typed error with
the original cause retained. The fixed archive passed **183 planning tests
in 12.76s** with `--locked --no-sync` and offline execution. No residual hard
standard violation or newly actionable smell was found.

The initial review also independently checked all 60 research artifact manifest
entries for size and SHA-256, and the two original-file Decimal integrals. It
found no ownership/use/hash substitution bypass: CSV keeps its frozen TZif,
PVGIS is solar-only and native UTC, and Worker dependencies are rebound to the
selected project asset IDs. Acquisition and rights remain trusted server-side
intake inputs, not authority delegated to a browser.

**Final Standards: pass; 0 residual findings.** The initial P2 remains recorded
as an actual pre-fix failure, not erased by the later passing result.

## Spec

The independent Spec reviewer archived both versions. Initial `4555b623`
passed 181 planning tests in 10.91s and **338 whole-engine tests in 25.10s**;
it independently reproduced the same out-of-range integer failure. Final
`37198e86` passed **340 whole-engine tests in 24.57s**. Two malformed durable
jobs with oversized `P`/`Int` produced `invalid_input` and no result through
the real Worker, rather than `execution_failed` or fabricated zero output.

Additional independent checks confirmed:

- ERA5 full leap-year integration equals the original Decimal sum
  **946.43692 kWh**, with no second 14% loss.
- SARAH explicitly reconstructed and refined to 15 minutes still records
  instantaneous origin, reconstruction history, 3600-second effective native
  resolution and no claim of energy-preserving point-sample conversion.
- Wrong year, missing/duplicated last hour, missing P, nested duplicate fields,
  malformed quality flag, mismatched loss and the actual north-facing
  `−180° → −179°` provider response are rejected.
- PVGIS assets used as load/auxiliary demand and foreign-owned assets fail
  before enqueue. Wrong raw hash, an extra TZif role, unsupported interpretation
  version or Worker model all fail explicitly.
- A legitimate two-hour original-file window survived backup/restore and
  produced the independent **0.61936 kWh** expectation.

The parent also exercised the full 8784-hour actual ERA5 input through owned
asset → frozen run → registered Worker → continuous energy verification and
result, with a distinctly synthetic constant 1 kW gross load, zero auxiliary
load and no battery. Independent expectations were load **8784 kWh**, solar
to load **946.43692 kWh**, grid import **7837.56308 kWh**. The project was edited
after enqueue; the old run retained revision 2 and its original input/source
hashes. Root Ruff, formatting and strict mypy passed for the changed component.

**Final Spec: pass; 0 residual findings.** No other reproducible omission,
unrequested behaviour or wrong implementation was found within this component.

## Actual limits of this evidence

This establishes source format/identity handling, explicit modelling semantics,
provenance and owned durable execution. The complete originals are two public
Berlin/2020 requests; other probes check specific provider metadata/capabilities.
They do not prove every European location/year or a customer's field accuracy.
The valid ERA5 and reconstructed SARAH results are modelled scenarios, not
measured generation. The provider's actual `Unknown` response has no P in any
of its 8784 rows and has degenerate zero temperature/wind fields; it is not an
alternate usable PV/weather source.

Specific equipment, DC/shared ports, site shading, country rules, official
acquisition transport, WP/native identity, UI/report/commerce consumers and
the complete site migration/readback remain in the same active delivery scope.
Nothing here is a substitute for those implementations and their acceptance.

Review axes remain separate: **Standards 0 residual; Spec 0 residual**. Both
originally found the same P2 typed-error failure; both verified its repair.

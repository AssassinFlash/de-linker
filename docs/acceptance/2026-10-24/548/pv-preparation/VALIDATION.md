# Managed PV preparation and immutable output preview

This is a backend checkpoint of the active unified-workbench delivery. It is
not native workflow, complete engineering capability or production acceptance.
The running p548 page retains its previous accepted version; this increment
has not been installed into that instance.

## Source and primary evidence

Base `79632d0e9eaa04423aec7c736d93dbe5d1351082`; initial source
`0deef6efb4132e448d388922ae8760674a62f117`; corrected source
`a14567de149e79c837d2053ae67073b1d62c413e`.
The [managed-preparation specification](../../../../specs/548-pv-preparation.md)
records both this checkpoint and the required stages still in the same goal.
Separate review axes and corrections are in [REVIEWS.md](REVIEWS.md).

[New primary research](../../../../research/2026-10-24-pv-managed-intake/FINDINGS.md)
was acquired through one successful Apify run with an explicit numeric build
pin. It retains official run/input/dataset/file-download contracts and original
manufacturer/library evidence. No additional full weather year was fetched:
tests reuse the already retained JRC original with SHA-256
`5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`.
The roof, loads, battery and generation parameters in integration cases are
explicit synthetic scenarios; they are not manufacturer-qualified systems.
The original Trina coefficient and SAPM construction/mounting facts in the new
research are evidence for subsequent model controls, not claims that the
synthetic parameters were replaced with those manufacturer facts.

## Implemented behavior

Trusted retained TMY intake checks ownership before parsing/publication and
verifies the original against explicit request, capture and time interpretation.
The saved revision selects an owned weather asset. Private `/runs/pv` enqueues
the frozen roof/parameter/weather/runtime task; it performs no PV calculation.
A registered numerical executor generates all 8,760 values and retains the
input bundle and full witness. A result cannot become a project's owned asset
until the same fenced transaction commits its successful run. Cancelled,
expired and foreign-project completion cannot publish an asset/result.

The real managed worker now dispatches both energy and PV kernels through
exact registered execution keys. Optional PV policy is explicit; old
energy-only runtime policy remains readable. HTTP, worker startup and CLI
identity use one executor-set factory. Existing routing-cache reconstruction,
receipts, historical runs, guest transfer and backup dependency retention apply.

Profile preview reads the existing model-input/witness artifacts and original
weather through hash-verified storage. Cross-bindings, complete axis, output
values, reconstruction policy and energy are checked before projection. It
runs no solar/transposition/temperature/DC/AC model. Full physical reproduction
continues in the worker when the profile is used by an energy calculation.

## Verification at the corrected source

`source-pin.json`, `commands.json`, exact stdout and full JUnit case list bind
these checks to the source. `initial-checks/` separately retains the initial
685-case run; it has not been relabelled as the corrected 691-case result.

| Check | Result |
| --- | --- |
| Complete engine regression | 691 passed; pytest 66.53 seconds |
| Planning source/test lint | Passed |
| Planning source/test format | 130 files already formatted |
| Strict planning types | No issues in 100 source files |

The 19 newly added cases include an actual independent worker-host process
executing both task types, full-year PV preparation followed by energy use,
incompatible work left unclaimed, private command/receipt/error boundaries,
cancellation after calculation, expired/replacement/late attempts, publication
rollback under a real SQLite trigger fault, foreign-project rejection, guest
ownership transfer, historical roof edits and actual backup/restore.

The full-year reuse has a separately known 87,600 kWh synthetic load, no
storage and zero auxiliary demand. Available PV serves that load and grid
supplies the remainder. The preview test then disables `generate_pv` in all
three entry modules and verifies the retained output's full document plus
actual first/tail HTTP pages. Corruption checks reject broken binding, missing
values, negative power, changed energy, changed time policy and forged inputs.

## Instance and resource preservation

[Read-only preservation](preservation.json) confirms all 164 baseline projects
unchanged, with only the previously existing synthetic energy project in
addition. The protected roof remains revision 14 with its exact previous
input hash. Runtime policy and the complete live worker ready record match
the previous acceptance; the worker process remains alive.

No live database write, source install, restart, mail, inquiry, production
write, new site instance, new worktree or full backup occurred. Existing locked
engine dependencies were reused. Temporary tests use isolated SQLite/CAS and
stop their own subprocesses. Retained primary evidence is bounded; no site
copy was made for research or review.

## Continuing full-goal work

Fresh Apify acquisition and its durable ambiguous-start/recovery journal,
native source/model/task controls, explicit selection of prepared profiles,
EN/DE desktop/mobile walkthroughs and paired local installation are still
required in this goal. They have not been implemented by this checkpoint.
Detailed near/inter-row shading, electrical/equipment/country methods,
BOM/report/PDF, site/Genie/Woo/draft/inquiry consumers, migration, review-site
release and production readback also remain in the same complete delivery.

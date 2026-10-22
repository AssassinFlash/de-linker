# Profile interpretation increment review

2026-10-23. Independent fixed-source Spec and Standards re-review pending.
This is the private/native data-interpretation service, not complete path A
or a completed upload UI or engineering qualification.

The code audit found that CSV parsing already rejected bad data, but the HTTP
adapter dropped its reason and line, returning only invalid_input. CsvIssue
now exposes bounded code/physical-start-line/mapped-role diagnostics without
private values. The adapter still returns no exception message or trace.
Multiline records are explicitly tested: the diagnostic points at the record's
starting physical line rather than the reader's ending line. Accumulated
energy overflow is converted to a typed input refusal before asset publication.

The new owned preview reads the same original bytes and pinned interpretation
used by calculations. It reports full-series coverage, gaps, signed energy,
interval-mean range and resolution, with paged intervals and bounded gap samples.
CSV, ERA5 model means and SARAH reconstructed samples retain their distinct
source/transformations. It neither fills gaps nor turns a metadata parse into
an engineering release. Pinned TZif preview works after current host name
availability is removed. A different owner is refused before profile parsing.

Implementer checks:

- 314 planning fixtures passed in 14.88s. New cases cover safe detailed HTTP
  failures, blank/quoted record semantics, overlap/sign/overflow, full-series
  versus page summary, explicit gaps, exact source identity, private ownership,
  strict page bounds, signed net import and both actual captured JRC originals.
- Strict mypy over 64 planning modules and targeted ruff/format passed.
- Native PHP suite: 289 tests, 2357 assertions; WPCS and PHPStan passed.
- A new real p548 native HTTP fixture passed in 2.19s (other 12 deselected).
  Actual guest cookies/nonces imported the synthetic CSV and read its preview:
  900 gap seconds, 3 kWh covered energy and 8 kW full-profile maximum mean,
  while its first page contains 4 kW. Another guest received 404. A malformed
  private-cell fixture returned the safe timestamp issue and line 2, with no
  bad source publication or private value in the reply. No mail was sent.
- Planner strict types/build passed after adding the new allowlisted read path.
  UI consumes no fabricated sample or hidden provider default.

The native local service was restarted from the owned checkout for this HTTP
fixture. Production was not changed. Frontend upload/column preview/mapping,
localized errors and unknown upload recovery remain current implementation
obligations in the same delivery, alongside the other workbench paths.

Both independent axes rejected fixed `807149a2` for one reproducible P2:
finite signed net-import powers `1e308` and `-1e308` over two-hour intervals
produce mixed infinite integral terms; `math.fsum` raises `ValueError`, which
was not covered by the initial `OverflowError` conversion. Actual ASGI returned
500 rather than the contracted typed 422. Neither source nor TZif was published.
The correction maps both arithmetic failure forms to the same safe refusal,
without clipping powers or removing negatives. Regression exercises the parser
and actual ASGI for positive and mixed-sign overflow and asserts no new blobs.
Targeted tests: 116 passed; full planning tests: 317 passed in 15.08s; ruff and
format passed. These checks do not replace independent re-review.

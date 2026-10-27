# Geographic intake Spec review — a0d12a9f FAIL

Fixed target`a0d12a9f68b17db3ebade24bace5eb8a890c6e3f`, base`787728224cd3b20aec63ca7c5a36471a3e9ea22f`. ThreeP2 implemented-wrong findings; no separate scope creep or missing UI requirement counted. The increment is the geographic/API/domain seam, not the fullA–D or map/drawing/provider/UI release.

## 1. Horizontal geographic fold/conditioning

Spec`548-geographic-intake.md:16–28,38–51` distinguishes fullENU/zero-height conventions and requires unsupported positions/numerical results to fail explicitly. `geometry_import.py:128–130` instead drops curvatureUp and accepts E/N alone without a chart applicability check.

Actual private ASGI with anchor`(0,0)`, h0=0, flat plane relativeUp5 accepts a Polygon from longitude`179.99990..179.99999`,latitude`0...00009`and publishes an owned asset. Roof area is`99.70348384173016m²`, but roof UV lies only`1.113..11.132m`from origin. The full source ENU's curvatureUp is`-12,756,273.999990284m`. Candidate full inverse is approximately`(.0001°,0°,5m)`, about`20,003,931m`from its original. A near-horizon`89.99990..89.99999°`patch is also accepted, area`9.5713e-5m²`instead of the local comparison's≈100m². Finite/UV-grid checks do not prevent this geographic fold/conditioning error. FullPROJ forward/inverse itself is not the failure.

See`probe_geographic_edges.py/.results.json`for actualASGI source/candidate values. The first two pytest counterexamples require explicit refusal for back-facing/unsupported horizon inputs; both are red on this fixed source. No arbitrary engineering distance/radius threshold is proposed by the test.

## 2. AbsoluteUp destroys local projection

Speclines26–28 require the3-4-5 slope and explicit unsupported results. In`geographic.py:134–139`and browser`geographic.ts:150–154`, absolute planeUp is constructed then subtracted again. For a valid declared plane`origin=[0,0,1e15],u=[1,0,0],v=[0,.8,-.6]`, horizontal`[0,.1]`must yield`UV=[0,.125]`: simply N=.8V. Both implementations return`[0,.08000000000000002]`. Pure translation inUp changes a local metric answer. All values are finite and inside the public number range. A support refusal would be honest; the silent wrong result is not.

`test_spec_geographic_counterexamples.py`checks the analyticPython result; `probe_plane.test.mjs`records Up0/10/1e9/1e15 and independently fails the browser helper. This is arithmetic correctness, not a source/survey accuracy claim or a re-audit of accepted panel/packing physics.

## 3. Current source hash can contradict its bound original

Speclines59–60 say “Source.reference_sha256 unambiguously references the raw original”; lines71–75 require source/manifest association while permitting later geometry/source notes.

`geometry_import_selections.py:38–55`checks current sourceID exists and candidate sourceID matches, but never compares the current source's reference hash to its selected asset. ActualASGI import→attach succeeds; a later note-only revision succeeds as a positive control. Changing only the current Source.reference_sha256 to64zeros then also saves200, while geometry_imports still binds the original asset and `/assets/content` hashes to`47770a0dc5034b54743dd2da28d1c855e2c8c047c7678d3688215d8e89d9eebc`. Existing SourceForm exposes this field atline28. Original asset metadata is not changed; the project's pointer now contradicts it. The fourth Python assertion is red.

## Passed independent boundaries

18new target Python and6new domain tests pass. An additional15-case ASGI malformed-input matrix rejects duplicate JSON, malformed/CRS, bool/unsafe/exponent-overflow/invalid-Unicode IDs, string/bool/3D coordinates, bad closure and nonunit/nonorthogonal/vertical planes with422 and no published bytes. Exact HTTP receipt/replay succeeds under a conversion-constructor fault injection; changed intent409, foreign malformed source404, missing original503. These are real private factory/SQLite/CAS/PROJ executions with synthetic service credentials, not WordPress or browser acceptance.

## Reproduce

Run`python3 rebuild_snapshot.py`in this directory; no dependency installation is needed. Existingvenv/node_modules are symlinked. Then:

```sh
services/engine/.venv/bin/python run_review_checks.py
PYTHONPATH=services/engine/src services/engine/.venv/bin/python probe_geographic_edges.py
PYTHONPATH=services/engine/src services/engine/.venv/bin/python probe_parser_and_replay.py
```

`run_review_checks.py`writes exact logs and expects the fixed source's18+6green,4Python red,1browser red outcomes. Its own success means that expected evidence was reproduced, not that the product passed. Individual commands are in`check_runs.json`. Runtime fixtures are self-created and automatically removed; original probes/results/logs remain. First ASGI setup needed fixeduv.lock for immutable RuntimeSnapshot capture; that harness omission was corrected before reported results.

No parent source/native/prototype/production edits or browser actions occurred. Root's accepted proposed fixes and future geometric-model changes were not implemented or marked verified here. Known UI/native/full-goal obligations remain separate.

# Fixed geometry checker4 Spec evidence

Target `bc80334b7b29553f24e0c75de3c2e6781493066e`; full base `8791c933fca452fc7d6922deb91b1bd4691eb81b`; patch base `d7deddf74295f4e6b3042a3b96dd6b78f3e47c51`. Verdict: PASS for the fixed geometry service/shared-model increment. No remaining missing/partial, scope-creep or incorrectly implemented requirement was found within this scope. Native editor/renderers and full B/whole-tool acceptance remain separate and were not asserted.

Only unique probes/results remain after SHA-verified reclamation. Restore the exact minimal source/spec/fixtures with `python3 rebuild_snapshot.py`. Every blob is SHA256 checked; existing changed files are never overwritten. Dependencies are symlinked, not copied. No acceptance or large research directories were archived. The parent worktree, p548 and production were untouched.

From this root use:
`PYTHONPATH=services/engine/src /Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/services/engine/.venv/bin/python -B <probe.py>`
for unchanged `probe_geometry_support.py`, `probe_geometry_touch.py`, `probe_geometry_numeric.py`, `probe_geometry_periodic.py`, `probe_geometry_domains.py`, and new `probe_geometry_topology.py` / `probe_geometry_footprint_parity.py`.

The old touch probe intentionally still prints centre-plus-corners GEOS intersection areas from the old construction as historical diagnostics. Its authoritative `geometry_status` and conflict kinds now correctly permit contact; checker4 uses the new shared `footprint_uv` and analytic within-array topology. Do not treat the old diagnostic areas as the current classifier's footprints.

`probe_geometry_topology.py` independently intersects high-precision local rectangles rather than copying the implementation's row-separation formula. All27 cases passed: flat contacts, positive row gaps, thick adjacent/nonadjacent rows at30/45/90deg, different columns, exclusions, cross-array shared edges, actual positive-area duplicate arrays, excluded duplicate arrays. These are synthetic mathematical fixtures, not independent engineering certification.

After the Python parity generator, run `node probe_geometry_footprint_parity.mjs` from `apps/planner`:16 cases,768 coordinates, max difference0. `node probe_geometry_rebase_support.mjs` confirms unmodified prior failure probes explicitly throw `GeometryPrecisionError`. Existing Node tests: `node --test src/domain/geometry.test.ts` passed11.

Python tests from `services/engine`:
`PYTHONPATH=src:tests/planning /Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/services/engine/.venv/bin/python -B -m pytest -p no:cacheprovider --basetemp=../../.pytest-geometry-tests -q tests/planning/test_geometry.py tests/planning/test_private_http.py tests/planning/_probe_geometry_http.py tests/planning/_probe_geometry_support_http.py` passed157 (151 fixed+6 independent).
New runtime identity fixture: same command using `--basetemp=../../.pytest-geometry-runtime -q tests/planning/_probe_geometry_runtime_http.py` passed1. It verifies actual private ASGI runtime_sha256 equals EnergyKernel runtime, checker4 returned and caller body cannot override identity.

The unchanged actual5000-slot/200000-candidate probe returns explicit incomplete;5001 is refused. Concave roof, holes, whole thickness, sloped extrusion and zero-clearance keepout contact pass. This is one local bounded execution, not production-capacity evidence. No browser/native instance, production service, email or customer data was used.

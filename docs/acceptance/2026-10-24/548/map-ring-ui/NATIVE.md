# Native boundary editing and shared project readback

This is an increment of the active whole-workbench goal, not whole-product or
production acceptance. The final application/source pin is
`6b2a8a4cc43c95d4710fcb42f16d1bd1e4a8c100`. Computer Use operated the existing
p548 WordPress page at port 9347 and its real planning service at port 9348.
There was no injected SDK, calculation response, geometry or browser fixture.

The one owned synthetic project is `82a84c56e50c4efb8497d1bfbe106bd1`, named
`Köln · owned synthetic roof · acceptance`. Its brief is commercial. Its source
explicitly describes generated geometry, unknown spatial accuracy and permission
to retain/export the generated geometry. It is not a measured building or an
engineering reference result.

## Actual editing and persistence

| Target | Native action and actual result | Saved comparison |
| --- | --- | --- |
| Roof boundary | EN desktop pointer drag; pause/reload/open saved drawing; required source confirmation; real check; common Undo/Redo; Save project | v5 to v6: only boundary vertex 2 changed |
| Roof opening | EN desktop pointer drag outside parent roof; DE phone recovery and explicit check refused it; original project stayed v6; desktop correction reset confirmation; second check and Save succeeded | v6 to v7: only opening vertex 1 changed |
| Obstacle footprint | Normal DE numeric form created a synthetic obstacle with 0.8 m vertical extrusion; saved v8; native map pointer changed one corner; real check and Save | v8 to v9: only footprint vertex 3 changed |
| Keep-out footprint | Normal DE form created a synthetic area with an explicit test-only reason; saved v10; native map pointer changed one corner; real check and Save | v10 to v11: only footprint vertex 2 changed |

The running server's SQLite revisions and content-addressed blobs were read
without writing. Each blob's bytes were checked against its SHA-256. The roof
and opening comparisons retain the full synthetic inputs in `native-project-v5`,
`v6` and `v7.json`; the obstacle/keep-out receipts retain their exact before/after
objects and revision/blob hashes. Equality checks removed only the one edited
footprint field before comparing the entire remaining input. Roof planes,
sources, permission, obstacle height/extrusion, keep-out reason, other objects
and other project inputs were exactly unchanged by each boundary edit.

The invalid-opening attempt left the server at revision 6, hash
`0174544639e774e0fda588dc6324188ff9c402c6125a3f0336bcf3867082ff91`.
The actual German refusal focused the result and retained the four editable
corners. This exercised the repaired parent-invalid gate through the real
geometry service, as well as the independent engine-backed probes.

The final saved revision is 11, hash
`4bf62b8f25d736062d07963c86e36e3f1b9eb7894449170645c09b89862232d9`.
An actual reload and language change retained that project/revision. Its plan,
map and native WebGPU 3D view used the same project. These rendering checks
establish common geometry and actual execution, not measurement accuracy,
shading analysis, structural/electrical approval or equipment release.

## Property links, phone layout and evidence quality

Native reload of `#lp-map-ring-properties` originally opened overview with no
design workspace. The route repair now initializes design/Map. Final native
reload at revision 11 is recorded in `native-anchor-v11.json` and
`de-desktop-anchor-reload-v11-full.txt`. Separate real React tests cover both
public property fragments and preserve the user's later Plan/Map selection.

The earlier `anchor-reload-before.txt` and `anchor-reload-after.txt` contain
short AX diffs, not complete state; they cannot independently prove the route.
The later full AX and DOM readback supply that evidence. No full snapshot was
retroactively attributed to the earlier files.

Literal AX text and the original independent failing terminal output retain
their captured trailing spaces (16 lines). They are data, not source formatting
changes. The source increment's diff check is clean; the staged artifact check
reports only these named captures. VALIDATION.json distinguishes the two checks.

Browser viewport capability set actual 1440x1000 and 390x844 surfaces. Manual
device-metric overrides were cleared after a screenshot/backing-surface mismatch
was found. The final German phone source/refusal and English phone/desktop
captures use normal native `getScreenshot`, not document crops. A misframed
intermediate English source screenshot was removed with a small metadata record.

At 390 px the German source grid was one column (318 px), document scroll width
was 390 px, and the source heading settled at 210 px below the 194 px fixed
header/project bar. The refusal was brought into view and focused. A smooth
anchor scroll was allowed to settle before recording its position. English phone
navigation, saved revision 11, full 3D rendering and source-language copy were
also read back. Synthetic names/source notes remain user-entered data and were
not machine-translated.

This record does not claim a full EN/DE x size x every-state matrix, physical
touch hardware, provider failure paths or whole-European engineering coverage.
Those remain requirements of the active whole goal. Existing-boundary edits are
the scope here; creating arbitrary new openings, obstacles and keep-out shapes
on the map remains part of the same unfinished implementation.

## Whole-product identity

The owner's clarification concerns the entire Solution Configurator. Current
native EN/DE disclosure was reopened without changing the project: the product
is `Solution Configurator · by Linker` / `Lösungskonfigurator · von Linker`.
Linker's project workflow is explained before subordinate software/data credits.
Map attribution remains attached to its own role. This implements the existing
`548-product-identity.md` contract; no new public claim was added in this native
increment. Current desktop/phone screenshots are retained here.

The final product explanation must include accepted system calculation,
equipment selection and proposal/report delivery as those paths are completed.
The current project/editing wording neither announces those as already accepted
nor removes them from the full product obligation.

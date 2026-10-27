# Standards review: saved solar settings

Source: `cf951e3d2219015c65943e0fc21b74b55bac7b0a`.
Accepted base: `367640fcf09eba92eb77b8e61aaedaa6957cdd7b`.
Reviewed the complete cumulative diff and both commits, including schemas, generator, new TS→ASGI contract regression, copy artifacts and generated modules. Authority: current main-repository `AGENTS.md`, owned `CONTEXT.md`, accepted isolated-runtime ADR and package configurations. No nearer contributing/coding-standard file exists. The Spec axis was not read.

**[P3] Add provenance for the form's copied numeric bounds.** `apps/planner/src/components/energy/WeatherForm.tsx:52–53,66–67,110–111,124–125,213–214` introduces coordinate bounds `±90`/`±180` and repeats years `1…9998` without a source comment. Current main `AGENTS.md` §4 explicitly requires “每个数字与阈值必须有来源注释.” These values agree with the exported `weather-acquisition.schema.json` coordinate definitions and `Year`; the defect is missing traceability, not incorrect validation. Add a source comment naming those definitions, or derive the bounds from the contract. This also keeps a technical calendar limit distinct from provider-year availability.

No further material documented-standard violations or Fowler-baseline smell findings. Incomplete drafts, strict compiled contracts, project/session fencing and the shared durable start path retain their separate responsibilities. New source has no secret/model/private-control indicators, and native gateway/identity PHP is unchanged. The browser fixture explicitly simulates saving and transport without claiming installation or acquisition acceptance.

Independent checks in `standards-tests.txt`: eight solar compiler/domain tests, one actual shared-controller DOM test and one TS→ASGI save test pass; all four exported schemas equal the backend generators. All 99 approved literals occur in actual source and generated JS and agree with PO, MO, planner JSON and installed WordPress i18n, including placeholders. All 158 source and seven build hashes match frozen blobs; five modules parse and 55 named imports resolve. Added-line legacy-identifier scanning has no hits.

An uncached default strict mypy run checks 159 files but reports three followed-import errors in two unchanged older tests. Raw failure is retained; existing type debt is not waived or counted as a new source finding.

Only the two owned review artifacts were written. The temporary contract store was removed. This review does not accept native installation, live acquisition, deployment or the complete #548 goal.

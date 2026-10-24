# Native weather and PV task consumers

This is one implementation increment within the full unified Solution
Configurator goal. Residential and commercial projects, European country
coverage, released equipment, complete parts lists, reports/PDF, site entry
points, commerce, deployment and production readback remain required. This
increment does not constitute that delivery or replace any of those requirements.

## Product contract

The common project owns weather acquisition, roof-derived PV preparation and
energy replay as separately identified tasks. The frozen manifest identifies
each task even before it has a result. A history page must not parse weather or
PV output as battery/energy metrics. Existing saved browser intents must remain
recoverable under their current IndexedDB database and store identifiers.

Native WordPress exposes only the declared weather/PV starts and owned weather
status reads, alongside existing energy operations. Provider credentials,
arbitrary URLs, operator acknowledgement/resume/stop and identity controls stay
private. The three starts share the existing calculation admission quota and
receipt-before-quota replay mechanism. No live credential is bundled in the app.

Successful output must agree with the project, revision, manifest, runtime,
pinned inputs, owned prepared asset and published source records. A queued
acknowledgement must already agree with its declared task model. Source
preparation never automatically selects or saves its result. One explicit
selection changes the appropriate role in the current open draft and preserves
unrelated later edits; native Save project persists that selection. PV selection
invalidates an already prepared energy replay. Changed geometry, weather
selection or PV parameters cannot acquire an older PV result. A changed or
removed weather request cannot acquire its earlier weather result. Source
verification failure must not assert that the customer's roof changed.

Uncertain starts retain the exact original revision, operation and request key.
They block replacement requests across task kinds. Explicit retry sends the
same bytes. Current native identity must be checked again before transport and
selection; late responses cannot regain former authority.

Weather progress distinguishes a provider request from retained validated
original data and a published project source. READY is waiting, RUNNING is
processing, ABORTING/TIMING-OUT are not confirmed terminal states, SUCCEEDED
alone is not a usable project source, and an unknown start cannot be repeated
automatically. The browser reads the local owned journal, with bounded visible
polling during active local work or maintenance; it never polls the provider.

PV output remains an unshaded reference profile. Equipment release, country
requirements and near shading remain explicitly unassessed. Dates are displayed
in the active locale with UTC stated; numerical generation stays server owned.
Source/task checksums are expandable technical details, not a claim of accuracy.

## Scope and integration gates

The source/model input forms, their native start controls, production credential
wiring, paired HTTP/worker/schema upgrade and full native end-to-end acquisition
are still required by the full goal. Existing weather/PV backend specifications
continue to govern those tasks. This increment supplies their shared durable
transport, typed readers, history, status and explicit result consumers. It does
not represent a completed customer acquisition workflow.

The current local project store remains schema 2 until that paired upgrade is
ready. Do not restart a mutable worktree HTTP process with the newer schema
against the protected project merely to render these components. The isolated
visual fixture uses actual worker-published result views, retained weather,
synthetic roof/model inputs and a simulated provider adapter; it has no live
mutation transport. Its EN/DE × 1440/390 renders prove component behavior and
wrapping only, not native identity, live data acquisition or production support.

The application-wide product identity remains Solution Configurator / by Linker
and Lösungskonfigurator / von Linker. Linker's contribution is described at system
level before narrower component and source credits. No unaccepted capability is
advertised as already available. Required provider attribution stays in its
corresponding surface.

Verification combines real worker/publication fixtures, browser durability and
selection tests, bounded owned mixed-history HTTP tests, native gateway route
tests, independent Spec/Standards review, reviewed EN/DE copy and Computer Use
component rendering. Native paired integration and the complete goal's site,
engineering and deployed acceptance gates remain distinct.

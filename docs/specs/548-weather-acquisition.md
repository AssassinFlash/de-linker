# Durable Apify weather acquisition

This is part of the same complete unified-workbench delivery. The retained-TMY
path is already accepted as a backend checkpoint. Fresh acquisition must use
the owner's Apify channel and produce the same trusted source, not a second
weather interpretation or an HTTP-side PV calculation.

## Request and provider authority

Build the official PVGIS 5.3 TMY request from typed coordinates, selection
years, expected database, horizon and separately declared synthetic time axis.
No customer chooses a provider URL, Actor, build, request headers, crawl code,
storage destination or credential. Pin the previously exercised Actor/build;
all execution, transport, decoded-byte and retry budgets are explicit policy.
Reject a leap-year scenario before starting an external operation.

Before POST, commit an intent bound to the immutable local run and exact plan.
Only the current task lease may issue that intent. The worker atomically
consumes its start permit immediately before the one POST. An intent whose
permit was never consumed can safely resume; rereading a consumed permit
never grants another POST.
After permit consumption, crash-before-send and lost-acknowledgement are indistinguishable
without provider evidence. Do not automatically repeat the POST after either.

Persist the first verified remote run ID/acknowledgement immediately. Retrying
an acknowledged operation polls or reads that same run. A late acknowledgement
may still be retained after cancellation or lease loss: it records a real
external side effect and enables cancellation/recovery; it cannot publish a
project asset or a successful local result. Provider identity/storage changes
conflict. Progress and terminal observations are retained without allowing a
late nonterminal observation to erase a terminal fact.

## Capture and recovery

Only a succeeded pinned run can supply data. Verify its effective INPUT against
the submitted plan. Read a bounded dataset; require exactly the expected file
record, official target URL, HTTP status and media type. Only fetch a record
from that run's own key-value store through the fixed Apify origin, privately
authenticated and without following arbitrary redirects. Enforce decoded-byte
bounds while streaming; never trust wire/compressed content length as the
decoded size. Strict original-TMY validation remains the single interpretation.

Retain the exact submitted/effective inputs, verified run, dataset capture,
original raw body, both time axes, model/source policy and attribution. A
completed source capture is immutable and reusable after worker failure.
Its dependency tree and acquisition journal must survive backup/restore and
ownership transfer. Foreign readers/writers receive the existing not-found
behavior. No provider token, signed URL or private account object is stored.

An unacknowledged start stays visibly uncertain. Recovery requires verified
provider run plus matching INPUT; it does not assert that no remote run exists
and does not issue another start. Cancellation attempts a known remote run's
abort and retains observed confirmation; local lease fencing still decides
publication if the remote run finishes concurrently.

## Integration and acceptance

The managed weather executor must use the existing frozen run, worker,
cancellation and atomic owned-asset publication. HTTP queues work and reads
state; provider requests occur outside database write transactions and outside
HTTP. A fetched source is explicitly selected into a saved project revision;
background completion cannot replace current inputs. Native source/task states
and EN/DE 1440/390 acceptance remain required before the paired install.

Test real SQLite/CAS, lease replacement, concurrent begin, lost start reply,
late acknowledgement, cancelled/foreign runs, identity mismatch, immutable
capture, original bytes, backup/restore, bounded HTTP and actual Apify capture.
Primary contracts are retained in
`research/2026-10-24-pv-managed-intake/FINDINGS.md`; application safeguards above
are explicit engineering policy, not claims of provider exactly-once delivery.

## Transport and orchestration checkpoint

The source now includes the fixed-origin authenticated transport, pinned client
and durable acquisition orchestrator, alongside the accepted journal. Requests
are outside write transactions. The transport rejects redirects before reading
their bodies, has no implicit retries, bounds encoded and decoded bytes and
checks lease/cancellation/deadline between raw reads. Connection/read timeouts
are inactivity bounds; DNS/header reads are not advertised as immediately
interruptible or a hard wall-clock guarantee. Per-attempt poll count and the
task attempt count are bounded; the original elapsed deadline survives retries.

Actual submission adds the journal nonce in `startUrls[].userData` and the
explicit User-Agent from the retained successful primary request. This fixed
server-owned submission rule belongs to the immutable code snapshot; it does
not accept customer headers or change the original typed plan representation.
Complete effective INPUT must equal the 51 known-safe pinned-build defaults
overlaid with that exact submission before its original bytes are retained.
Unknown/default changes fail visibly. Temporary dataset access queries are
removed; the retained dataset document is explicitly a selected projection,
with the full received response's hash/byte receipt rather than an exact copy.

Cancelled tasks attempt a known run's abort and retain the actual response.
ABORTING is not ABORTED. A lost old lease does not abort a run being resumed by
its replacement; confirmed cancellation or the shared expired deadline may
trigger cleanup. Cleanup failures keep the known ID and log only the named
failure code; they do not mask the original failure or invent confirmation.
Completed retained captures can be reused after the network deadline without
another provider request, subject to the active local lease fence.

Private recovery reads a supplied known provider ID and verifies the exact
unique nonce-bearing INPUT before acknowledging it. It cannot extend the
original deadline, repeat the start, requeue or publish a task. These are
internal Python primitives; no operator RPC/UI is installed yet.

Two new isolated weather trials exercised the real channel. The first provider
run SUCCEEDED but returned HTTP 200/text-html rejection and was correctly
rejected locally. A separate explicit task restored the known request header
and succeeded with the exact 1,268,118-byte original, SHA256
`5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`.
The nonce echo, full effective INPUT and strict original-TMY interpretation
passed. One docs-only Actor also ran for primary-contract research. No claim
is made that one successful repair establishes availability at every site or
that a header alone caused the difference. Evidence is in
`../acceptance/2026-10-24/548/weather-transport/`.

## Managed execution and durable cancellation integration

Saved `weather_acquisition` inputs declare only the typed official source
request and time interpretation. The deployment owns transport/resource
policy, Actor/build, headers and credential. Private `/runs/weather` freezes
the exact plan, project revision and actual runtime bundle before queuing.
It performs no provider request. One service-registry factory supplies the
energy/PV/weather execution set to HTTP, worker startup and operator identity;
disabled weather policy remains compatible with energy-only configuration.
Installed transport, numerical and geospatial library versions are part of
the runtime identity as well as the source and lockfile.

The weather kernel verifies the complete frozen plan against the run's saved
inputs and its execution settings. It uses the durable acquisition module,
the original-TMY interpreter and the same metadata projection as trusted
weather import. Its prepared owned source commits atomically with successful
evaluation. Cancellation, expired/replaced execution and publication failure
cannot publish it. A retained capture survives a producer crash and can be
published by a valid replacement without another provider operation.

Completion does not change the saved project. Selection uses the existing
explicit project-revision operation to set `pv_preparation.weather_asset_id`.
When saved acquisition choices are present, a selected source must have that
exact request and time interpretation. Changing the request cannot silently
keep a source for another location/year/horizon. The existing managed PV
preparation then consumes the selected source. Historical completion never
replaces current saved inputs.

Private `/runs/weather/status` first verifies current project ownership,
distinguishes not-started tasks, and exposes original task state, provider
observations, capture and cleanup state. It remains readable with acquisition
disabled. The existing receipt endpoint replays a weather command without
context compilation, admission spend or provider work. Foreign/retired readers
and writers retain not-found behavior, including after guest ownership transfer.

Local cancellation and a separate `abort_weather` job are committed in one
transaction. One cleanup job per original run uses the existing leased queue
and explicit original attempt budget. It remains eligible when the producer
is in retry wait, failed or gone. Repeated cancellation cannot cancel or reset
cleanup. Cleanup changes neither the original cancelled evaluation/result nor
project assets. It reads the acknowledged provider identity, attempts abort
when needed and polls for an actual terminal state; ABORTING is not a terminal
success. A provider finishing between read and abort is read back accurately.
Its elapsed budget starts at cleanup admission and persists across retries;
polling/attempt counts remain bounded. Lost abort replies may be reconciled by
reading that same known run, and no cleanup path can start an Actor. Unknown
starts fail visibly pending verified provider recovery rather than guessing
an ID or asserting that nothing was started.

Core SQLite schema 3 adds this job kind. Versions 1 and 2 migrate inside the
same immediate transaction with foreign keys kept on. The queue and its
referencing routing rows retain IDs, attempts, leases, receipts and byte
references. The referencing child is preserved and rebuilt with its parent;
simply deferring a parent DROP was reproduced to fail at commit despite a
clean final foreign-key query and is not used. An injected failure after the
parent DROP must roll back the complete old schema and records. Old archives
are verified before restore and migrate only in their new destination.

This is a paired code/database change. An old schema-2 executable cannot be
used as a code-only rollback after migration. Before installation/release,
quiesce writers, drain compute and cleanup, retain and verify the prior
code/database recovery point, then migrate/read back; rollback must restore
the matching pair while writes remain closed. No live migration is authorised
by a passing isolated fixture alone.

The current integration must be checked through real SQLite/CAS, private HTTP,
the actual managed worker and an independent worker-host process. Provider
responses in integration fixtures are labelled simulated; the original TMY
bytes and prior external-capture evidence remain retained. No new Actor is
required merely to rerun the same protocol fixtures.

The live p548 runtime has not been installed or modified. Native source/model
controls, explicit selection/recovery UI, operator recovery operations and
EN/DE 1440/390 acceptance remain required before the paired installation in
this same complete goal. Detailed engineering and all downstream/production
work remain required; this is not completion of the customer workflow.

## Operator recovery and release quiescence

Operator recovery is admitted privately into the existing leased queue as
`reconcile_weather`, tied to the original run/manifest/plan. The commands are
acknowledge a supplied known ID, observe an acknowledged run, capture its
original, and stop an inactive producer's remote work. CLI admission uses an
explicit storage binding and idempotency key and performs no provider request.
Only a trusted private team identity may admit it; no customer RPC is added.
One pending reconciliation per original run is allowed. Repeating the same
command key returns its original job receipt without admitting another job.

The same managed worker performs recovery even when new weather acquisition
is disabled. It uses the original server-owned transport/source policy and
credential injection, with no customer URL/header/Actor controls. Each explicit
operator job has its own finite created-at elapsed budget and original attempt
count; automatic retries do not reset either. This does not extend the original
acquisition deadline. Known-run observation, polling, stopping and original
capture share one implementation with acquisition and cancellation cleanup.
There is no Actor-start method in the known-run module. A supplied ID must pass
the pinned build and full nonce-bearing INPUT checks before acknowledgement.
Known-run state resolution checks the task fence first; a database outage
cannot replace an already-known cancellation or lease loss.
Capture and stop require a failed/cancelled producer and are checked again by
the worker. Customer cancellation cannot cancel the independent recovery job.

Recovery outputs retain their exact evidence dependencies under that job;
they cannot publish owned assets, set the original run's result, change project
inputs or turn cancellation into success. Retaining a verified original after
the original acquisition deadline is permitted under the explicit recovery
job's budget. It remains evidence until a valid evaluation publishes it.

A separate explicit resume command can requeue a failed original evaluation
only under its matching runtime, with a known acknowledged run, no pending
maintenance and remaining original attempts. Its attempt count, maximum,
deadline, immutable request and manifest never reset. After the original
deadline, the complete verified capture must already be retained. Cancelled
or successful producers and exhausted budgets cannot resume. Admission drain
blocks new evaluation resumes, and their exact receipts remain replayable.

Core schema 4 adds the reconciliation kind and active-operation uniqueness.
Nonempty versions 1–3 migrate with the existing transactional parent/child
queue rebuild; old archives migrate only after verification in their restore
destination. Installation and rollback still require a matching code/database
pair with all writers quiesced, not a code-only fallback.

Release status reads the local queue and issued remote observations from the
same database snapshot. It is quiescent only with admission closed, no pending
compute/report/cleanup/reconciliation and no unknown or last-observed nonterminal
remote starts. ABORTING remains unresolved. Missing/corrupt evidence fails
closed. Local lifecycle draining must consume that decision. For an older
executable lacking remote-aware status, a read-only check must prove its
configured journal issued no starts; it must neither create nor migrate that
database. Issued legacy operations require verified reconciliation.

An unknown start without a verified provider identity remains unresolved.
Operator admission offers no "assume no remote run" override; missing evidence
cannot establish quiescence. The provider identity still has to be obtained
and verified against the issued intent before the known-run operations apply.

Native customer controls, credential wiring for actual installation, EN/DE
1440/390, paired installation and the remaining full delivery remain required.

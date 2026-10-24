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

The live p548 runtime has not been installed or modified. The managed weather
executor/registration, explicit source selection, recovery controls and native
EN/DE 1440/390 acceptance remain required in this same complete goal. This is
a component checkpoint, not completion of the customer acquisition workflow.

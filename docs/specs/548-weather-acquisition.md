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

## Current implementation checkpoint

The current source adds the typed pinned plan, selected provider-run document,
durable intent/one-POST permit, late acknowledgement/progress/abort-reply
records, immutable original capture, owned read projection and backup/restore
references. It reuses the existing task lease fence and original-TMY parser.
The journal only accepts the exact plan already pinned by the immutable run.

No external HTTP client, weather executor, native control or new public/private
RPC has been installed by this foundation checkpoint. No new Actor was started.
The transport/orchestrator, explicit recovery and remote-abort execution,
managed registration, source selection and native acceptance above remain
required work in this same goal. This is not fresh-acquisition completion.

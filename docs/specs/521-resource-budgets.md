# #521: resource admission and actual provider dispatch budgets

Status: implementation in `codex/521-resource-budgets`, stacked on #519. Local
fixtures are evidence for this branch. Production activation and the #511 initial
assessment outlet are part of the planned combined #522 acceptance, before the
whole group is deployed. This document does not claim production protection.

## Basis and retained behavior

Owner decisions in #507/#508, especially #508 comment 6324114050, set the initial
operating allowances below. They are operating choices, not vendor safety limits
or estimates of euros/tokens. Existing behavior comes from specs 13 (Genie), 14
(Solution Configurator), 12 (roof canvas), 519 (shared admission), the real PHP and
Python endpoints, and the existing inquiry/registration prototypes under
`docs/prototypes/2026-10-17-*`.

The mature patterns retained here are the native framework boundaries and the
existing tools: WordPress REST validates arguments and runs permissions before
`rest_dispatch_request`; Woo remains the inquiry/draft writer; existing Genie
failure handling restores the question/files. The source dossiers
`docs/research/2026-10-12-genie-openai-design/DOSSIER.md`,
`docs/research/2026-10-17-knocket/TRIAL.md`,
`docs/research/2026-10-18-judge-remit/`,
`docs/research/2026-10-12-configurator-sources/DOSSIER.md` and
`docs/research/2026-10-21-configurator-rooftop/matrix/matrix.md` support retaining
conversation history, immediate engineering results, and a separate inquiry
handoff. None provides a vendor quota to copy. The numerical allowances are the
owner-approved policy, with the two explicitly identified recommendations below.

## Two separate journals

The #519 WordPress admission journal protects browser/account resource actions.
Its public `off/observe/enforce` mode controls that rollout. A native server
callback context, unavailable from browser JSON, carries action, operation UUID,
input HMAC, binding and receipt. `finally` restores the prior context even when
work throws. In observe mode the browser sends the native nonce/credentials and
a logical UUID when available, without waiting for Cloudflare. Missing browser
client/hash/cookie, new body/file prechecks and shadow-store failure never add a
block to the original native callback; its permissions and validation remain.
Private provider and actual-work gates are independent and remain enforced.
Commerce reads `linker_commerce_public_business_context` before its
native save; it must not debit an already admitted Tools handoff again.

A different, private SQLite journal protects actual provider requests. It lives
on the service host, outside the web root, at the absolute
`LINKER_PROVIDER_BUDGET_PATH`. All Genie workers and the quality worker use the
same persistent path. `LINKER_PROVIDER_BUDGET_MODE=enforce` enables it;
`off` is the explicit rollout setting. Invalid modes, missing paths, storage
errors, corrupt databases and permissive file modes refuse dispatch. A public
`observe` setting cannot bypass this private guard.

| Provider dispatch | UTC-day cap | Source |
| --- | ---: | --- |
| deepseek-flash, official DeepSeek only | 2000 | #508 comment 6324114050 |
| typesafe/jev-1.13, OpenRouter native systemone only | 200 | same decision |
| Runtime gemini-embedding-2 queries, existing OpenRouter route | 2000 | #521 operating recommendation accepted by owner during implementation |

A unit is one admitted provider call attempt, including retries, model tool loops,
vision pages, summaries, translation and quality escalation. It is not a turn,
completion, token, precise API-usage report or exact billed cost. In the rare case where the caller is cancelled while an asynchronous debit is waiting for the SQLite lock, that unused attempt can conservatively occupy one unit. Cancellation never sends the upstream request later. Offline embedding batches/index builds
are excluded from the runtime embedding quota. An already configured query
encoder's refusal is explicit; it never silently switches to another provider or
BM25. The existing no-encoder BM25 role remains.

SQLite `BEGIN IMMEDIATE` commits before sending. An attempt UUID is consumed once.
Duplicate UUIDs return 409; exhaustion returns 429; unavailable protection returns
503. An ambiguous timeout never refunds an actual dispatched request. There is no
network I/O in the database transaction. Only provider, UUID and UTC day are
stored. The current and previous UTC days are retained for bounded storage and
midnight ambiguity. Use a private directory (0700), ledger file 0600; do not put
the ledger in a release directory or recreate it on service restart.

## Actual provider outlet inventory

| Outlet | Guard |
| --- | --- |
| Pydantic AI / AsyncOpenAI, including each tool-loop request | `OpenAITransport`, matching the installed SDK's HTTPX 2 transport |
| Jev understanding HTTPX client, each retry | `Transport("jev", inner)` |
| Photo and rendered PDF-page vision, each retry/page | `Transport("deepseek", inner)` |
| Conversation summary | same DeepSeek transport |
| Quality worker's Jev and DeepSeek escalation | shared `linker_judges.http.post_json` immediately before each urllib send |
| Runtime query embedding | `GeminiEmbedder._embed(runtime=True)`, each urllib attempt |
| PHP automatic German synchronization | private Genie `POST /budget/take` before `wp_remote_post` |
| #511 background inquiry assessment | exact `AsyncTransport("jev", inner)` seam supplied here; real outlet wired and tested on the #522 combined branch |

The PHP translation gateway uses the existing `LINKER_GENIE_SERVICE_TOKEN` /
`GENIE_SERVICE_TOKEN` header, not a new credential. Its private route is absent
from the public Genie/engine proxy whitelist. The PHP guard accepts only a 200
with an integer remaining count. A service configured `off` returns null, so PHP
enforcement fails closed on an inconsistent rollout. There is no permission
retry after a lost gateway response. Translation enters the existing
`TranslationFailed` path: retain prior German and expose the exception in the
existing admin/digest mechanism.

The direction is PHP → Genie for the private debit. Python never calls WordPress
back to obtain a provider allowance; a WordPress → Python → WordPress worker
self-lock is avoided. Initial inquiry classification remains background work:
quota, failure or timeout produces “undetermined”, then normal internal mail,
inside its absolute 10-second window. Customer submission does not wait.

### Exact #511 integration contract for #522

```python
from linker_genie.provider_budget import AsyncTransport
from linker_judges.budget import BudgetError

# Keep the existing remaining-seconds asyncio.timeout around this entire work.
async with httpx.AsyncClient(transport=AsyncTransport("jev", transport)) as client:
    # Existing native systemone endpoint/model and input stay unchanged.
    # Each retry invokes the guarded transport again.
    ...
# BudgetError at any attempt maps to the existing undetermined safe result,
# never a blocked customer submission, guessed classification or model fallback.
```

The async guard moves SQLite waiting to a worker thread, so the caller’s absolute deadline remains effective. A real held-write-lock fixture verifies deadline cancellation and no late upstream dispatch.

`tests/test_provider_budget.py` exercises this async transport, the installed
OpenAI SDK transport, actual durable/multiworker counting, no-refund timeouts,
private endpoint authentication, replay and missing configuration. #522 must
also run the real #511 assessment function with depleted/unavailable budget and
its absolute deadline; a transport test alone does not prove that integration.

## Public resource policy

| Action | Anonymous | Account | Site / concurrency |
| --- | --- | --- | --- |
| Genie turn (text, hero, capsule, browser dictation) | 30/day and 10/10min | 120/day and 30/10min | 500/day; subject 1, site 2 in flight |
| Files | 10/day | 40/day | 100/day |
| Sizing and roof outline/packing, shared recomputation pool | 30/hour | 120/hour | subject 1, site 4 in flight |
| PDF | 10/day | 10/day | 100/day; sizing concurrency pool |
| Conversation creation/deletion/selection/vote and solution save | 500 writes/day | 500 writes/day | 2000 writes/day |

All but the final storage-only row are #508 decision 6324114050. The final row is
#521's recommendation: four lightweight mutations per maximum signed-in turn,
rounded from 480 to 500; the site ceiling follows four times that allowance. It
never spends inquiry or model-turn quota. Reads/list/open-existing-thread are
free. Selecting an existing conversation spends only a storage mutation, no model
turn. The current GET thread endpoint already returns empty instead of creating
a conversation, and retains that behavior.

Identity is #519's first-party browser HMAC plus native account HMAC; IP is never
the primary resource identity. Account allowances retain browser use and import
anonymous spend using the shared journal's existing carry operation. New threads,
hero/dock changes, switching accounts or routes do not reset the site/provider
budgets. A server-selected plan is atomic across all its dimensions.

Existing attachment limits are retained: three files/turn; image 6MiB, PDF16MiB,
CSV1MiB, XLSX6MiB; total20MiB; at most four rendered PDF pages. The PHP raw Genie
body is capped at30MiB to allow base64/JSON headroom. Other resource bodies and
the private engine POST gate use6MiB: the existing largest commercial CSV is4MB,
and report logo's schema ceiling700kB. Existing schema, magic checks and raster
bounds are not widened. Size/count checks precede parsing; the real successful
verification parent must be validated before base64/magic work. Dispatch repeats
that validation atomically. Invalid heavy input cancels only an unused reservation.

Sizing/PDF input is deduplicated for its current verified subject binding, UTC day
and the **actual running engine snapshot**, fetched through private authenticated
`GET /resource/version` before either public or native saved-solution cache lookup.
The private route requires the existing service token and an enabled engine gate;
it is absent from the public EngineProxy whitelist. Health remains readiness only.
EngineVersion validates a64hex response, uses only an in-flight WP_REST_Request
WeakMap cache, and has no transient/option/deployment-constant fallback. Enforce
refuses unavailable/malformed readback even when an old response exists; observe
retains native work without depending on this new handshake.

The engine captures immutable source bytes once at module import. Under a loading
lock it reads feed/compat bytes once and constructs validated Products/Compatibility
from those exact bytes, then hashes source + loaded feed + loaded compatibility in
the same order as the local release algorithm. It never hashes newer disk data
while still serving old in-memory products. A nightly sync-file write does not
relabel an existing worker; the existing restart loads and advertises the new
snapshot without an SSH push to WordPress or a new credential. The local
LINKER_ENGINE_RESOURCE_VERSION constant is an informational deployment stamp,
never authority for cache reuse. Object key ordering
uses #519's canonical input HMAC. The semantic key is the actual JSON body plus
engine route. The full upstream input is nested separately from adapter metadata;
JSON fields that look like form transport remain part of the actual input.
Query/default REST fields not forwarded upstream cannot create
fresh work. The native proxy reads its path from `get_url_params()` so a body or
query `path` cannot turn an unguarded route into an expensive engineering POST. An in-flight duplicate returns an explicit
pending status, and a completed duplicate restores the private native response.
A definite failed pure calculation can be retried under a new explicit operation
UUID, consuming a new recomputation unit. A successful retry updates the existing
canonical private result, so later identical inputs still reuse it. Unknown,
dispatched and business-write outcomes never gain this retry path.
The real database fixture and DE browser run cover failure → same-input explicit
retry → success → canonical reuse; an initial live PVGIS outage exposed this
recovery defect during acceptance and it was fixed in this branch.

The account-only saved-solution read ability can recompute. Its trusted
`linker_tools_engine_request` filter authenticates the native account, uses the
same account sizing dimensions and deduplicates its input/version. It uses the
existing service token and supplies an opaque subject to the engine. Observe
retains native recomputation when live version readback is unavailable; enforce
requires live readback before dispatch or restoring a cached response. Both PHP
callers send X-Linker-Engine-Version on actual guarded POST work. The private gate
compares it to the loaded snapshot before parsing/work and returns409 if a restart
happened between readback and dispatch. Successful work carries the matching
response header; missing/mismatched200 headers become explicit failures in PHP,
never a successful response stored under a different version's key. Existing
private callers without WordPress's result cache need no new mandatory header.

## Actual work and ordinary reading

Genie holds a second, private actual-work scope inside its synchronous turn
worker, around attachment reading, understanding, model loops and ability calls.
The response iterator only serializes the already completed answer. A PHP timeout
or disconnected socket cannot release a still-running worker. All Genie processes
share `LINKER_GENIE_WORK_PATH` (absolute, persistent, private SQLite path) with
`LINKER_GENIE_WORK_MODE=enforce`. The existing private token authenticates the
request; PHP adds `X-Linker-Resource-Subject`, a server-selected browser/account
HMAC shared across conversations. These slots enforce subject1/site2 independently
of WordPress's lease. No elapsed-time expiry frees live PID work; only actual
finally or dead-worker recovery does. Store failure is503 and capacity refusal429
(`genie_resource_*`), mapped to the existing visible Genie refusal with retained
input/inquiry handoff. The local launcher supplies this configuration; #522 must
publish/read back it on the service host alongside the provider guard. A real
uvicorn fixture disconnects a caller during synthetic sync work, then verifies
same-subject and third-site work remain refused until that work actually ends.


The engine's private POST gate verifies the existing service token, counts the
body before JSON parsing, then acquires a persistent SQLite work slot. Subject1 /
site4 remain occupied until the actual computation returns, including after PHP
stops waiting. Separate processes share the file. A dead PID's slot is reclaimed;
passing time alone does not release live work. A pathological PID reuse can
retain a stale slot conservatively; no timed release creates extra computation.
An inaccessible/corrupt store is an explicit503. The gate mode is
`LINKER_ENGINE_GATE_MODE=enforce`; the local launcher supplies it and the existing
token. #522 must do the same on the service host.

`GET /geo/plz/{plz}` reads the bundled, cached postcode table (`geo.py`) and has no
external geocoding request. It stays free and does not consume a recomputation or
model turn. `GET /health` exposes only readiness, no private quota counters.

## Customer recovery and privacy

The first-party verification client loads with the tool's existing site surface;
the third-party widget/script is interaction-only. Managed proof is carried in a
header, separate from semantic payload/operation UUID. Retry after an ambiguous
lost response retains the UUID, including an empty/HTML gateway502 or503 after
a potentially saved business write. A native `linker_admission_quota` pre-dispatch
refusal can become a fresh explicit attempt. Only a pure calculation with the
native `X-Linker-Resource-Outcome: failed` completed-failure marker (or a Genie
model-only quota refusal) may otherwise renew its operation UUID; business writes
never treat a generic5xx as proof that nothing happened. No request body is copied to localStorage. Genie's existing
failure record retains text/files in tab session state. A resource refusal restores
the input and attachment chips, keeps thread/draft data, and presents the native
inquiry-page link. Only an explicit click carries the unsent text through tab sessionStorage: destination path checked, 300-second maximum, delete-on-read, pure text `.value`, and no overwrite after a customer edit. No URL, attachment, log or server trust is involved. A 660-byte first-party entry restores it without eagerly loading the Genie app. Direct inquiries have their own business policy and remain
available after model quota exhaustion.

Contact, inquiry and conversation mail use #520's
`linker_commerce_public_business_limits` and `_carry` filters exactly once. They
have no private duplicate counters here. The old three-second/IP guard is skipped
only within the successfully dispatched trusted enforce callback. Ownership,
nonce/CSRF, business validation, email confirmation and the native mail/Outbox
boundary remain. Receipt target caps and safe mail templates belong to #520. Before an unverified guest confirmation creates any secret or pending metadata, Tools calls the trusted four-argument `linker_commerce_receipt_budget_reason` filter with the admitted logical UUID and `conversation_confirmation`. Missing guard or nonempty refusal returns unavailable; it never claims confirmation mail was sent. Verified exports retain their existing authorized route.

An empty private native receipt is allocated only after admission and before work; completion updates that same ID. Privacy erasure during work cannot recreate a deleted response. Completed responses are stored as private, non-public native `linker_tool_reply`
posts for24hours; the admission receipt stores only that native ID. Binary PDFs
are base64 in that private response JSON. Raw submitted requests, proof strings
and service tokens are not stored. Reply lookup rechecks subject binding. Native
verified-email export/erasure handles linked receipts by recipient HMAC OR the
account whose native email was verified, so account A's reply remains discoverable
when the submitted response address was B; native user deletion removes
account-owned records; hourly bounded cleanup removes expired guest records. The
pull anonymizer drops these posts and their association metadata. Erasure never
refunds dispatched quota, and deleting a reply cannot manufacture another permit.

## Framework alternatives and presentation boundary

WooCommerce owns native inquiry, account and saved-solution records, but has no
cross-provider transport dispatch counter or anonymous engineering-job allowance.
LiveCanvas owns page composition, and WindPress owns presentation; neither is a
resource transaction journal. WordPress REST's post-permission dispatch hook,
private native posts, privacy callbacks and cron are therefore used for the narrow
missing behavior. No customer plugin CSS, new customer page layout, PHP layout
template or Code Snippet is introduced. Existing EN/DE translation catalogs carry
customer error/status/action copy and are generated with native make-json.

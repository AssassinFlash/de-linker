# Turn-local ability permission

This delta addresses repeated full Woo authority reads inside one Genie turn.
It changes neither the model channels nor timeout, retry or tool budgets. The
PHP ability gates, final service validation and proxy/receipt gates remain in
place. No WordPress instance or provider was used for these tests.

## Cause and evidence

The existing snapshot-backed local turn log, row 1, recorded the question
`Can I buy EcoFlow PowerOcean?`. Understanding took 13.004 seconds, including
9.518 seconds for vocabulary and 2.744 seconds for Jev. The model phase took
56.055 seconds. Its four search calls accumulated 67.581 seconds under one timing
key; that is cumulative concurrent work, not 67.581 seconds of sequential wall
time. Understanding and model alone totalled 69.059 seconds. The row had no
`first_event` or `total`, so a computed grounded answer did not establish browser
delivery inside the proxy budget.

Before this change, four AbilityClient calls produced four GET manifest requests,
four ability requests and four POST validation requests. Each PHP search already
reads its own authority before and after computing all candidates. Validation
also reassembles the current authority, including current PDF bytes. The Python
per-tool pair therefore duplicated expensive reads around an already protected
PHP operation.

## Narrow interface

`AbilityClient.for_turn(S0)` returns a new immutable facade. Only its HTTP client
is shared; it never stores a turn snapshot on the singleton or changes that
client's publication reader. S0 is the service's freshly captured original input
set, supplied by server composition. There is no browser parameter, TTL or
cross-request permission cache.

The same facade is explicitly passed through understanding, commerce lookup and
the model tool factory. Every protected product tool checks its complete input
product IDs/document URLs and every returned product, candidate, pairing and PDF
URL against S0. Only the duplicate remote snapshot/validation pair is omitted.
The existing protected-tool set is unchanged; historical saved-solution reading
and customer identity rules retain their existing contracts.

The service still freshly validates original S0 before release, including the
original document revisions and product associations. A fresh output URL alone
cannot authorize old page references after same-URL replacement. A product newly
published after S0 cannot be mixed into this turn. PHP still performs its own
before/after current reads on every tool. Authority failure still fails closed.

Standalone `run` and `record` retain their per-call current snapshot and final
validation. Their existing shared fact collection/logging is also used by the
facade, so the facts recorded are the actual response of each tool.

## Verification

The first new counter regression failed on the absent factory, then passed after
the facade implementation. Its public HTTP boundary shows one initial manifest,
four tool requests and one final validation. A separate standalone regression
retains four manifest, four tool and four validation requests.

The complete ASGI turn fixture uses real AbilityClient/PublicationClient and
mock HTTP transports, with injected understanding/model responses and a private
temporary turn log. It proves all three stages receive the same facade, four
searches and a commerce get-product add no per-tool authority reads, and the
unchanged service boundaries still make two manifest and three validation
requests. Final draft/replaced-document permission returns 409 with no answer
blocks; authority outage returns 503. Parallel scopes also preserve independent
membership and customer headers. New/unpublished input IDs, later returned
candidates/pairings and unauthorized URLs are refused, while a current locale ID
and bound document alias remain usable.

Validation: the new focused scope suite has 15 passing cases; the whole Genie
suite passed 2,185 tests, with one skipped, six expected failures and 195 existing
duplicate campaign cases deselected. Full strict mypy passed all 195 source
files, and Ruff lint/format passed all 200 Python files. Existing direct private
answer tests were given their explicit unused tool dependency; their routes and
assertions were not weakened.

The existing integration virtualenv was reused with this worktree's `src` on
PYTHONPATH. No dependency install, WordPress instance, provider key, timeout or
model setting was changed. Source-level request counts do not establish a
production latency improvement. Root owns the actual HTTP EN/DE generic-family
and exact-model readback after integration; vocabulary and its separate authority
reads were deliberately not optimized here.

## Input encoding boundary review

Independent Spec/Standards review found that the ID collector recognized only
integer/list values, while the HTTP encoder accepted strings and tuples. For
example, S0 containing only product 1 did not reject `product_ids=(1, 2)` or
`inverter_id="1", battery_id="2"`. PHP accepts those query values through native
integer conversion, and a compatibility response may contain only a verdict,
with no returned product ID for the later check. Publication of product 2 after
S0 does not revoke product 1's original dependency, so final validation alone
cannot repair that input mismatch.

The client now strictly checks and copies its flat arguments before any authority
or ability request. Product ID scalars must be positive native integers; product
ID arrays must be native lists of those integers. Booleans, floats, strings,
tuples, nested/null ID values and PHP-ambiguous field names are rejected. Other
native scalar fields and simple non-ID arrays retain their existing forms. The
exact checked argument copy is both inspected against S0 and encoded on the
wire, with no PHP-equivalent key normalization left implicit.

Seventeen verdict-only negative examples first failed with actual mock HTTP
requests; after the fix all are rejected before HTTP. Two positive examples
preserve integer pair/list forms and a published locale ID. These join the
original scope/standalone/ASGI regressions; no product ID in the tool's response
is needed to establish the input rejection. The focused ability suites passed
45 cases. The complete Genie suite on this branch passed 2,204 tests, one skipped,
six expected failures and 195 existing duplicate campaign cases deselected.
Full strict mypy passed all 195 source files, and Ruff lint/format passed all
200 Python files. This follow-on changes only the ability input boundary, its
regression tests and this evidence; it does not change model, timeout, budget,
PHP, publication clients or the final permission gates.

## One final release validation

Root's subsequent native run computed a service turn in 49.008 seconds while the
WordPress/browser request still failed after approximately 65 seconds. The
initial snapshot was outside the service's clock, and the compute tail made
three additional complete Woo reads before returning to the outer release gate.
This was not accepted as a completed browser turn.

The compute tail now checks all shipped IDs and URLs against original S0 and
annotates documents with S0's original document identity/revision. It performs
no authority RPC. The existing outer handler remains the only final release
authorization: it freshly validates original S0 after the computed answer is
logged and before returning any SSE. PHP tool before/after checks and the
WordPress proxy/receipt checks remain unchanged. No fresh manifest can replace
the evidence behind an already computed answer.

The normal complete-turn HTTP regression first failed on the previous two
manifest reads. It now proves exactly one initial manifest and one final
validation, with final validation as the last Woo request. It also checks the
logged and delivered citation identities remain S0's. Same-URL byte replacement
and product withdrawal refuse release with 409; authority outage returns 503.
Additional derived new-member/new-URL cases are refused against S0 even though
the fake current source contains them. No partial answer blocks are released.
The combined scope/publication suite passed 104 cases. The normal worker and
actual browser timing readback remain root's integration acceptance, not a
latency claim derived from these local HTTP-contract tests.

Final validation on this branch: 2,206 passed, one skipped, six expected failures
and 195 existing duplicate cases deselected; full strict mypy passed 195 source
files, and full Ruff lint/format passed 200 files. The final-read delta changes
only app composition, these regressions and this evidence.

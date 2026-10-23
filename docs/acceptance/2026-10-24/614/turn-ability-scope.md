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

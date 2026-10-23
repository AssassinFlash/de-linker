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

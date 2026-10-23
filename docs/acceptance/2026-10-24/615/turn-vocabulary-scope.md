# Native vocabulary reads within a turn

The native browser request on the preceding integrated version still exceeded
the WordPress request budget. Its service trace spent 8.012 seconds in vocabulary
loading. The Store API cache fetched current Woo permission in `get()`, then
fetched it again in `_load()` on a cold cache. Warm calls still fetched permission
even though the outer turn had already captured S0.

The regression command was:

```sh
cd services/genie
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_turn_vocabulary.py -q
```

Before the fix, all ten cases failed. The standalone cold-call counter observed
two manifest reads where one was required. A source change between those reads
also reproduced a correctness error: vocabulary content used the second permit
while the cache was labelled with the first revision.

`StoreVocabulary.get()` now accepts an optional trusted, already captured
`Snapshot`. Without one, a configured standalone caller reads current Woo
permission exactly once per get, including warm gets. With one, cold loads,
warm gets and TTL reloads make no additional permission read. The native Store
API listings, EN/DE product filtering and existing TTL remain in use. `_load()`
receives exactly the permit used to choose the cache revision; content and
revision are committed together under the existing lock after loading succeeds.
A failed reload raises rather than returning another revision's cache.

The app retains one native Store API cache handle. Each real turn passes a
local vocabulary getter closure bound to its captured S0 into `prepare()`.
`Understander` uses that override only for the current call; its original
constructor getter and standalone API remain available. No request permission
is stored on either singleton. Old/new revision calls serialize cache reloads
and retain separate vocabulary objects. A later call always checks its own
source revision before reusing the cache.

The new tests cover native cold/warm counters, TTL expiry, source changes during
load, newly published and withdrawn products, failed source reloads, standalone
authority outage, old/new concurrent calls in both arrival orders, the original
understander getter after an override, and actual cold/warm HTTP turns through
the real understander/factory. Both HTTP endpoints retain one outer manifest
and one final validation; the final validation remains the last authority call.

The outer fresh validation of original S0, PHP before/after checks, receipts,
model channels, provider budgets and timeouts are unchanged. Permission reuse
does not claim a measured browser latency improvement: normal runtime and CUA
timing readback remain the integration acceptance boundary. No WordPress data,
original documents, live index or provider endpoint was touched for these tests.

Validation on this branch: the new tests plus vocabulary/understanding/turn tests
passed 447 cases. The final focused vocabulary/turn/publication suite passed 114
cases. The full Genie suite passed 2,228 cases, with one skipped, six expected
failures and 195 duplicate campaign cases deselected. Full strict `mypy .` passed
196 files; Ruff lint and format passed all 201 Python files. Full and final
focused test fixtures used bounded temporary directories removed on completion.

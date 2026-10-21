# #521 local acceptance

This branch implements public resource admission and private provider attempt
budgets. It is stacked on #519. It has not been merged or deployed and does not
claim production protection. The real #511 inquiry-assessment outlet and #520
business/receipt policy are connected and jointly accepted in #522 before the
whole group is enabled.

## Real local environment and fixture boundaries

`g521` was created with `just up g521`, then loaded with
`just pull load g521 latest` (snapshot 20261022-0018, actual theme/uploads,
212 products and 2756 attachments, snapshot check passed) and
`just serve g521`. Its WordPress/engine/Genie ports are 9285/9286/9287.
Only this child task's new background tab was used. Viewport overrides were
390×844 and 1440×1000, reset afterwards. User/parent tabs were untouched.

The official always-pass dummy Turnstile widget loaded from the official origin.
There was no first-party replacement widget. The local isolation CSP originally
blocked it; the narrowly scoped official-origin CSP correction owned by #520 was
copied into this instance's MU isolation file. Official api.js and challenge iframe
200 responses were observed, followed by native prepare → verify → turn.
Canonical Siteverify success was an explicitly local HTTP fixture. The real dummy
provider response has a non-production hostname/action and is not evidence for
production verification. Genie answers/provider429 and private-engine429 were
explicit synthetic HTTP responses; no paid provider was called and no real mail
was sent.

`ui-http-fixture.php` records the exact narrow HTTP fixture. It requires a local
WordPress, this instance's canonical URL, and the exact official dummy secret.
It only intercepts canonical Siteverify and loopback service routes. Mode comes
from `/tmp/de-linker-521-network-mode.txt`: `valid`, `quota`, `outage`, or
`engine_quota`. The private local-only wp-config supplied dummy keys and
`enforce`. Before installation its exact bytes were saved with mode0600. After
acceptance the config was restored byte-for-byte, our MU fixture was removed,
and the temporary PVGIS cache fixture was removed. No production key is in any
fixture or repository file.

An initial real-engine request for 80331 failed because the external yield service
was unavailable. The existing committed PVGIS test profile for Munich was then
copied only into g521's local cache for 80538 (35°, south). Actual engine sizing,
product/feed selection, service-token gate and PDF generation ran normally.
This local cache use is evidence for the guarded calculation path, not external
PVGIS availability. The original failure also exposed whole-day caching of a
failed pure calculation; this was repaired and covered by native database and
browser recovery fixtures in this branch.

## Visible states checked

| State | EN evidence | DE evidence |
| --- | --- | --- |
| Model429 preserves unsent question and native inquiry link | `en-390-quota.png`, `en-1440-quota.png` | `de-390-quota.png`, `de-1440-quota.png` |
| Siteverify503 preserves question, failure explanation and inquiry path | `en-390-verification-outage.png`, `en-1440-verification-outage.png` | `de-390-verification-outage.png`, `de-1440-verification-outage.png` |
| Latest failed question enters editable native inquiry field | `en-1440-inquiry-preserved.png` | `de-390-inquiry-preserved.png` |
| Engine429 retains inputs and explicit retry control | `en-390-configurator-limited.png`, `en-1440-configurator-limited.png` | `de-390-configurator-limited.png`, `de-1440-configurator-limited.png` |
| Actual engineering result; DE same-input refusal→recovery | `en-390-configurator-result.png`, `en-1440-configurator-result.png` | `de-390-configurator-recovered.png`, `de-1440-configurator-recovered.png` |

`en-390-initial.png`, `en-390-checking.png`, `en-390-success.png` also record the
initial/question/checking/answered path. The DE reload retained the unsent question
(`de-390-reload-preserved.png`); existing failure recovery presents a retry on
reload. The native inquiry fields were not submitted during this UI run.
The initial fallback exposed the previous completed question being prefilled;
the explicit single-use300-second tab handoff now carries the latest unsent text,
without files or URL parameters, and never overwrites a customer's field edit.

The actual PDF request returned200 (`network-paths.json`), with the existing
report preserved (`en-1440-report-export.png`). The network capture contains
only origin/path/status/type, no headers, body, proof or credential. The browser
ring buffer is marked truncated: the saved tail is not a complete chronological
trace. Earlier widget success and synthetic turn200 were observed during the run
and are represented by the success screenshot.

The new status/CTA placements were visually inspected at both widths. Existing
LiveCanvas/WindPress page composition and plugin CSS are unchanged. There is no
new public page or layout. This is tool-state acceptance, not a claim of a fresh
all-site live/local pixel-zero comparison.

## Relevant checks

- Genie full suite: 1940 passed, 1 skipped, 195 deselected, 6 existing xfails;
  mypy180 project files and ruff passed. Eight new provider fixtures cover real
  SQLite workers/restart/crash, midnight/replay, damage/missing config, actual
  installed OpenAI HTTPX2 transport, each-loop HTTPX transport, timeouts without
  refunds, private authentication and absolute-deadline cancellation under a
  real SQLite write lock. No late upstream request is sent after cancellation. Three additional actual-work
  fixtures cover private Genie slot configuration/damage, real process crash
  recovery and real uvicorn HTTP disconnect while synchronous work is blocked:
  same subject and third site request stay429 until the actual work finishes.
  PHP adds the trusted stable subject to real private turn HTTP requests, and
  changing conversations preserves it.
- Engine full suite:153 passed; mypy50 project files, ruff and new-file format
  checks passed. Private actual-work slots are shared between processes,
  retain live work through caller disconnect, recover dead worker PIDs and
  reject unauthenticated/oversize input before parsing/work.
- Tools JS:407 passed in50 files; types, eslint, Prettier and committed build
  check passed. Existing webpack size/runtime recommendations remain warnings.
  Native `just i18n-tools` make-json/msgfmt and `just i18n-coverage` passed.
- Tools PHP unit:286 tests,2341 assertions. Real g521 resource integration:
  21 resource tests. The additional complete Tools real-WP integration run
  finished85 total tests/677 assertions/23 prerequisite skips with no failures.
  CI mu-smoke explicitly runs the resource and shared-owner classes against its
  bare native instance with synthetic live-version/loopback settings and intercepted
  HTTP; no paid API or real mail is used. PHPStan and WPCS passed. The real journal/native
  fixtures cover bad/revoked proof before heavy decode, single dispatch,
  completed replay, crash ambiguity, trusted-context cleanup, free reads,
  no model cost for storage writes, same-input design success deduplication,
  definite failure recovery, shared business seam, no confirmation secret/mail
  after recipient refusal, privacy erasure without late resurrection, PHP
  provider refusal and account-owned recomputation/service-token propagation.
  Review regressions additionally cover mixed-case native REST routes, observe
  CF/hash/cookie/body/file/storage failures retaining native validation, absent
  observe live-version readback, account-author OR recipient privacy and
  late completion after erasure, unknown business502/503 retaining one UUID,
  real native engine query deduplication and rejected body/query path overrides.
- Shared Commerce additions: real WP3 tests/24 assertions, enforce/observe
  email-owner export/erasure and native parent revocation; PHPStan/WPCS passed.
  Commerce unit run:1376 total with190 integration skips,6039 assertions,
  no failures. Its ReadSolution change passed WPCS.
- I18n PHP:239 tests/585 assertions, PHPStan/WPCS passed. The new translation
  refusal fixture proves no paid HTTP dispatch and the existing transient failure
  path; existing translation preservation/digest behavior remains authoritative.
- Pull anonymizer:20 passed; private response/PDF and association metadata are
  absent from a real SQL-shaped snapshot fixture. Local launcher:6 service tests
  passed; ruff/mypy passed. No global registry/port-sensitive local stack test was
  run concurrently with the parent's stack.
- `git diff --check` passed; no changed CSS files. No copied legacy identifiers
  or alternate model/provider route were introduced.

## Practical limits and combined acceptance

The hard journal is a call-attempt operating guard, not precise API usage,
tokens or euros. A rare cancellation while SQLite waits may conservatively occupy
one unused unit; it never dispatches later. Already sent requests never refund.
The root accepted this verified conservative boundary to preserve the absolute
10-second assessment deadline.

#522 must connect the real #511 outlet with
`AsyncTransport("jev", existing_transport)`, map BudgetError to undetermined,
run its real absolute-deadline/normal-notification fixtures, load the real #520
business and receipt filters, and publish/read back the same persistent provider
path, mode, existing token and actual private loaded-version readback. It must also set
`LINKER_GENIE_WORK_MODE=enforce` and a shared persistent absolute
`LINKER_GENIE_WORK_PATH` for all Genie workers; the local launcher and its native
environment fixture already supply the per-instance private path. A missing guard
must refuse paid/resource dispatch. Those are the planned joint acceptance steps,
not a claim that this isolated branch already protects production.


## #522 nightly feed integration correction

The existing03:40UTC feed-sync timer can update feed/compatibility and restart the
engine on the same UTC day. A static WP release constant could then restore an
old successful result. The final narrow integration increment uses the private
running-version route and shared EngineVersion reader described in the spec.
A snapshot version is made from the same bytes that construct loaded objects,
with source captured for the process, and the engine verifies/echoes the expected
version on actual work. No new credential or WordPress SSH callback is needed.

Actual Python fixtures cover token/gate refusal, damaged/missing data, source
capture, disk mutation while loaded A remains A, a new app loading B, stale-A409
before JSON parsing and real successful roof work echoing B. Real WP fixtures
cover public/native same-input reuse, same-day rotation creating a fresh result,
unavailable readback refusing even a known cached response, request-scope-only
caching, observe native passthrough, and a mismatched worker200 becoming503 rather
than canonical success. No customer copy, visual layout or model route changed.
The previously frozen dce072d9 CI run39689608503 passed both jobs; this additional
increment is independently committed for the combined #522 review and CI.

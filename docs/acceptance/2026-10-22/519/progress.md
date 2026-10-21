# Shared admission — backend checkpoint, implementation in progress

Issue #519, part of #505. Source base:
`4f722c2636a61861c74e1a39b58350c0c218af3d`.

The new private configuration, canonical Siteverify transport, pseudonymous
browser/account identity, scoped signed prepare/verified proof, and atomic
multi-dimensional ledger are implemented. The ledger uses one non-autoloaded
native option and a connection-owned mutex; one atomic write commits every
reservation dimension and its retry receipt. No SQL transaction commits unrelated
Woo work. It preserves pre-dispatch cancellation, post-dispatch spending,
expired in-flight recovery, stable UUID replays, native outcomes, and import of
actual anonymous spending without importing unused holds. Imported receipt
ownership survives expiry of its shorter counter window.

Native WordPress privacy callbacks export/remove only verified account/recipient
links, preserve other subjects and aggregated dispatched spending, and explicitly
report temporary minimal replay-marker retention. Late completion cannot restore
an erased payload. The live-pull anonymizer drops the complete private journal.
No customer text, password, raw IP, raw challenge token or service credential is
stored in this journal. Policy primitives use private HMAC owner/bucket keys.

## Verification at this checkpoint

- Real WordPress fixture: 27 tests / 133 assertions passed on the loaded `g519`
  snapshot instance. Includes strict Boolean/hostname/action/provider failures,
  safe diagnostics, no upstream I/O for malformed input, proof scope/kind/expiry,
  native login binding, atomic quota denial, dispatch/cancel/replay, crash leases,
  a second real database connection, privacy scope/late completion, and the native
  privacy-registration path.
- PHPStan (full Commerce and latest changed-file scope): no errors. PHPCS on all
  new protection classes and their integration tests: clean.
- Live-pull anonymizer: 19 tests passed on this branch's base. Its count differs
  from the separate stacked customer-evidence branch; both changes need combined
  validation when integrated.
- Provider responses in these fixtures use the real WordPress HTTP interception
  boundary. They are not evidence of live Cloudflare or regional availability.
  The production key file was not used by the fixtures.

## Work still required before #519 is ready

Connect the application module, same-origin prepare/verify routes, positive
verification retry receipts, single-use business-proof consumption, resource
proof checking, scheduled cleanup, shared client, staff health/mode/coverage and
native privacy registration. Finalize the configuration/policy interfaces for
#520 and #521; complete EN/DE copy, rendered 390/1440 states, full checks,
independent Spec/Standards reviews and PR/CI.

The helper classes are not yet wired into public handlers. No business/resource
door is claimed as protected by this checkpoint. No production change, model
request or external mail was performed. #520/#521 own actual door integration,
and #522 owns joint acceptance and controlled activation.


Final implementation, repairs and real-browser evidence supersede this early checkpoint; see checks.md and review.md. PR #523 remains separate from production rollout.

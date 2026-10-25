# 询盘初判的独立后台派发

Part of #533; implementation #543. The owner confirmed that customer submission must not wait for Jev, the initial classification has an absolute ten-second acceptance window including queue delay, and an unavailable assessment still produces the normal internal notification. Content labels do not reject inquiries.

## Observed mechanism and choice

The installed WooCommerce 11.2.0 includes `WP_Async_Request`; Action Scheduler uses it for its general queue runner. That general runner has a sixty-second async dispatch lock. The incident's successful inference times were short, but many assessments first started after their acceptance deadline. Changing the global lock or global batch concurrency would affect unrelated work.

Use Woo's existing `WP_Async_Request` transport for one specific inquiry. `Queue::defer()` first retains the existing PROCESS and EXPIRE Action Scheduler tasks, then attempts this independent wake-up. `Queue::process()` remains the only classifier consumer. The original connection locks, notification holds, provider-budget request, model/prompt, ten-second absolute deadline, notification recipients and minute recovery remain authoritative.

```text
customer submission
  native inquiry + immutable snapshot/deadline saved
  durable PROCESS + EXPIRE saved
  persist one record capability hash
  native nonblocking loopback
  customer response

private loopback
  validate + consume one-use record capability under DB mutex
  empty 202 acknowledgment
  try dedicated worker mutex without waiting
    original Queue::process(inquiry)
      original hold/process/release locks
      original provider budget + remaining absolute deadline
      original typed result + Outbox handoff

loopback fails / worker busy / worker dies
  original AS tasks and independent minute recovery
  deadline => Unable to assess + ordinary team notification
```

## Capability and work bounds

- The fixed AJAX action receives only inquiry ID and a 256-bit random one-use token. It accepts neither content nor model/destination/budget parameters. The token is sent in the POST body, never in a URL or customer response. The database stores only its SHA-256 hash.
- The hash lives in a purpose-specific private order meta record alongside the original deadline. A nonwaiting connection-owned mutex atomically consumes it before model work; the hash is removed on claim. Missing, malformed, forged, unknown-ID, cross-record, expired, replayed and held callbacks produce no model or notification side effects.
- The expiry must equal the inquiry's original stored deadline. No callback or failed dispatch renews it. The actual consumer rechecks deadline and hold after the claim.
- There is at most one additional independent assessment worker for this database/site, with no waiting queue or recursive dispatch. Busy work retains its original durable recovery. AS global concurrency and dispatch settings are unchanged.
- No logged-in cookies, WordPress shared guest nonce, provider credentials or customer content travel in the wake-up. TLS verification is enabled and redirects are disabled. Native transport body/response are bounded; its acknowledgment is empty.
- Native `WP_Async_Request` requests `timeout=0.01`, `blocking=false`. Installed WordPress Requests' cURL transport rounds timeout up to at least one second. An authenticated callback therefore acknowledges immediately after consumption, before classification. It uses FPM/LiteSpeed finish-request functions when available, and an empty Content-Length response on local PHP. This is not a claim of a ten-millisecond network ceiling.
- `submitted` describes a local dispatch attempt, not completed classification. Private wake metadata records issue, dispatch, claim and finish timestamps and explicit failed/busy states without storing original content. Assessment data retains accepted/deadline, started/queue/model seconds and the first notification result.

## Failure and rollback

A failed optional wake-up never runs classification synchronously, creates a second notification implementation, removes the durable tasks, or changes public submission results. A crash after consuming the capability leaves original recovery intact. Holds remain authoritative in the original consumer; a model label alone never creates a hold.

Rollback is the previous code release. No schema migration or destructive data rewrite is required. Wake metadata expires with the original deadline; older code ignores it and still consumes the durable AS tasks. Preserve all inquiries and mail jobs when rolling back.

## Acceptance

Real local WordPress/Woo + isolated mail/HTTP, using the production snapshot, tests the native HTTP dispatcher and independent PHP/database connections. Inference is a local simulated service boundary with actual two/eight-second wall-clock delays. No paid model or real mail is used. Tests cover token scope and replay, actual HTTP rejection and empty acknowledgment, two-connection race, bounded worker contention, loopback failure, notification hold, budget refusal, explicit unknown recovery, and disconnected customer HTTP after durable acceptance. Native CI runs this class beside the existing assessment/review/hold suites.

No customer-visible layout or copy is changed. Fresh EN/DE customer-path and production callback/readback remain release acceptance responsibilities after composition with the intake-protection work; local/CI proof alone does not establish managed-host loopback or inbox delivery.

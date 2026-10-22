# Pre-send content verdict contract

Owner policy, 2026-10-23; source base `97ef132f176066c25812c8093a1b5106c443b3fc`. Supersedes observation-only inquiry notification decisions. Persist complete customer input first without waiting for a model. Model results are evidence for a native sending permit, never an authorization supplied by the customer. Unknown, expired, provider/budget failure and malformed response are not normal. Keep records and use bounded native recovery; no substitute review-reminder mail.

## Authenticated existing service wire

`POST /inquiries/assess`, unchanged private shell authentication. Request:

```json
{"state":{},"binding":{"protocol":"inquiry-mail-v1","policy":"inquiry-mail-v1","record_id":123,"snapshot_sha256":"<64 lowercase hex>","purpose":"inquiry_mail"},"remaining_seconds":10}
```

Binding is required, extra keys forbidden, record_id is a positive native integer (not bool/string). Purpose is exactly `inquiry_mail` (Woo inquiry ID) or `conversation_mail` (private mail-job ID); neither can authorize the other. The PHP producer hashes its frozen complete source JSON and retains its exact bytes; the service treats that hash as opaque and echoes every binding value unchanged. Do not try to reproduce PHP JSON serialization in Python. PHP compares the complete field set and each value, without depending on object-key ordering. The service is not an unauthenticated public classifier. Passwords, keys and credentials never belong in state.

Response always includes binding, decision=`normal|malicious|unknown`, one basis, fixed reason, model=`typesafe/jev-1.13`, rubric=`inquiry-mail-v1`, seconds and raw evidence. Bases: business_request, service_or_complaint, reporting_abuse, fraud_or_phishing, unsolicited_bulk_promotion, meaningless_abuse, insufficient_context. Normal pairs only with the first three; malicious only with the next three. Unknown grants no sending permission.

`raw={primary: reading|null, escalation: reading|null}`. Each reading is `{model:string,answers:{classification:answer,basis:answer}}`; each answer is `{type:"choice",choice:string,confidence:number|null,probabilities:object}`. Classification choices are normal/malicious/unknown; basis choices are the seven above. Numeric evidence must be finite and in[0,1]; provided probability distributions must contain exactly the allowed choices and sum to1 within floating-point tolerance. Preserve typed evidence, never generated instructions or arbitrary provider text. `usage` is bounded per-provider attempt telemetry, not authorization; reported fees may be unavailable.

Only reasons `classified` (direct primary) and `escalated` (successful approved escalation), together with consistent typed evidence, can produce normal/malicious. Unknown reasons include conflict, insufficient_confidence, insufficient_context, missing_credentials, invalid_model, invalid_response, transport_error, deadline, provider_http_NNN, provider_budget_{quota,unavailable,configuration,permissions,replayed,provider,attempt}; escalation failures use the same fixed code prefixed `escalation_`. No free-form provider response or customer text enters diagnostics.

## Decision and provider discipline

New initial operating threshold:0.90 for both questions, frozen before the evaluation at the coordinator's direction. It is not calibrated on real customers and does not mean90% accuracy. Use declared confidence, capped by the selected-choice probability when supplied; a probability alone may supply confidence. Missing confidence is insufficient. A choice contradicted by its own probability maximum or by the other answer is a conflict. Valid primary unknown/conflict/insufficient-confidence may escalate; invalid model/wire or provider failure must not silently switch providers.

Primary is only `typesafe/jev-1.13` at OpenRouter's native `https://openrouter.ai/api/v1/systemone`; allowed successful reported ID has the existing optional eight-digit date suffix. Escalation is only exact reported ID `deepseek-flash` at the official `https://api.deepseek.com/chat/completions`, using the existing approved judge role and JSON answer schema. No dated DeepSeek alias is established by the existing official response evidence. No chat Jev router, OpenRouter DeepSeek or alternative model. Same finite/confidence/consistency checks apply to escalation; an unresolved result remains unknown.

Every provider attempt uses the existing shared persistent provider ledger. At most one retry per stage follows the existing inquiry client discipline; all attempts and both stages share one absolute remaining window of at most10seconds, never renewed on retry. Timeout is unknown, not send permission. Background recovery owns a new bounded attempt; it does not reinterpret an expired observation-v1 response or erase/debit-refund history.

## Native sending permit

One frozen source verdict may serve both team and customer-receipt purposes without duplicate classification. After a validated normal source verdict, trusted PHP renders each immutable actual Message and atomically stores a separate local permit bound to source fingerprint, native record/staff/erasure version, policy, exact mail purpose, real recipient route and complete Message/attachment-content digests. Conversation mail never borrows inquiry authorization. The classifier has not scanned the final templated HTML; this is deliberately a source verdict plus server-derived message permit, not a claim that a model inspected that HTML. A changed source, purpose, route, Message, attachment, staff decision or erasure invalidates the permit. Existing Outbox must recheck before any SMTP/PHP budget or transport. Existing incident holds and non-content security transactions retain their own protections.

## Evidence boundary

Rollout must install and verify the fail-closed native PHP gate together with this wire. Publishing a classifier alone cannot stop an older observation-only consumer that still notifies on unknown. Backend, native consumer, and production readback are separate acceptance gates.

Freeze adversarial and realistic positive controls before live evaluation; at most16 additional primary dispatches plus necessary approved escalation. At least half are normal hard cases. Report normal-to-hold, malicious-to-normal, unknown/deadline and latency/fees separately; no small-corpus accuracy guarantee. Raw incident fields, keys, request bodies and provider captures remain private. Local mock protocol, actual provider, native mail-consumer and live deployment/readback are separate evidence layers.

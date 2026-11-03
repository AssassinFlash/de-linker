# Sending permission after automated abuse assessment

Status: owner requirement fixed on 2026-10-23; solution research and validation in progress. This document does not assert deployment.

## Owner decision

The owner rejected the default workflow of saving suspicious inquiries and repeatedly emailing a link for manual review. The system must identify malicious submissions before any content-triggered mail is sent, automatically withhold malicious mail, and protect the limited sending allowance. Jev and the existing large-model channel may perform that assessment. Normal customers must retain access and a prompt submission response.

This supersedes the earlier observation-only notification contract for inquiry abuse: a spam label must not be informational decoration on an otherwise unconditional email, and a ten-second timeout must not itself grant permission to send. It does not authorize deleting customer records, weakening authentication, replacing approved model routes, or pretending that AI has zero errors.

The owner also requires research against mature, commercially usable free solutions before the broader design is selected. New free components are authorized where evidence establishes their suitability. Existing metered model calls are not described as free services.

## Directly observed defects

At 18:28 UTC on 2026-10-22 the real internal mailbox contained four review reminder emails sent at 15:24, 16:24, 17:24 and 18:25 UTC. The last three reported the same 77 records. Their bodies contained only count, age, timestamp and an administration link. Private message evidence is retained outside the repository.

At 18:30:23 UTC a read-only production check found 78 verification-lane records, three campaign samples and the original 38 held standard mail jobs. Seventy-seven of the 78 verification records matched the current narrowly confirmed campaign predicate; the remaining record had no automated classification and must not be asserted malicious from this count alone. No queued review-reminder job remained at that observation.

Current source has three distinct gaps:

1. `ReviewReminder::tick()` produces a new aggregate email each hour even when the pending set is unchanged.
2. `Queue::process()` skips held inquiries, so the verification lane does not actually receive the promised automated content judgment.
3. The current inquiry rubric explicitly says observation-only, and `Queue::finish()` can produce a notice for every label or an expired deadline. The customer receipt is a separate status listener and can precede team classification on the verified path.

These are separate from the existing confirmed-campaign rule, which already prevents new matching records from creating individual jobs. A successful CAPTCHA is not a content judgment.

## Immediate containment

Stop the review-reminder producer and prohibit its exact trusted message category at the transport boundary, before either sending allowance is debited. Preserve existing jobs, message bytes, attempts, historical sending entries and audit evidence. This change must not disable recovery for inquiry processing, password resets, registrations or Proforma notices.

This narrow correction is an emergency containment change, not completion of the automated assessment system.

## Broader design requirements

- Save the complete native inquiry and return the submission result without waiting for an external model.
- Establish durable, server-owned sending permission after assessment, bound to the exact native source and assessed content. Public request fields, a proof of human interaction, a model-looking string or a stale result cannot grant it.
- Apply the decision to all mail caused by that public submission, including internal notification and automated customer receipt. Keep security transaction messages in their appropriate separate policy.
- Automatically quarantine confirmed malicious submissions and suppress their per-record mail and replacement review reminders. Retain evidence and a reversible audit trail.
- Deliver normal inquiries with their actual contents. Do not replace useful information with a count and a link.
- Treat unresolved classification, invalid response, exhausted provider budget, timeout and recovery failure as explicit states with bounded automatic recovery; none is implicitly an allow verdict. Avoid indefinite invisible stranding of a genuine customer.
- Keep the approved Jev native endpoint and official deepseek-flash escalation route. An OpenRouter outage is reported and retried under its policy; it must not silently replace Jev with another model.
- Protect the model and database as well as email: early deterministic campaign handling, duplicate control, admission budgets and bounded recovery must prevent an attacker from turning spam detection into unlimited paid model calls or unlimited storage.
- Do not use a sender's language, country, optional missing details, an external URL, a short request, a complaint or quoted scam text as sufficient evidence of abuse.

No confidence threshold, escalation cutoff, retry count, new retention period or new service is selected merely by writing this document. Each selection needs source evidence, measured site-specific results and an explicit implementation contract.

## Required evidence before acceptance

The research must distinguish free commercial use from personal-only offers, explain what each proposed component actually inspects, and identify which live endpoint or host can use it. WordPress plugin installation alone does not prove coverage of custom admin-post, REST, Genie or the VPS.

Freeze real malicious examples and independent normal controls before tuning. Include multilingual technical requests, short callbacks, complaints, legitimate links, a report quoting the scam, model instructions embedded in the submission, identity rotation, duplicate content and both inquiry doors. Report false malicious decisions, malicious allows, unresolved cases, latency and per-attempt model usage without claiming a production false-positive rate from a small test set.

Native tests must prove malicious and unresolved decisions produce zero external mail and zero mail-budget debit, all original contents remain available, normal delivery creates only the intended durable jobs, and provider failures cannot fall through an older notification or receipt path. Exercise concurrent workers, edits invalidating a verdict, crash/retry, transaction rollback and action recovery. Preserve existing held jobs and historical budgets.

Independent Spec and Standards review, actual local runtime evidence, exact release CI, production backup, installed-source and consumer readback remain necessary. Queue inspection is not inbox delivery. No new real production test email is implicitly authorized by this document.

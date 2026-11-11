# Natural inquiry end-to-end readback (#533 gate)

Read-only. Nothing was written to production, no mail was sent, no mailbox was
modified. Personal data is masked; Message-IDs and counts are preserved.

This closes the #533 re-open gate: *first natural inquiry → classification →
notification permission → transport debit/ACK → same Message-ID in the inbox*.
The #542/#543/#545 acceptance inquiries (#8535/#8457) are **not** used as
evidence here, per the 2026-11-04 map instruction.

## Verdict

| Gate step | #8680 | #8685 |
| --- | --- | --- |
| Native inquiry record, `wc-inquiry-received` | pass | pass |
| Classification (`normal` / `business_request`) | pass | pass |
| Durable send permission bound to source hash | pass | pass |
| Team notification job, `delivered_at` + witness | pass | pass |
| Customer receipt job, `delivered_at` + witness | pass | pass |
| Transport ledger debit, matching transport | pass | pass (SMTP → PHP fallback) |
| Same Message-ID observed in inbox | **not verified** | **not verified** |

Chain integrity is proven from the inquiry record through the transport ledger
and the on-box PHPMailer log. The **inbox leg is unverified** — see
"Unverified: inbox leg" for the exact reason. It is not reported as passing.

## Scope and evidence sources

Production MySQL was down for the whole session: `127.0.0.1:3306` answered
connection-refused (probed with `fsockopen` from the host itself), `/tmp/mysql.sock`
existed only as a dangling symlink, `wp` CLI returned `Error establishing a
database connection`, and the site answered 000 both from outside and from the
host. Live SELECTs were therefore impossible. Three independent sources were
used instead:

1. **Imported production snapshot** `db-20261110T233636Z.sql.gz`, taken
   2026-11-10 23:36:36 UTC — after both inquiries, and after every job in this
   report was delivered. Imported into a throwaway local schema for SELECTs
   only. Every database figure below is labelled as *snapshot-time*.
2. **On-box `~/.logs/mail.log`** — PHPMailer's own log of PHP `mail()`
   transports, including the Message-ID actually written. Read-only.
3. **`wp-content/uploads/wc-logs/linker-mail-*.log`** — the plugin's send log,
   which records the intent (recipients, subject) for both transports.

Snapshot-time evidence is not live evidence. Where a number could have changed
after 2026-11-10 23:36:36 UTC the report says so.

## Chain 1 — #8680

Submitted 2026-11-09 20:22:11 UTC by an external guest (`customer_id=0`), a
German private customer asking for a SAJ BU2-5.0-HV1 module price, battery
grade and whether a private order to Germany is possible.

### Inquiry record

| Field | Value |
| --- | --- |
| Order | 8680, `wc-inquiry-received`, `2026-11-09 20:22:11` GMT |
| Source / topic / locale | `contact` / `offer` / `de_DE_formal` |
| Public request UUID | `03532e33-f26c-43d4-9245-9eab8f85c0db` |
| `_linker_public_input` | `ca00a32d2c6add7b4b692bb07198c32bd150b80caef9dabc5247ca8bcfac522f` |
| Selection | product 6738, "SAJ BU2-5.0-HV1" |
| Review lane | `verification` |

### Classification and timeline

`_linker_inquiry_assessment_pending = complete`; `_linker_inquiry_assessment`
carries `accepted_at 1794255731.844003`, `deadline 1794255741.844003` (a 10.0 s
window), `completed_at 1794255733.431179`, `elapsed 1.587 s`.

Verdict: `decision=normal`, `basis=business_request`, `reason=classified`,
`model=typesafe/jev-1.13`, `rubric=inquiry-mail-v1`, classification confidence
1.0, `escalation: null`, one primary call, HTTP 200, 0.373 s, 1367 in / 133 out
tokens. No escalation call, so no second model was consulted.

Action Scheduler: `linker_inquiry_assessment_process` action 11618 (scheduled
20:22:11, last attempt 20:22:13), `linker_inquiry_assessment_expire` 11619
completed 20:22:25.

### Permission and jobs

`linker_inquiry_send_8680` (`_linker_inquiry_send_policy = inquiry-mail-v1`):

```
status normal, attempts 1
snapshot_sha256 a2734d938e4263e01c55ebcd7df36ab68953d8d14f0dc07a009545dd108cf7dc
source_sha256   74d9e577c756a1ae6e7b30dd95cd81384d65de8fc7fd49c45d9660f574a258ac
jobs.team.id    8681  delivered_at 1794255739 (20:22:19)
jobs.receipt.id 8682  delivered_at 1794255740 (20:22:20)
```

| Purpose | Job | Witness Message-ID |
| --- | --- | --- |
| team | 8681 | `<O88hTjOpaqxwGhEqqm32idtNqbsmvCZj71fLtczGQNg@de-linker.com>` |
| receipt | 8682 | `<zrQbPT4PIKh2tNTKIkPvCFaq0xIy4gTXEKizGUBo2HE@de-linker.com>` |

Both job posts are absent from `wp_posts` in the snapshot, which is the
documented success path, not a gap: `JobStore` states "A message that was sent is
deleted" and `Outbox` deletes the job after a successful transport. The 38
surviving `linker_mail_job` posts are all dated 2026-10-22 with
`_linker_mail_attempts = 0`; each one's `_linker_incident_hold` names incident
`public-inquiry-campaign-20261022` and points at an order that is both disposed
and held — the 38 jobs and the 38 "disposed **and** held" records below are the
same set. That is the frozen historical attack cluster, untouched. Nothing was
inferred from job-post absence alone: the authorization row carries the
delivered timestamps and witnesses independently.

`_linker_receipt_skipped` is empty, i.e. the customer receipt was **not**
suppressed (no `review_hold`, no `daily_cap`).

### Transport debit

`linker_commerce_mail_transport_sends`, `next_id = 68`:

| id | time (UTC) | transport | matches |
| --- | --- | --- | --- |
| 60 | 2026-11-09 20:22:18 | smtp | job 8681 (team), delivered 20:22:19 |
| 61 | 2026-11-09 20:22:19 | php | job 8682 (receipt), delivered 20:22:20 |

Action Scheduler `linker_commerce_mail_attempt` 11620 `[8681]` last attempt
20:22:19, and 11621 `[8682]` last attempt 20:22:20. Both `complete`.

`linker-mail-2026-11-09-*.log`:

```
20:22:19 Email "New inquiry #8680 from Nowack Steven" sent to <team>, bcc <bcc>.
20:22:20 Email "Ihre Anfrage #8680 ist eingegangen" sent to <customer>.
```

**Why only one #8680 Message-ID appears in `mail.log`.** The team copy was
delivered over SMTP, and `~/.logs/mail.log` records PHP `mail()` only — so
`<O88h…>` is legitimately absent there while `<zrQb…>` (PHP) is present. This
reconciles instead of contradicting: the ledger says `smtp` for id 60 and `php`
for id 61, and there is no `Internal SMTP failed` warning for #8680, so the SMTP
attempt succeeded. The independent corroboration for `<O88h…>` is the witness in
the authorization row plus the `linker-mail` intent line; it is not cross-checked
against a PHP log by construction.

## Chain 2 — #8685

Submitted 2026-11-10 12:10:13 UTC by an external guest, a German installer
planning a GoodWe ESA GW8K-ETA-G20 installation.

### Inquiry record

| Field | Value |
| --- | --- |
| Order | 8685, `wc-inquiry-received`, `2026-11-10 12:10:13` GMT |
| Source / topic / locale | `contact` / `product` / `de_DE_formal` |
| Public request UUID | `c49ff3c4-45b5-494a-95d6-3b867a7aa9ea` |
| `_linker_public_input` | `e2c149e56e3a0f221391ffec88b45fdee071ee7cf10e8dee1112960e77f27b64` |
| Selection | product 6666, "GoodWe ESA GW8K-ETA-G20" |
| Review lane | `verification` |

### Classification and timeline

`_linker_inquiry_assessment_pending = complete`; `accepted_at
1794312613.278176`, `deadline 1794312623.278176` (10.0 s), `completed_at
1794312615.343577`, `elapsed 2.065 s`.

Verdict: `decision=normal`, `basis=business_request`, `model=typesafe/jev-1.13`,
classification confidence 0.98, `escalation: null`, one primary call, HTTP 200,
0.477 s, 1455 in / 133 out tokens.

Action Scheduler: 11679 `linker_inquiry_assessment_process` (last attempt
12:10:15), 11680 `linker_inquiry_assessment_expire` (12:10:33).

### Permission and jobs

`linker_inquiry_send_8685`:

```
status normal, attempts 1
snapshot_sha256 b187f1195d8e7aa98d21d2910d48cc10d6aa55d405474351f5d688e8ef1befd4
source_sha256   2aa21831326e51a0a9a5d5d6715a4c51898a04bc113f118e62a364052c550d7e
jobs.team.id    8686  delivered_at 1794312628 (12:10:28)
jobs.receipt.id 8687  delivered_at 1794312633 (12:10:33)
```

| Purpose | Job | Witness Message-ID |
| --- | --- | --- |
| team | 8686 | `<WbE5QVu5g7so205ZPvRy6o08GwkYiH1KFS82LkyTbU@de-linker.com>` |
| receipt | 8687 | `<ysErUqTLKTN9tKSdvM0wdI8LKY3jUqId6bURDPZcmU@de-linker.com>` |

`_linker_receipt_skipped` empty — receipt not suppressed.

### Transport debit and the SMTP fallback

`linker_commerce_mail_transport_sends`:

| id | time (UTC) | transport | matches |
| --- | --- | --- | --- |
| 63 | 2026-11-10 12:10:20 | smtp | team attempt, **failed** |
| 64 | 2026-11-10 12:10:28 | php | job 8686 (team), delivered 12:10:28 |
| 65 | 2026-11-10 12:10:33 | php | job 8687 (receipt), delivered 12:10:33 |

`linker-mail-2026-11-10-*.log`:

```
12:10:28 WARNING Internal SMTP failed; PHP fallback requires its own available
         budget. Reason: smtp_failure.
12:10:28 Email "New inquiry #8685 from Johann-Christian Hanke" sent to <team>, bcc <bcc>.
12:10:33 Email "Ihre Anfrage #8685 ist eingegangen" sent to <customer>.
```

This is the fallback contract working as specified: the SMTP attempt is debited
(63), fails without consuming the customer copy, and the PHP transport is debited
separately (64) before the retry. The 8-second gap between the two debits is the
observed duration of the failed SMTP attempt; `InternalSmtp::configure()` sets no
explicit `Timeout`, so the report does not attribute that duration to a
configured timeout. Both #8685 Message-IDs appear in `mail.log`, consistent with
both copies having gone out over PHP.

## Composition of the `wc-inquiry-received` pool

The 2026-11-10 audit claimed "196 external inquiries from 190 distinct external
mailboxes". Both numbers reproduce exactly, and both are **mislabelled**.

At the audit's own cutoff (2026-11-09 21:22 UTC) the pool held 200 records and
200 − 4 `*.example.test` = **196**; distinct billing mailboxes among them = **190**.
So the arithmetic is right and the denominator is "everything except
`*.example.test`" — which is not the same set as "external real customers".

Classifying the same cutoff by message body gives:

| Class | Records |
| --- | --- |
| `fredmer.buzz` campaign family | 95 |
| `xtimex.buzz` campaign family | 77 |
| Russian-template, other host | 1 |
| Latin gibberish (no sentence punctuation) | 12 |
| **Attack total** | **185** |
| Test / acceptance / internal addresses | 5 |
| **Real external customers** | **6** |

185 + 5 + 6 = 196, which is the audit's figure exactly. Attack bodies are one
template with the host rotated (`Вам перевод … руб. забрать тут <url>`); the
gibberish variant is the same wave with the link moved to the subject line. 182
of the 185 arrived on 2026-10-22, 3 on 2026-10-21.

The current pool (snapshot 2026-11-10 23:36 UTC) is 204 records:

| Class | Records | Notes |
| --- | --- | --- |
| `fredmer.buzz` | 95 | 2026-10-22 |
| `xtimex.buzz` | 77 | 2026-10-21/22 |
| Russian-template, other | 1 | 2026-10-21 |
| Latin gibberish | 12 | 2026-10-21/22 |
| **Attack total** | **185** | |
| Test / acceptance / E2E | 11 | `example.test` ×4, `de-linker.com` ×5, `chesterjohn.dev` ×2 |
| Spam-like probe, `unknown` verdict | 1 | #8683, text wrapping `de-linker.com` and `www.google.com` |
| **Real external customers** | **7** | 5 distinct mailboxes |

The 7 real external records: #7413/#7414/#7415 (`cntepower.com`, three identical
BESS distributor messages sent 01:44:41–01:44:43), #7463 (`googlemail.com`,
German private customer wanting three Power Ocean2 batteries), #7792
(`gmail.com`, Italian customer asking for a single-unit price), #8680, #8685.

### Corrected statement

> The production ledger holds 204 received inquiries (snapshot 2026-11-10
> 23:36 UTC): 185 attack records from one spam wave on 2026-10-21/22, 11 test or
> acceptance records, 1 further link-spam probe the classifier left unresolved
> (#8683), and 7 real external customer inquiries from 5 mailboxes between
> 2026-10-19 and 2026-11-10. The earlier "196 external inquiries" figure counted
> everything except `*.example.test` and therefore included 185 attack records;
> it must not be cited as natural-customer volume.

## Relationship to the #568 quarantine set

The #568 disposition manifest covers 87 records and is a **subset** of the
attack, not its whole extent. Cross-tabulating the 185 attack records against
the two markers:

| | held (`_linker_incident_hold`) | not held | total |
| --- | ---: | ---: | ---: |
| **disposed** (`_linker_business_disposition`) | 38 | 49 | 87 |
| **not disposed** | 90 | 8 | 98 |
| **total** | 128 | 57 | 185 |

- All 87 disposed records are attack records, all dated 2026-10-22.
- Only 38 of the 87 also carry a hold — matching the "original held mail jobs"
  count of 38 in the #568 spec, and the 38 surviving `linker_mail_job` posts.
- 131 records carry `_linker_incident_hold` in total: 128 attack (128 on
  2026-10-22) plus 3 non-attack (#8683 on 2026-11-09, and the two E2E probes on
  2026-11-10).
- 49 records were disposed **without** a hold, and 90 were held **without** ever
  being disposed. 8 attack records carry neither marker.

So "87 quarantined" and "185 attack records" are both true and describe
different things. Any future reuse of the 87-entry manifest must not be read as
covering the wave, and the hold flag is not a reliable proxy for either set.

## Observations that are not chain failures

Recorded, not fixed — repair belongs to a separate ticket.

1. **#8683 (2026-11-09 22:49:23) is still unresolved.** `status=pending`,
   `attempts=7`, `verdict=unknown / insufficient_context`, `label=uncertain`,
   `notification_job=0`. The authorization row's `deadline 1794339074`
   (2026-11-10 19:31:14) shows the **seventh** attempt claimed at 19:31:04 and
   answered in-window at `completed_at 1794339071` (19:31:11). The assessment
   meta's `elapsed 74508 s` is measured from first `accepted_at` to that final
   answer — 20.7 hours of retry history, not one slow call. `next_at 1794425472`
   (2026-11-11 19:31:12) is the 24-hour rung, the last in `Outbox::RETRY_DELAYS`;
   one more failure moves it to `manual` and holds it.

   This is the documented bounded-recovery path, so it is not a silent strand.
   Two things are still worth recording: the body is a link-spam probe
   (text wrapping `de-linker.com` and `www.google.com`) yet the classifier
   returned `unknown` rather than `malicious`, and it consumed 7 model attempts
   over 20.7 hours to reach that answer.
2. **Only 2 of the 7 real external inquiries reached `send_status=normal`.**
   #7413/#7414/#7415, #7463 and #7792 have no `linker_inquiry_send_*` row at
   all, so no assessment or notification was ever attempted for them. #8680 and
   #8685 are the two that ran the full chain. This is consistent with the
   designed "store first, classify later, hold if uncertain" behaviour rather
   than lost mail, but it means the automated path has a very small
   natural-customer sample — two inquiries — and no claim about a production
   false-positive rate can be made from it.
3. **#8683's severity is under-called.** A link-spam probe classified
   `unknown` consumed 7 retries and stayed in the pool; `unknown` is not treated
   as `malicious`, by design. Combined with the cross-tab above — 98
   attack-family records never disposed, 90 of them held — the class of
   "attack-shaped traffic the pipeline does not resolve" is much larger than the
   87-record manifest suggests.

## Unverified: inbox leg

The final gate step — the same Message-ID present in the receiving mailbox — was
**not** verified, and is not reported as passing.

Reason: no IMAP credential exists in any location this agent may read. Checked:
the repository (no IMAP tooling, no credential file; the only `imap.hostinger.com`
mention is prose in `docs/specs/533-security-upgrade.md` recording the #8535
check), local instance env files, `~/.config/terravolt-builder/` on the
workstation (AI/SMTP keys only, no mailbox credential), and the production host
`~/.config/terravolt-builder/` (contains `deepseek.env` and `sunriver-smtp.env` —
an SMTP **sending** credential, which cannot read an inbox — and
`sunriver-smtp.env.save`).

Technical note for whoever repeats this: the earlier #8535 check used
`ssl://imap.hostinger.com:993` with `EXAMINE INBOX` (read-only, no flags or
deletions). The Mailbox name is not recorded in the repository and would have to
come from the owner.

What the mailbox check would add, and what is already established: the
authorization row records a `delivered_at` and a witness Message-ID captured
from `PHPMailer::getLastMessageID()` after a successful send, the transport
ledger debits that attempt, and the on-box logs name the recipient and subject.
That is end-to-end delivery from the site's side. It does not prove the far end
accepted the mail — only that the local MTA handed it off. Queue inspection is
not inbox delivery.

## Reproducing

Snapshot import (read-only SELECTs afterwards):

```
gzip -dc ~/de-linker-data/snapshots/db-20261110T233636Z.sql.gz | mysql <scratch-schema>
```

Chain readback per inquiry:

```
SELECT option_value FROM wp_options WHERE option_name='linker_inquiry_send_8680';
SELECT id,status,date_created_gmt FROM wp_wc_orders WHERE id IN (8680,8685);
SELECT meta_key,meta_value FROM wp_wc_orders_meta WHERE order_id=8680 AND meta_key LIKE '_linker%';
SELECT option_value FROM wp_options WHERE option_name='linker_commerce_mail_transport_sends';
SELECT action_id,hook,status,last_attempt_gmt,args FROM wp_actionscheduler_actions
 WHERE args IN ('[8680]','[8681]','[8682]','[8685]','[8686]','[8687]');
```

On-box logs (read-only, no writes):

```
grep -E '8680|8685' ~/.logs/mail.log
cat wp-content/uploads/wc-logs/linker-mail-2026-11-09-*.log
cat wp-content/uploads/wc-logs/linker-mail-2026-11-10-*.log
```

## Limits of this evidence

- Every database figure is **snapshot-time** (2026-11-10 23:36:36 UTC). The
  inquiry records and their delivered timestamps cannot have changed since
  (delivery completes within seconds of submission), but the pool counts and
  the #8683 retry state can drift.
- Production MySQL was down throughout, so no live re-read was possible. The
  outage itself is unexplained here and is not diagnosed by this ticket; it is
  an active production fault.
- Two natural inquiries is not a rate. It proves the chain works end-to-end for
  a real customer on the live link; it does not establish accuracy.
- The inbox leg is unverified (above).

## Resource report

- No production write, no mail sent, no mailbox touched (no IMAP connection was
  opened at all). Production access was SSH reads of `~/.logs/mail.log` and
  `wp-content/uploads/wc-logs/` only.
- Scratch database `i_natural_readback` was created locally from the 2026-11-10
  snapshot for these SELECTs and has been dropped; nothing from it was copied
  into the repository beyond the masked figures in this report.
- Worktree `/tmp/i-natural` holds only this report.

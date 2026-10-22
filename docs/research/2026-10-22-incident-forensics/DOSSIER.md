# Public inquiry abuse: entry, quota behavior, and intrusion boundary

Research ticket: [#534](https://github.com/AssassinFlash/de-linker/issues/534). Incident map: [#533](https://github.com/AssassinFlash/de-linker/issues/533). Source baseline: `dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0`. Research performed 2026-10-22, read-only against the WordPress shared host. Times below are UTC; add eight hours for the owner's local time.

## Verdict

The available evidence establishes an active, automated transfer-lure campaign abusing the intended guest contact writer and exhausting the application's outbound notification capacity. It does not establish a WordPress code-execution exploit, administrator takeover, or hosting-account compromise. Those broader possibilities require separate authentication, host, and vulnerability evidence; absence of source drift alone cannot exclude them.

The native admission ledger admitted the sampled operations normally. Its browser buckets were effectively disposable, its two retained connection buckets remained below their allowed capacity, and its ordinary business policy had no site-wide intake or notification-capacity dimension. Disabling mandatory verification on the two ordinary forms exposed that policy mismatch. This was a protection-design failure with a real availability consequence, not evidence that the ledger's atomic counter was bypassed. Sources: the native order/ledger snapshots [E2], quota and identity source [S1–S4], and mail-capacity snapshot [E1].

## Evidence and scope

Private evidence is retained outside Git under `/Users/chesterjohn/de-linker-data/incident-20261022/`. This dossier publishes aggregates and source references, with no sender addresses, raw IPs, cookies, secret material, active malicious links, or credential hashes.

| ID | Primary evidence | Time / scope |
|---|---|---|
| E1 | `recent-runtime-sample.json` | Read at 06:34:15.384751; 80 saved records accepted since 05:45, plus native mail queue/capacity. Includes full frozen record evidence privately. |
| E2 | `forensics/native-sanitized.first.json`, `forensics/native-sanitized.json` | Native read-only database/order snapshots at 06:45:16.073244 and 06:50:29.955551. 88 sampled records, 107 retained ledger receipts, 170 retained buckets. Bucket and subject identifiers replaced by report-local aliases. |
| E3 | `containment-readback.json` and coordinator's change record | Private business verification restored to required at approximately 06:38; native configuration reads ready/enforce/production keys, contact and inquiry verification required. This researcher did not make that change. |
| E4 | `forensics/integrity-manifest.json`, `forensics/integrity-summary.json` | Read at 06:47:22.620332; custom plugin/runtime, owned MU, core file hash comparison, upload executable-extension inventory. |
| E5 | `forensics/user-baseline-summary.json` | Current native user IDs, roles and registration timestamps compared with `cutover-20261022-0541/db.sql.gz`; no membership or role changes. |
| E6 | `forensics/additional-read.json` | Root `default.php` metadata and conservative content indicators; conventional SSH log-directory availability. |
| E7 | `acceptance-522-availability-20261022/deployment.json` | Existing deployment record identifies `20261022T052053999643Z-dcd5560d`; source baseline and local shipped-runtime staging provenance. |

The orders query selected the latest 180 native records and retained those with assessment acceptance timestamps at or after 05:45. It found 88, so this selected window was not truncated by that 180-record limit. It does not constitute a historical all-time inquiry audit. The native ledger is bounded and cleans up expired buckets; counters are not a complete HTTP request log. [E2, S4]

## Timeline and impact

| Time | Observation | Boundary |
|---|---|---|
| 05:46:11.442623 | Earliest accepted record in this window. | Does not establish the first attempt or original campaign start. |
| 05:47:45.835614 | Controlled genuine-looking acceptance record #8037 saved. | The one controlled record is excluded from campaign counts. |
| 06:34:02.175044 | Latest saved record in the first 80-record sample. | 79 campaign records and one controlled record. |
| 06:34:15.384751 | Application outbound ledger at **80/80** sends in rolling 24 hours, **30 queued**, zero terminal failed jobs. | Send ledger covers all mail types, not exclusively spam; queue completion is distinct from recipient delivery. |
| 06:37:57.669249 | Latest saved campaign record in the expanded native sample. | 87 campaign records plus one controlled record, all native guest contact records. |
| About 06:38 | Coordinator restored required verification. | Configuration change, not a new source deployment. |
| 06:45:16.073244 | 88 saved records; latest acceptance unchanged. | First post-containment sample. |
| 06:50:29.955551 | Still 88 saved records and 88 contact-admitted events. | No additional accepted records observed during approximately 12.5 minutes after containment. This does not prove zero attempted attacks. |

The 87 non-controlled records independently match the transfer-lure phrase and the current campaign's destination host. This characterization uses their actual frozen content, rather than treating a Jev label as ground truth. The first 79 campaign records use **79 distinct reply addresses and 79 distinct literal message strings**, with one repeated submitted name and one repeated company value. Amounts and suffixes vary. Exact whole-message deduplication or per-email limits alone therefore would not collapse this campaign. [E1, E2]

## Which writer was used

All 88 recent records have source `contact`, `created_via=linker_contact`, customer ID zero, and received inquiry status. All 88 request UUIDs map to native ledger receipts with purpose `contact`, status `completed`, and outcome equal to that exact order ID. Each receipt has the expected browser-hour, browser-day and connection-hour debits. The 88 records have 88 distinct bound subjects. [E2]

The native owner of this action is `Contact\Handler::process`, registered on both guest and signed-in `admin-post` hooks. Its sequence checks the native form nonce, validates fields and PublicGuard, then calls `Business::run`, which reserves and dispatches admission before `Sender::message` persists the order. The saved data and ledger therefore strongly identify this intended public contact path. No matching access log was available through the two conventional SSH log directories inspected, so the exact HTTP request URI, user agent, raw source IP and script implementation are not independently proven. [S2, S3, E6]

Nonce and signed-start values are embedded in the public form. A valid form token proves an acceptable form context; its existence alone does not identify a human. The hidden honeypot remains present. When the new business admission mode is active, the older fixed three-second minimum and legacy three-per-connection gate are intentionally bypassed in favor of the new policy. [S2, S3]

## Why the configured quotas did not stop this incident

| Dimension | Policy | Actual evidence | Interpretation |
|---|---|---|---|
| Guest browser/hour | 10 | Each retained browser-hour bucket used one unit. | Every request had a different browser-bound identity. |
| Guest browser/day | 20 | Every retained browser-day bucket used one unit. | Browser identity churn avoided accumulating spend in one bucket. |
| Connection/hour | 100 | Two 06:00–07:00 retained buckets used **21 and 42**. | Both remained well below their caps. |
| Ordinary site-wide business intake | No dimension in this policy | No site-wide business debit on these receipts. | Multiple fresh subjects may collectively admit more notifications than the site can send. |
| Optional customer acknowledgement/site/day | 10 | 10 admitted, 78 quota refusals in the current daily event aggregate. | This bounded optional acknowledgement only, not the team notification or saved inquiry. |
| Outbound application mail | 8/minute, 80/rolling 24h | 80/80 and 30 queued at 06:34. | Resource exhaustion occurred before broad connection quotas were reached. |

`Identity::current` accepts any syntactically valid 32-hex browser cookie, otherwise issues a fresh one. It does not require that a cookie value was previously issued by the server. Hashing that value prevents disclosure in policy storage but does not make it an identity that resists rotation. The 88 different bound subjects are evidence of identity churn; they do not distinguish discarding issued cookies from supplying new syntactically valid ones. Merely signing cookies would still allow a bot to obtain new issued cookies, so cookie signing alone is insufficient. [S1, E2]

Connection identity uses the server's `REMOTE_ADDR` and an HMAC, without trusting arbitrary client-forwarded headers. The two retained connection buckets establish two distinct server-derived connection identities, not necessarily two humans, two physical machines, or two independently verified public IPs. The preceding 05:00–06:00 connection buckets have expired from retained bucket metadata, so the whole-period raw-origin count cannot be reconstructed from this snapshot. [S1, S4, E2]

There are **no recorded contact quota-refusal events** in this daily event aggregate. Atomic quota reservation is present and each saved contact is accounted for. The experiment demonstrates that configured dimensions were insufficient for notification capacity and that browser quotas needed a costly trust signal when mandatory proof was removed. It does not demonstrate lost debits, a race, forged ledger state, or arbitrary bypass of a reached cap. [S1, S4, E2]

## Other public writers: source boundary checked

This is a source-path inspection, not an assertion that every installed third-party plugin and every possible WordPress route received a penetration test.

| Public writer | Current native owner / admission | Incident evidence |
|---|---|---|
| Ordinary contact | `Contact\Handler` → `Business::run('contact')` → native sender | All 88 sampled records used this purpose. |
| Ordinary inquiry | `Inquiry\Handler` → `Business::run('inquiry')` | No sampled order used this purpose. |
| Genie contact / inquiry | Tools `Resources::dispatch` applies shared admission to registered route and sets trusted server context before Commerce handoff. | No such business receipts in the recent incident cohort. Commerce's handoff is a trusted PHP filter, not a separate public REST endpoint. |
| Conversation email | Tools `ResourcePolicy` maps the email route to `conversation_mail`, shared business policy and proof admission. | No cohort evidence identifying it as the entry. |
| Registration / password reset / login / draft changes | Native owners registered by Commerce protection module; verification remains required according to action and failed-login policy. | No newly registered native users in the observed window. No complete HTTP attempt counts. |
| Native Woo checkout / Store API checkout | Retired checkout blocked before the alternative native order creation boundary. | No sampled record has an alternative checkout creation channel. |
| Comments / pingback | Native and REST comment gates; unused pingback write disabled in enforcement mode. | No incident evidence that this was the inquiry entry. |
| Genie turns, attachments and engineering tools | Resource dispatch plus per-action/site/provider budgets. | Those budgets are separate from ordinary business mail and cannot prevent the demonstrated contact path from consuming team notifications. |

Primary route/owner sources: [S5–S8]. Counter coverage is limited: `Admission::reserve` rejects missing proof **before** calling ledger reserve, so unchanged contact-admitted counters and absent quota-refusal events do not establish absence of denied attack attempts. [S4]

## Intrusion and integrity boundary

| Check | Result | Limit |
|---|---|---|
| Shipped custom source against baseline | **869/869 files match**: Commerce 560, i18n 62, Tools 247. | Deployment excludes development directories and vendor for this source comparison. |
| Full custom runtime against shipping stage | **1,220/1,220 match**, no extra files in those three deployed plugin trees. | Stage is local deployment evidence, not an independent signature authority. Includes runtime vendor files. |
| Owned MU artifacts | **5/5 match** source. | Other hosting and LiveCanvas MU files were inventoried, not fully authenticated by a fresh external package manifest. |
| WordPress core against cached package | **3,338/3,338 match** local `wordpress-7.1.3-en_US.zip`. | Offline cache comparison; provenance of the cache was not freshly verified against official signed/checksum evidence. |
| Extra core-root file | `default.php`, 16,359 bytes, metadata modification date July 3, Hostinger content marker; no checked eval/base64/exec patterns. | Outside core package. Metadata and narrow pattern checks alone are not a full malware verdict. |
| Executable extensions in uploads | Zero `.php`, `.phpN`, `.phtml` or `.phar` files found. | Does not detect every execution path, polyglot, server rule or executable content type. |
| Native users | 15 users, one administrator; same IDs, roles and registration dates as the pre-incident backup. Latest registration October 19. | Existing account/session theft can occur without creating a user or changing a role. |
| Application passwords | One current application password in total. | Count alone does not establish who created/used it; creation/usage audit not obtained. |
| Cron inventory | All current hook names already appear in the pre-incident SQL backup. | Name presence does not prove callback integrity, argument safety, or external scheduler health. |

Sources: [E4–E6]. These observations support public-form abuse and show no custom-source, cached-core, new-user or new-role drift in the checked scope. They do **not** certify the complete hosting account as uncompromised. Authentication events, SSH/control-panel access, installed third-party package vulnerability status, plugin/theme runtime beyond the explicitly owned files, server configuration and database content require their own evidence.

The WordPress shared-host WP-CLI process reported **PHP 8.3.35**, SAPI `cli`, WordPress **7.1.3**, WooCommerce **11.2.0**. That does not prove the browser-facing web SAPI runs the same PHP build, nor that a particular advisory has been patched. It is separate from the VPS's Python services. The Hostinger PHP notice must be evaluated against its exact affected build and the actual web runtime, rather than inferring vulnerability or safety from the major/minor version alone. [E2]

## Protection consequences for the coordinator

1. Preserve the current containment while testing the legitimate submission path in the affected browser. The 12.5-minute no-new-admission observation is encouraging but is neither a client acceptance test nor evidence that requests ceased.
2. Couple abuse controls to the scarce resource: protect team-mail capacity and oldest queue age while retaining every accepted inquiry in an owner-visible record. Do not turn a model label into silent deletion. A reserved critical-notification lane or campaign aggregation requires an explicit implementation contract and receiving-side validation.
3. Add a cross-identity campaign dimension using bounded normalized content/destination evidence, with care for genuine shared templates and common company domains. Exact payload hash, recipient count and browser cookie alone were each easy to vary in the observed campaign. No language- or nationality-wide rule follows from this evidence.
4. Treat client-replaceable browser identity as a convenience bucket. A low-friction adaptive gate needs a successful action-bound server proof or other justified trust signal before expensive side effects. The legitimate-browser proof failure must be diagnosed and repaired; broadly removing proof without resource-coupled safeguards recreates this failure mode.
5. Add rejection observability before ledger reserve and record stage-level queue timing. Current counters cannot supply an honest overall request rejection rate or prove post-containment attack volume.
6. Complete the broader host/runtime/package/authentication audit separately. The evidenced incident mechanism is sufficient to fix the inquiry abuse path now; it does not justify dismissing the owner's PHP security notice.

This research made no production write, cache flush, configuration change, real mail send, external model call, destructive action or request to the malicious destination. No implementation branch or PR is created by this dossier.

## Primary source references

All source links are pinned to the deployed baseline.

- S1: [BusinessPolicy](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/BusinessPolicy.php), [Identity](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Identity.php), [Allowance](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Allowance.php).
- S2: [Contact handler](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Contact/Handler.php), [public form fields](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Contact/Form.php), [PublicGuard](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Inquiry/PublicGuard.php).
- S3: [Business boundary](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Business.php), [native sender](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Inquiry/Sender.php).
- S4: [Admission](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Admission.php), [Ledger](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Ledger.php), [verification configuration](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Configuration.php).
- S5: [Protection module native owner map](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Module.php), [comments](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/Comments.php).
- S6: [Tools resource boundary](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-tools/includes/Protection/Resources.php), [resource action policy](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-tools/includes/Protection/ResourcePolicy.php), [Commerce Genie handoff](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Genie/Module.php).
- S7: [Native inquiry handler](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Inquiry/Handler.php), [retired checkout transports](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Inquiry/Checkout.php).
- S8: [Application mail throttle](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Mail/Throttle.php), [optional acknowledgement budget](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/plugins/linker-commerce/includes/Protection/ReceiptBudget.php), [shipping exclusions and artifact inventory](https://github.com/AssassinFlash/de-linker/blob/dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0/tools/cutover/src/linker_cutover/plan.py).

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

The native owner of this action is `Contact\Handler::process`, registered on both guest and signed-in `admin-post` hooks. Its sequence checks the native form nonce, validates fields and PublicGuard, then calls `Business::run`, which reserves and dispatches admission before `Sender::message` persists the order. The saved data and ledger therefore strongly identify this intended public contact path. At the initial inspection, no matching access log was available through the two conventional SSH log directories inspected. The subsequent Hostinger CSV addendum supplies independently recorded HTTP paths, source identifiers and user-agent claims, but does not expose the actual attack script, request bodies or cookies. [S2, S3, E6, H1–H2]

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

## Addendum: actual Hostinger HTTP, account and malware evidence

The coordinator requested an additional account-level investigation after the initial source/ledger research. This addendum uses the **actual de-linker Business Web Hosting account**, inspected through a newly created browser tab. The expected existing hosting account was verified privately; no password entry, new login, account setting change, malware scan initiation, production code change, queue operation, paid model call or mail send was performed. The researcher's own two hPanel tabs were separate from the coordinator's deployment tab.

### Raw HTTP export and retained evidence

Hostinger's Analytics → Access logs view generated an official downloadable CSV. The initial visible six-hour summary showed 6,106 requests; the subsequently prepared file contains **6,123 rows**, so the exported file, not the earlier live counter, supplies the statistics below. Its explicit `Z` timestamps cover **2026-10-22 04:36:02–10:35:41 UTC**.

- Private file: `/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/de-linker-access-last6h.raw.csv`.
- Size: **1,328,992 bytes**.
- SHA256: **`aa4368246e41d36c621a17dee706a70ed3b4aeddee90784c44b641abe9bbea90`**.
- Columns: status, source IP, host, request, user agent, country code, bytes, duration and timestamp.
- The export contains no request body, browser cookie, application request UUID, redirect Location or deployed release ID.
- Evidence directory is mode **0700**; all evidence files, raw source identifiers and screenshots are mode **0600**. IPs, account addresses and user-agent originals remain private; `origin-1` and `origin-2` below are report-local aliases. [H1]

| HTTP scope | Requests | Relevant observations |
|---|---:|---|
| Entire exported six-hour window | 6,123 | 164 source IPs; 2,293 POST and 3,830 GET. This total includes ordinary maintenance and service traffic. |
| Incident window 05:30 ≤ UTC time < 07:00 | 1,486 | 42 source IPs; 511 POST and 975 GET. |
| Incident-window POST `/wp-admin/admin-post.php` | 148 | 98 from origin-1, 49 from origin-2, plus the single Mac-labelled controlled-test source. All returned HTTP 302. |
| Entire export, the two repeated origins' admin-post requests | 573 | 382 from origin-1 and 191 from origin-2, all HTTP 302. |
| 06:38–07:00, after required-verification containment | 36 | Further admin-post requests persisted. Of these, 19 precede the final 06:50:29.955551 native sample; the saved cohort stayed unchanged through that sample. The remaining 17 are outside its observation window. |
| Entire export, `/xmlrpc.php` | 138 | All returned HTTP 403; this is a refusal observation, not proof of an exploitation attempt or successful authentication. |
| Incident-window HTTP 5xx | 0 | This does not negate the proven mail-capacity exhaustion or certify all dependency health. |

The two repeated origins account for 2,865 total requests. Their counts form the same request pattern: each admin-post POST is accompanied, in aggregate, by two successful contact-page GETs, one successful root-page GET and one root-page HTTP 301. The source IP labels in Hostinger are NL and SE; those labels do not identify the operator or justify a country-wide block. Both sources cycle through the same five Windows/Chrome user-agent strings. User-agent claims are not authenticated client identities. The controlled source's one admin-post occurs at **05:47:47 UTC**, consistent with the independently retained #8037 test. [H1, H2]

### HTTP/native correlation and the HTTP 302 boundary

The native acceptance window is **05:46:11.442623–06:37:57.669249 UTC**. There are exactly 88 HTTP admin-post requests in the matching cohort, timestamped **05:46:12–06:37:58 UTC**, and 88 previously evidenced native records, including one controlled record. The matching search permits an HTTP timestamp from 0.5 seconds before to four seconds after a native timestamp; this is a temporal tolerance, not a shared request identifier. A complete one-to-one temporal alignment can be made with the previously used nearest-unused rule; its maximum recorded timestamp difference is **2.012 seconds**. In the retained 06:00–06:38 segment, the two HTTP-origin counts are **42 and 21**, exactly matching the native connection-bucket totals previously observed. This substantially strengthens attribution to the intended contact writer. [E2, H2]

However, the initial phrase “uniquely corresponding requests” would overstate the export. The CSV has no application request UUID, body, cookie or redirect Location; adjacent requests at second-level timestamp precision permit alternative mathematical time pairings. The result is **complete temporal cohort alignment**, not a cryptographically or mathematically unique per-request binding. The native request UUID → order ID mapping remains the separate, stronger application-side evidence. [E2, H2]

HTTP 302 is the native form handler's redirect transport for both accepted and refused submissions. It must **not** be counted as successful inquiry acceptance, successful mail delivery, or successful authentication. The 36 continued POSTs between 06:38 and 07:00 demonstrate that incoming requests continued. Nineteen fall within the native observation window ending at **06:50:29.955551 UTC**, during which the saved cohort remained at 88. The other 17 occur after that native readback, so that sample cannot establish their admission outcomes. Thus “no new saved inquiries through 06:50:29” was an application-level containment observation, not evidence that remote traffic stopped or that later attempts had the same outcome. [S2, E2, H1]

The export also contains **12 admin-post POSTs from the same two origins after the coordinator-reported 10:29 UTC publication marker for release `003cedd3`**: eight from origin-1, four from origin-2, timestamped **10:29:10–10:34:52 UTC**, all HTTP 302. The file ends at 10:35:41. The marker does not establish the exact moment the new PHP code began serving requests. The HTTP rows alone do not prove which release executed or whether any operation was admitted, saved or notified. [H3]

The coordinator's separate native readback at **10:49:58 UTC**, retained locally, records three new contact orders in the `campaign` lane: #8218 at **10:32:56 UTC**, and #8219/#8220 at **10:32:58 UTC**. All three have `held=true`, an empty wake marker, no assessment result and no notification job. Registry occupancy is exactly three in that lane; the distinct `campaign_count` counter reads 30. This proves the new intake behavior had executed by 10:32:56, with those records retained rather than turned into new assessment or notification work. It does not establish the exact effective-start time or a one-to-one mapping between the counter value 30 and the 12 CSV rows. The same readback retains 38 private/held mail jobs; a count alone does not establish each job's provenance. The coordinator separately verified the original historical jobs and blocked-callback behavior in its own acceptance evidence. This researcher did not query or mutate production during publication. [H7]

### Existing malware scan result

The actual de-linker malware-scanner page states that no malware was detected in the **past 30 days** for the Business Web Hosting plan. The same page explicitly limits the scanner to **website files and excludes database content**. It does not show an exact latest scan timestamp. No new scan or paid cleanup was started. [H4]

This adds a hosting-provider file-scan observation to the earlier byte comparisons. It does not exclude database injection, credential or session theft, undiscovered files, scan blind spots or abuse of an intended public form. Do not describe it as a fresh full-site security pass.

### Account activity and hosting-operation history

The correct hosting account's Account activity page exposed **53 records**, all saved privately using its 100-row view: 26 email-type and 27 Google-type entries; 52 desktop and one mobile. Its introductory text describes connected devices and the ability to log them out. The two entries dated October 22 display **16:03:22** and **15:03:52**, both email/desktop. **The account-activity UI did not explicitly label its timezone**, so those displayed values are retained verbatim and are not converted into a definitive exclusion of the 05:30–07:00 UTC incident window. [H5]

Within this displayed set, neither of the repeated HTTP-origin IPs overlaps an account-activity IP. The two newest account entries share the IP of the independently controlled HTTP test source. Those are private identifier comparisons, not proof of the operator behind any login or of account security. Failed login attempts, SSH authentication, cookie reuse and complete account audit events are not supplied by this connected-device table. No session was revoked and no account setting was modified. [H5]

The website's separate Advanced → Activity log view displayed 291 hosting-operation records. Its first five visible entries were October 14 hosting/database operations; this view was saved but not presented as a complete authentication or SSH audit. It contains a different event class from both HTTP access and connected-account activity. [H6]

### Hostinger addendum evidence index

H1–H6 evidence is under the private `incident-20261022/hosting-logs/` directory. H7 is the coordinator's separate local native readback. Only aggregates and boundaries are committed here.

- H1: raw official CSV, `access-export-manifest.json`, `access-analysis.sanitized.json`, `containment-overlap.sanitized.json`; observed source UI `https://hpanel.hostinger.com/websites/de-linker.com/analytics`.
- H2: `native-http-correlation.sanitized.json`, `correlation-boundary.json`, `origin-request-shape.sanitized.json`, and private origin alias map. Pairing is explicitly non-unique at the export's time precision.
- H3: `post-deploy-http-tail.sanitized.json`; deployment time/release supplied by the coordinator, actual tail rows supplied by Hostinger.
- H4: `malware-full.ax.txt`, `malware.png`; observed source UI `https://hpanel.hostinger.com/websites/de-linker.com/hosting-security/malware-scanner`.
- H5: `account-activity-all.ax.txt`, `account-activity-rows.private.json`, `account-activity.sanitized.json`, `account-activity.png`; observed source UI `https://hpanel.hostinger.com/profile/account-logs`. No explicit UI timezone was observed.
- H6: `activity-view.ax.txt`; observed source UI `https://hpanel.hostinger.com/websites/de-linker.com/advanced/activity-log`.
- H7: `/Users/chesterjohn/de-linker-data/incident-20261022/deploy-542/live-consumers-readback.json`, timestamped 10:49:58 UTC; coordinator-owned production readback, read locally without modifying it. The three saved-record times were converted from its Unix timestamps to UTC. It does not identify the effective serving-start timestamp or bind native counter 30 to specific HTTP rows.

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

# Public protection: production acceptance, 2026-10-22

The customer-facing protection and observation release is deployed and enabled.
Merged implementation: [PR527](https://github.com/AssassinFlash/de-linker/pull/527),
`c022f81a48010c9ee66967245d81468495b1b21f`. Site deployment
`20261021T235952677061Z-c022f81a` completed with native activation, presentation,
OPcache reset and verification. The atomic rename took0.017seconds.
The final operational supplement for the retention repair in this evidence PR is
recorded in [rollout issue522](https://github.com/AssassinFlash/de-linker/issues/522).

## Actual enabled state

- Production uses `enforce`, real keys, configured/ready=true, test_keys=false.
  Inquiry assessment is enabled and the actual client is configured. Test-mail
  mode is off. See `evidence/production-current.json`, not merely saved settings.
- Actual WP callback objects and REST handlers were inspected in the running
  process:25 named hooks and54 mutating route registrations. Twelve critical
  deployed PHP/JS files hash-identically match the merged source. This supplements
  the diagnostic consumer inventory; declarations alone were not acceptance.
- Genie and quality worker provider/work gates are both `enforce`; engine's
  private gate is `enforce`. The actual service processes use persistent journal
  paths outside release directories and the existing token. Private health200,
  unauthenticated expensive endpoints401 before work; an authenticated engine
  request without its trusted subject returns400 before computation.
- Runtime provider credentials are present; Jev uses native
  `https://openrouter.ai/api/v1/systemone`, `typesafe/jev-1.13`, and DeepSeek uses
  its official API. No model, global routing, DNS, paid plan or password change.
- Provider SQLite was actually used by the three natural classifications. Its
  private directory/file are0700/0600 and integrity isok. Native work/engine slot
  stores were initialized using acquire/release of one synthetic readiness slot;
  both stores are0700/0600 with integrityok and the readiness slots released.
  That is storage readiness, not a production load/concurrency experiment.
- The authenticated engine version is read from running source/loaded data. It
  changed from`0ceb196c…0323` to`2d41c946…4b2db` after the existing feed refresh;
  WP and the live engine agreed at the later readback. No static WP version is
  substituted. The established `/root/.cache/linker-engine` remains in use.
- Official WindPress compilation completed at2026-10-22 08:11:22 Asia/Shanghai;
  the native cache diagnostic readsnull. No plugin CSS or snippet workaround.

## Entry and failure-path matrix

“Local” below means actual loaded WordPress/Woo fixtures and/or the live-snapshot
g522 browser; it is not a claim that attacks were submitted in production.
Browser account, contact, inquiry and tool states were checked in EN/DE at390
and1440. Earlier staff-card states and manual correction are in511/516 evidence.

| Entry | Protection and normal-customer behavior | Executed failure/recovery evidence | Production readback |
|---|---|---|---|
| Browse home, products, public pages | No challenge or model on idle reads | Off/on contact pixel comparison in511; normal combined native page reads | Seven independent current HTTP endpoints200; actual public HTML has no idle Cloudflare script |
| Contact, guest/account | Action-bound verification plus shared business ledger before save; Jev only after save | EN8463/DE8465 actual browser submissions received; DE verification outage retained input then retry succeeded | Both native admin-post callbacks loaded; EN/DE form marker/bundle; natural8022/8024/8026 below |
| Direct inquiry, guest/account | Separate from Genie model quota; stable operation UUID and native received record | DE8467/EN8469 after actual Genie429 preserved exact question; receipt quota yielded explicit no-confirmation message while team job survived | Both native callbacks loaded; EN/DE `inquiry` + `draft_write` form markup; actual production prepare200→official widget200→verify200 without submitting a business form |
| Registration | Native Woo/Core validation before account creation; verification failure retains two-step input | EN/DE actual synthetic users80/81 created as pending; DE outage→retry created exactly one account; EN outage-only attempt created no account | Woo/Core registration and created callbacks loaded; EN/DE markup; Woo registrationyes, Core registration0 |
| Login | Fresh ordinary login stays unchallenged; repeated failed use adds scoped verification without preventing a verified correct password | EN/DE actual wrong-password use→verification outage→same filled form retry→pending account signed in | Native before-password/failed/complete callbacks loaded; fresh EN/DE page intentionally has no login marker |
| Password-reset request | Native lostpassword check before key/mail; no password change performed | EN/DE outage retained email; same-form retry reached native reset-link-sent confirmation; local mail capture only | Native lostpassword/profile callbacks loaded; both native reset URLs200 and protected markup |
| Solution draft / Woo mutation | Shared pre-mutation guard for native forms, reorder, wc-ajax and Store API; reads free | Actual native fixtures cover missing/invalid proof, retries and shared subjects; normal browser draft/inquiry preserved | Loaded wp_loaded/reorder/REST guards; actual Store API registrations audited; Store checkout remains closed |
| Comments / reviews / XML-RPC | Native form and REST comment guard; pingback write removed in enforce, existing authenticated permissions retained | Native WordPress fixtures create the named local comment surface and prove rejection before write/retry behavior | Native/REST/comment-complete hooks loaded; synthetic methods filter removed pingback.ping, retained wp.newComment/read methods; existing public comments currently closed |
| Genie hero/dock/full page | Shared subject budget; actual expensive work slots; quota retains question and direct-inquiry recovery | EN/DE actual browser429 and preserved handoff, not just a rendered limit state | Native resource dispatch loaded, actual turn/contact/inquiry/conversation/email/vote route mapping, service gatesenforce |
| Attachments and voice | Attachment count/bytes/pages checked before expensive read, same real turn/work/provider budget | Native client/service fixtures cover image/PDF/CSV/XLSX/voice admission, refused work and released leases | Actual deployed Resources/ProviderBudget/Genie service and process modes; no production file/voice load test |
| Configurator / roof / report / save | Separate engineering limits, one subject job, site slots, immutable input+version reuse, PDF/storage budgets |521 native fixtures and EN/DE rendered failure/recovered/result/export states; combined native resource21/338 | Actual engine proxy/resource mapping and token gates; private version200; missing trusted subject400 before work |
| Actual model outlets | Each attempted upstream call incl retry/tool loop debits shared persistent provider budget; failures explicit | Actual assessment transport28 cases: deadline/corrupt/locked/depleted journal, no late dispatch; translation/tool/embedding gateway fixtures | Actual PHP hooks, service process modes, private provider401; natural Jev attempts in real persistent journal |
| Recovery / team notification | Customer save never waits for model; absolute10s background window; uncertain on error/quota/timeout | Native scheduler callback and failed Outbox write/retry fixtures retain one logical team handoff | Real recurring minute event args[]; independent VPS timer executes native cron; heartbeat49.02s old at03:53:49UTC |
| Staff customer evidence | Frozen source facts, unknowns and model attribution; append-only manual correction/withdrawal; no auto approval or external company lookup |516 real HPOS+classic33/257, concurrency/privacy/stale-edit fixtures; EN/DE actual staff correction/history390/1440 | Deployed evidence source hash matches; all three natural records have frozen evidence; no production staff decision changed |

Production public-page evidence preserves the original mistaken guessed German
reset URL404. The authoritative `wc_lostpassword_url` and actual visible DE link
both identify `/de/mein-konto/passwort-zuruecksetzen/`; that URL is200 with the
password_reset marker and enforce client. See `native-de-reset.json`. No URL was
changed to hide a failed probe. The generic dock-presence signal was removed from
the HTML report because it does not identify a standalone tool application.

## Natural production observations

These contact records arrived naturally during the observation interval. No
production test inquiry, malicious URL visit or attack submission was performed.

| Inquiry | Acceptance→classification stored | Jev service time | Queue time | Frozen first label | Team job |
|---|---:|---:|---:|---|---:|
|8022|0.918410s|0.315135s|0.332856s|suspected_spam / fraud_or_phishing|8023|
|8024|2.440489s|0.181301s|1.983552s|suspected_spam / fraud_or_phishing|8025|
|8026|1.898932s|0.271700s|1.362079s|suspected_spam / fraud_or_phishing|8027|

All three retain `inquiry-received`, pending=no, the immutable `initial_result`
and the matching latest result. The returned model was
`typesafe/jev-1.13-20260917`, rubric`inquiry-observation-v1`. Team job pointers are
stored. Outbox jobs had already been removed by normal successful-job cleanup;
their absence is **not receiving-mailbox delivery evidence**. Three examples
cannot establish a false-positive rate or production classification accuracy.
Labels never quarantine/reject/delete an inquiry or approve/restrict an account.
The10s limit is a classification window, not an inbox delivery-time promise.

## Initial operating limits

These are the delegated initial policy choices in507/508, not measured traffic
percentiles or euro budgets. Counters and fixed refusal reasons are staff-visible.

| Resource | Initial allowance |
|---|---|
| Anonymous business submissions |10/hour,20/day; account20/hour,100/day; direct connection100/hour |
| Optional unverified confirmation |2/target/hour,5/target/day,10/site/day; suppressing this optional receipt preserves the record and normal team job |
| Genie | Anonymous30/day and10/10min; account120/day and30/10min; site500/day; actual in-flight subject1/site2 |
| Files |3/turn; image6MiB,PDF16MiB,CSV1MiB,XLSX6MiB; combined20MiB; PDF4pages; daily10 anonymous/40 account/100 site |
| Actual provider attempts | DeepSeek2000/day,Jev200/day,runtime embedding2000/day; includes retries and tool loops, excludes offline embedding bake |
| Engineering | Anonymous30/hour,account120/hour; subject1/site4 in flight; PDF10/subject/day,100/site/day; same actual input+version reused |
| Light storage writes |500/subject/day,2000/site/day |
| Mail transport | Existing shared-host10/minute,100/24h and24h retry retained |

Genie depletion does not consume the separate direct-inquiry allowance. Model
budget/storage failure becomes explicit uncertain for the inquiry and ordinary
team notification; the customer save does not call Jev. Verification-service
failure is a separate pre-write condition: retain fields, retry, or contact the
published team email. There is no language, nationality, external-link or
negative-sentiment rejection rule. Shared-company-network/native atomic fixtures
are distinguished from geographies: only this machine's actual target browser
and network were verified with live Turnstile keys. No all-regions claim.

## Independent execution and operational evidence

`linker-wordpress-cron.timer` is enabled/active on the existing VPS. Once per minute
its bounded service requests the existing native wp-cron.php (curl55s/systemd60s),
which executes the registered60s assessment recovery and normal due jobs under
native cron locking. Real scheduled ticks and fresh heartbeat were read back,
independent of a visitor. This is not a claim that Hostinger hPanel was configured;
the available Google logins did not grant that site's panel. No new access token.

Current services: engine`/opt/linker-engine/20261021T235708937268Z`,
Genie`/opt/linker-genie/20261021T235727114477Z`. `service-current.json` supersedes
the intentionally retained initial activation readback where journals were not
yet created. `private-storage-readiness.txt` supersedes the earlier absent
work/engine files in `process-journals-before-readiness.json`.

The161-sample concurrent deployment probe has `successful=false`: a30s proforma
timeout and a commerce REST tunnel503 occurred in its steady phase before the
atomic switch. Deployment exited0, fatal log unchanged, directory rename proved;
the later switch/after samples passed. The original proof is retained unedited.
A fresh independent seven-endpoint matrix is all200; actual EN/DE browser pages
also load. This supports current functionality; it does not prove zero downtime.

## Backups, discovered retention repair and rollback

Full local backup:
`/Users/chesterjohn/de-linker-data/cutover-20261021-2259/manifest.json`;
40214 files, final DB7079156bytes, SHA256
`05d87c621119a153686880b842d5673b13640626846f2a3fa582d5df8c7cfee8`.
The first strict backup failed on concurrent deployment .prev changes and was
never called complete. Read-only reconciliation and refreshed DB/options passed
the three file-set checks before the final manifest was written. Existing private
site config/VPS env/releases were freshly backed up at
`/Users/chesterjohn/.config/de-linker/rollouts/522/before-20261021T235056Z`.
Private files0600/directories0700; credentials and raw customer content omitted.
Atomic code rollback tree is retained on the web host at
`/home/u388076051/deploy-prev/20261021T235952677061Z-c022f81a`.

The final check found an actual release helper bug: it counted persistent
`ops/state/index` directories as versions, deleting the preceding engine code.
This PR restricts discovery to exact publisher timestamp directories. Its real
shell regression first failed against the deployed helper, then passed after
repair: four publishes retain three versions, preserve persistent directories,
and actually roll back to the previous version. Spec and Standards incremental
reviews both PASS; bash syntax, all3 release tests and Ruff PASS. No runtime
business policy changed. The old engine directory cannot be described as retained.
The replacement rollback baseline is explicitly reconstructed from the reviewed
pre-protection main`a33a0bce` at
`/opt/linker-engine/20261021T235650000000Z`, with source provenance and native
health/readiness proof attached to522. It is not a byte-identical recovery of the
lost historical runtime directory. The preceding genuine Genie release
`20261021T173959832342Z` is still present. The source helper activation/readback
after this evidence PR's green merge is attached to522, without another live
application code switch.

Rollback order for the operator (do not run merely to demonstrate a rollback):

1. Back up current private config/env and pending counts. Set public modeoff to
   restore native writes; set new inquiry assessment optionno. Keep the recovery
   timer running until all existing PENDING handoffs are delivered normally.
2. Restore the private environments from the named0600 backups via temporary
   files + atomic replace. Restore the known engine baseline and genuine previous
   Genie release with the repaired `release.sh rollback`, then the existing
   activation helper; prove health/version/token paths again. Preserve engine
   state/feed/cache and all persistent journals; never clear real inquiry records.
3. Run the existing `linker-cutover rollback-deploy --write` from this checkout to
   atomically restore the previous site manifest/code. It verifies plugin status
   and native read paths. Rebuild native WindPress cache for restored templates.
   Prefer the narrow mode/config rollback if there is no code regression.
4. Read back modes, real hooks, seven public reads, authenticated private health,
   pending handoffs and heartbeat. Do not restore the old database over newly
   received customers merely to roll code back. Full DB restore is a separate
   recovery action with current data backup and reconciliation.

## Verification and cleanup

Combined source had full `just check`/`just test` exit0 and both full diff reviews
PASS; final narrow source throughfef52ea7 PASS. PR527 head
`e7a8d41ea572ef00d19fd25c8cd8a5ea846bbe6f`, CI39695586479 check andmu-smoke
both success. Actual tools JS465/54 files, provider/deadline28, engine153,
Commerce125/1242, Tools85/677 (23 documented prerequisite skips), final resource
admission21/338 and warmed-proof form8/8 provide the relevant execution evidence.
511/516/519/520/521 acceptance directories retain detailed cases and copy review.

Local account native readback: synthetic users80/81 pending; the English
outage-only registration created no account. Local account fixtures were removed,
wp-config restored byte-identically, TestModeoff; normal local disk mail capture
is retained. Earlier named business/resource fixtures and exhaustion were also
restored. No production test mail, account registration, password change or
customer approval was performed. Existing production draft quantity/question
were only focused for verification warm-up and remain unchanged and unsent.

This record claims current first-stage protection/labels/budgets/evidence and
recovery readiness. It does not claim perfect spam exclusion, measured model
accuracy, every geography's verifier availability, exact spending, or a new
receiving-inbox acceptance test.

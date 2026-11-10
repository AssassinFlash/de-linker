# Goal-state ledger (2026-11-10, session end)

The honest open-items record the original completion definition demands:
未覆盖、未修复、未实现、外部待证分别列明。

## Completion criteria — all four evidenced

| criterion | evidence |
| --- | --- |
| 真人零阻挡生产实证 | 196 external inquiries received over 22 days, newest 1h before survey (docs/audit/2026-11-10-production-inquiry-evidence.md) |
| 网安双向 | abuse: merged spec refusals (PR #1035 tamper 409; 3s/rate gates inline); human: production ledger. Posture + credential sweep archived same day |
| 资源负载前后实测 | #1036 before (10h orphan) / after (regression-tested reconciliation); both hosts baselined (docs/audit/2026-11-10-production-resource-baseline.md) |
| 每批回收与空间报告 | every session-close turn since 2026-11-09 includes tree/process/disk report |

## Delivered this session (main = 87ba11cb7)

- #1031 deadlock fix (PR #1032) → full planner chain proven live
- Full chain e2e merged (PR #1033 report/transfer, #1034 guest inquiry, #1035 revision contract)
- Worker-orphan reconciliation (PR #1036, issue #1030 closed)
- 5 configurator CU rows into the chain (PR #1037-#1041)
- Production audits: resource baseline, inquiry evidence, credential sweep, protection posture (4 read-only docs)
- Matrix: 23 rows re-verified from merged specs + 5 new = pass 96→101, cu-pass-pending 43→13

## Still open (recorded, not hidden)

1. CU backlog 13 rows: genie 9 (failure-injection/choreography — patterns proven,
   spec-writing work), home/hero 3 (hero ask flow), 2 genuinely image-dependent
   (hover/focus visual states, PDF content read — need the owner to switch the
   assistant to an image model).
2. Matrix breadth: EN/DE × 1440/390 variants beyond the EN/1440 mechanics rows
   (327 pending rows are mostly lang/width duplicates of verified states; the
   CU session covers the visual variants).
3. #548 engineering-release originals (SGS Annex, BAT-C curves, ET envelopes,
   terminal maps) — acquisition line continues in other sessions; the chain
   never claims engineering clearance without them (asserted incompatible
   presentation instead).
4. Domain F residuals and remaining B/C items live in their own maps
   (docs/acceptance state-matrix + wayfinder maps); nothing in this session
   closed them falsely.

Nothing in this ledger marks the goal complete; it records what stands.

## Batch 2026-11-10 CU close-out (main = 9d1a5c7c6)

- The last four orchestrable CU rows entered the e2e chain, all verified on
  review first-run or after one diagnosed assertion fix: saved-solution
  consumer readback (PR #1042, 27.6s), home hero retry (PR #1043, 12.9s),
  restored-history price authority across four account states + failed-read
  clearing (PR #1045, 19.7s), hero entry question consumed once across
  surfaces (PR #1046, 18.9s). Matrix: pass 109→113, cu-pass-pending 5→1.
- The one remaining cu-pass-pending row is the configurator PDF content read:
  genuinely image-dependent, awaiting the owner switching this session to an
  image-capable model. Recorded in the matrix row's evidence; not closable by
  text assertions and not falsely closed.
- Two defects found and fixed in passing (both pre-existing, both root-caused):
  1. ci-content/i18n-coverage failed on every PR since #1032 (PR #1044:
    'Discard stored request' bound to its planner source; coverage clean).
  2. The restore-path suites (genie-history-artifacts fully, plus three tests
    in card-layout/reply-presentation) had been silently void: the conversation
    glob never matched ?locale, the rail mock's current_id 0 never triggered
    the restore, the hero open drove the retired filechooser flow, the
    document fixture predated document_id/revision (PR #1047; 12/12 + 12/12
    green on review, differential run isolated the damage to exactly the
    restore-path tests).
- Resource close-out: tracked evidence refreshed by local reruns restored,
  this batch's untracked outputs removed, no stray playwright/chromium
  processes, disk 1.1 Ti free.

## Matrix write-back batch (main = 06b46f6e3)

- 17 language/width variants flipped to pass, each on a parameterized suite
  green on review this batch: card-actions 9 (product-add hover/retry/unverified
  x en:390/de:1440/de:390), failure-ownership 5 (service-error-retry 3,
  ordinary-draft-owner-isolation 2 - its de:1440 was already pass),
  parts-card 3. genie-parts' csv de:1440 strict-mode ambiguity fixed in the
  same commit (sentence stands in three places; anchored on the attachment
  status), suite 8/8 after the fix.
- Correction of that commit's message: it says 20 variants; the honest count
  is 17 (the linked-product variants are home-family rows covered by
  genie-hero, which was not run green this batch and stays pending).
- Not flipped without real coverage: the 90 planner-chain variants (single
  shape EN chains) and every other family whose suite has not run green in
  the row's shape. Pending after this batch: 310.

## Batch: shape coverage to every language and width (main after PR #1050)

- Four suites extended from their single EN/1440 row-shape to full en/de x
  1440/390, all verified green on review before merge: home-hero-retry and
  genie-history-authority (PR #1048, 24 tests), genie-hero's answer and
  linked-product tests (PR #1049, 4/4 - with the spec catching up to the
  shipped hero: planner-entry capsule excluded from the hide assertion,
  three-tier card grid, layout poll), genie-cross-surface-entry (PR #1050,
  all four shapes - phone shapes open the dock through the chip).
- Matrix: pass 142 -> 145, pending 295. Honest exclusions recorded: the 90
  planner-chain variants (single-shape EN chains, not flipped without real
  coverage), save-readback DE (its cart notice is an untranslated catalog
  string; customer-visible copy goes through the copy review line, not a
  freelance translation - the gap is this note), account-family variants
  (sibling evidence is production JSON audits of one shape).
- Operational lesson recorded: a tool-level background timeout does not kill
  the process tree - a zombie full genie-hero run starved the review Genie
  and produced a batch of 400s test timeouts; killed, diagnosed by service
  log (turns 200 OK but minutes-slow), and the shapes re-verified green on
  the quiet instance.

## Batch: project-brief in German (PR #1051)

- planner-brief-chain parameterized over en/de (13 tests, all green on
  review 51.7s); every German word from the shipped catalog, no new copy.
  Root-caused on the way: the direct-goto sites built the DE configurator
  URL without its /de prefix (a 404 - the single cause of the three first
  DE failures), then a doubled slash in the staged-URL regex.
- Matrix: pass 145 -> 181 (all 36 project-brief language/width variants),
  pending 259.
- Remaining planner variants: map-chain 33 and report-chain 39 need the
  same treatment (bigger label surface: 21 and 37 strings) - next batches.

## Batch: the roof map chain in German (PR #1052)

- planner-map-chain parameterized over en/de (8 tests green on review).
  Three root causes root-caused by EN/DE diff probes before fixing: German
  number fields take a decimal comma (dot decimals left lat/lng invalid and
  the workspace-switch guard blocked the whole chain), two German
  substring/label collisions, and a hydration wait before the first section
  navigation.
- Matrix: pass 181 -> 214 (all 33 roof language/width variants), pending 226.
- Remaining planner variant block: report-chain 39 rows (37-label surface -
  the biggest of the three), same method.

## Batch: the full planner chain in German (PR #1053)

- planner-report-chain parameterized over en/de: the complete customer
  chain (site -> roof -> strings -> profiles -> PVGIS -> PV -> equipment ->
  scenario -> report -> transfer -> Woo draft) drives the German configurator
  end to end; en and de both 5.2m green on review. Nine root causes fixed on
  the way, each verified against the live German DOM (the duplicated
  hardcoded fill that waits forever, four option labels, three English-only
  assertions, the Betrieb/Speicher substring collisions, the hidden-tab
  report select copy, the MPPT sprintf self-collision, the English-only
  confirmation segment). This closes the planner trilogy: brief-chain (#1051),
  map-chain (#1052), report-chain (#1053) all bilingual.
- Matrix: pass 214 -> 241, pending 199. The planner-variant block that was
  90 rows at the start of the day is fully retired where the chains cover it.
- Operational note recorded: the shared public-connection limiter must be
  reset between chain runs (3/hour shared across runs) - already a handover
  discipline, now hit in practice.

## Batch: authentication flows in every shape (PR #1054)

- account.spec.ts: the rejected sign-in parameterized over en/de x 1440/390
  (4/4 green, 40.8s); the signed-out notice verified on the German account
  at both widths and the English phone shape inside the partner journey
  (14.5s). Matrix: pass 241 -> 247, pending 193.
- Honesty note: four historical authentication de:1440 rows
  (invalid-sign-in, pending-submit, registration-success,
  password-email-confirmation) sit at pass with EMPTY evidence from an
  earlier session's bulk flip - an earlier attempt to backfill them with
  run-family evidence was rejected as unverifiable and reverted; the rows
  stay flagged here for dedicated re-verification instead.

## Batch: the reset chain at every width (PR #1055)

- account.spec.ts: both reset tests (lost-password through the new-password
  card; wrong-or-spent key refusal) gained the 1440/390 width loop over
  their en/de loop - 8/8 green on review. Matrix: pass 247 -> 251,
  pending 189 (reset-password and password-reset-token-states phone shapes).

## Batch: the account save at every width (PR #1056)

- The account-details save test gained the 1440/390 width loop over en/de
  (4/4 green, 18.2s). Matrix: pass 251 -> 253, pending 187.
- Remaining spec-backed pending: genie save-pending-error-success and the
  consumer-saved-solution-readback de/390 shapes (need the same width/locale
  extension on the genie side).

## Batch: the saved-solution consumer chain in every shape (PR #1057)

- genie-save-readback parameterized over en/de x 1440/390 (all four green);
  two real findings fixed on the way: the German notice's actual wording
  ('liegen jetzt in', the PO's empty msgid had the string under another
  key) and the save action arriving at the stream's very end (askGenie now
  waits for the button - the sequential-run 400s timeouts' root cause).
- genie save-pending-error-success 3 variants flipped on the already-green
  card-actions suite (locale x width x surface).
- Matrix: pass 253 -> 259, pending 181.

## Batch: the public doors at every shape (PR #1058)

- The four parameterized public-door suites swept green on review
  (public-inquiry 32/32 including the counter-reset rerun, inquiry-entry,
  inquiry-draft-actions, contact-selection-continuity). Root cause on the way:
  the shared per-instance public-door counters exhaust mid-sweep - the contact
  door then refuses its own verification dispatch; the suite now resets them
  beforeEach (the genie-hero freshCounters discipline).
- Matrix: pass 259 -> 278, pending 162.

## Batch: products contract sync (PR #1059)

- products.spec.ts guest test now asserts the draft button IS offered (the
  #246 inquiry-open-to-all contract, the page's own docblock); the comparison
  chip test signs in first (a guest's pill is a deliberate two-column grid
  via :has(.linker-create-account)). 4/4 green.
- Root-caused and recorded honestly (not papered over):
  1. review's WindPress cache was a month stale - `just windpress-compile
     review` rebuilt it through the admin (the delivery discipline's cache
     rebuild, hit in practice on the review instance);
  2. the library FAQ spec expects >200 product answers; review's data yields
     174 (EN products fully passing the publish gates; the census's 79
     "failures" were German twins misc counted, 6 real binding failures) - a
     review-data currency gap vs production, threshold NOT lowered, related
     rows NOT flipped;
  3. draft-visual-states' staff-session fixture (global snapshot/restore)
     races with parallel suites - flaky only under multi-file parallel runs,
     4/4 green in isolation; needs serialization or a per-test fixture.

## Batch: quick start field rhythm + choice labels reality (PR #1060, merged)

- The rewritten "choice labels" test exposed a real visual defect, not a
  measurement artifact: `.lp-quickstart-form` had ZERO rules in the WindPress
  planner volume (the global `.lp-field` sets margin 0 and every other planner
  form adds its own rhythm), so quick start rows rendered flush - the next
  field's label sat pixel-exact on the previous select's bottom (DOM probe:
  prev.bottom == own.top == 819.78, margin/padding 0).
- Fix: same 16px sibling rule as `.lp-new-project`; deployed via
  `just present review` + `just windpress-compile review` (cache mtime
  1794302771 -> 1794304842, anchor classes present).
- Test now targets the one-screen quick start reality (native select, >1
  option, >=8px row breathing, native selectOption response). choice labels
  4/4 green, full visual-details suite 28/28 green. PR #1060 CI green, merged.

## Batch: matrix flips + pending-account fixes + genie determinism (PR pending)

- 44 matrix rows flipped to pass (278 -> 322 cumulative; pending 162 -> 118):
  draft x12 (inquiry-draft-actions 8/8 + draft-visual-states 8/8 on review,
  assertion scope verified per state), price gates + account overview x13
  (pending-account en/de x 390 green on c222 after two test defects fixed:
  hardcoded /mein-konto/ waitForURL that always failed EN, and the custom
  browser context never receiving the consent seed so the CookieYes overlay
  blocked every 390 interaction), genie x19 (reply-presentation 10/10,
  card-actions 12/12, attachments 4/4, consumer-draft-readback via merged
  #1057 run - all assertion-mapped before flipping).
- pending-account restricted phase now also asserts the product-page price
  gate ("Not available for your account" / "Für Ihr Konto nicht verfügbar",
  no price amount) - the restricted-price-gate rows flipped on this.
- Genie inquiry-assessment determinism channel (services/genie app.py +
  tools/local env): LINKER_GENIE_ASSESS_DETERMINISTIC=1 on local serves the
  verdict through the same parser with a synthetic Jev answer. Root cause:
  every local inquiry-notification send spent a REAL OpenRouter Jev call
  inside the shell's 10 s window (Queue::WAIT_SECONDS); the window was
  missed on review all afternoon (genie log: repeated undetermined
  "deadline"). Production is untouched (env never set there). Genie pytest
  20/20; verdict->handoff->mail chain proven delivering.
- failure-injection 390 extension: 13/16 in the full run; de 1440 add
  passed isolated. de 390 inquiry/contact remain RED and are NOT flipped,
  NOT shipped: review's mail pipeline state is polluted (jobs created and
  authorized, attempt actions scheduled +8 h ahead, nothing due; throttle/
  ledger options already deleted without restoring delivery). This is an
  instance-state pollution loop, documented as an E-line finding: failed/
  orphaned mail jobs have no lifecycle recovery and their retry loop
  self-sustains throttle saturation. Next batch: reset review from
  snapshot, then land the fi spec changes (already written: ledger+throttle
  reset beforeEach, subject-scoped mail assertions via persistent
  linker-mail log, cron+AS runner in the poll).
- genie-hero long run on c222 in flight at batch close (regression
  coverage; no rows depend on it this batch).

## Follow-up: clean-review failure-injection run + hero finding (post #1061)

- PR #1061 merged after the ruff import-order fix (the only real CI error;
  the scope-gate failure was its downstream echo).
- review was reset from the production snapshot (2026-11-05) and rebuilt
  (present + windpress-compile). The full failure-injection run on the clean
  instance: 9/16, 7 failures - ALL at the seam's real verification round-trip
  ("Verification could not be completed"), spread across languages and
  widths: the dummy Turnstile secret still calls Cloudflare siteverify over
  the network, and the machine's network is flaky today (GitHub API TLS
  timeouts observed in parallel). The mail chain itself was proven healthy
  on the clean instance (same-second delivery, subject-scoped assertions
  passing).
- Next bounded slice for the fi landing: an env-gated local short-circuit of
  the siteverify round-trip under the dummy profile (same philosophy as the
  deterministic assessment channel; production never sets it), then the
  16/16 run and the spec PR. The spec changes stay in the working tree.
- genie-hero on c222: 20/28, all 8 failures share ONE assertion - the
  draft-added confirmation text ("In your solution draft." / "Im
  Lösungsentwurf.") never appears after the hero card send, EN and DE alike.
  Same copy family as the known empty-PO save-readback notice but wider
  (English fails too), so NOT just a missing translation. Own diagnosis
  line; no rows flipped (home-hero:en:390 stays pending).

## Batch: failure-injection 390 landing (local-verify constant + mail reset)

- Turnstile.php gained an env-gated local verdict: LINKER_TURNSTILE_LOCAL_VERIFY
  (set only by the e2e dummy profile alongside the official always-pass test
  keys; production never defines it) answers valid without the siteverify
  round-trip. PHPStan clean; verification integration tests 17/17.
- The suite's beforeEach now resets the whole mail subsystem per test
  (protection ledger, throttle, mail jobs, send-authorization options,
  budget ledgers, and the three Action Scheduler hooks) - the retry loops
  can no longer re-accumulate across 16 serial tests.
- Final configuration runs FULL 16-test suite in ~7 minutes (was 12-19
  minutes of scheduler/throttle stalls). Two full runs A and B: 15/16 each;
  each run's single failure is the Cloudflare widget CDN script fetch on
  this machine's flaky network, and each failed test passed in the other
  run - union covers all 16. Two widget-interception approaches (hand
  stub, cached real script) were tried and REVERTED: both made things
  worse (the widget has secondary CDN dependencies; intercepting api.js
  breaks the challenge and slows send tests). The CDN fetch stays the
  suite's one external dependency; a real offline widget mode would be a
  product decision with no precedent, not patched around here.
- 4 rows flipped (draft:update-failure en/de 390, product:
  add-pending-success-error en/de 390) on the A+B union evidence.

## Correction: the save-readback DE notice "external condition" was a misdiagnosis

The ledger previously held "save-readback German notification PO msgstr is
empty" as an external copy item. Checked directly: the PO has the German
sentence (multi-line msgstr), the compiled MO has it too, and the
genie-save-readback suite (4/4 green, #1057) asserts exactly this German
sentence ('Die Produkte der gespeicherten Lösung liegen jetzt in Ihrem
Lösungsentwurf.') and passes. The item came from misreading PO multi-line
format. Closed as invalid - the only remaining external condition is the
PDF content read (image model).

## Batch: hero add-to-draft proof wiring (PR #1064, merged; #1063 also merged)

- The hero card's ADD path never sent its signed draft proof (the SAVE path
  did): GenieCard.onAdd invoked (productId) alone, addToDraft ran with the
  empty default token and the server correctly 409'd every hero add. The
  one-line wiring fix landed with the full evidence chain in the PR
  (server minting healthy, proofs present in the browser-received body,
  loss was the last hop).
- After #1063 merged (lifecycle assertions), #1064 went green without
  touching any mail code - the mu-smoke mystery was exactly the two
  count-sensitive InternalSmtpTest expectations awaiting the lifecycle
  alignment, not an environment flake and not a main regression (my
  earlier "main fails locally" evidence was contaminated by the agent's
  uncommitted edits in the shared tree - lesson recorded below).
- genie-hero full suite on c222 after the fix: 22/28. The four cards-send
  tests (the original proof failures) all pass now. The remaining 6 are a
  DIFFERENT pair: "out of sight, the way back continues the same
  conversation in the dock" times out at 600 s in all four shapes, and
  "#236 attachment states render in the hero" never shows
  .linker-genie-attachment at 390. Own diagnosis lines; home-hero matrix
  rows stay pending.
- Parallel-agents lesson (hard-learned, now standing practice): subagents
  share the parent's working tree. An agent's staged-but-uncommitted work
  was swept into one of my commits (caught pre-push, reset), and its
  unstaged fix was overwritten twice by branch checkouts (recovered from a
  backup worktree). Standing rule from here: every parallel agent works in
  its own git worktree and commits by explicit pathspec.
- Misdiagnosis closed: the save-readback DE notice "empty PO" external
  item was PO multi-line misreading; the MO has the sentence and the
  4/4-green suite asserts it. Only PDF-content-read remains external.

## Batch: engine 503 healed end-to-end + the PDF content read (real verdict)

- The engine's /design 503 had two stacked local causes: (1) the snapshot's
  EvidenceBindings for exactly the 3 reference products were stale (the
  figures themselves are current and byte-consistent with production; the
  security design never renews a recorded binding), healed by deleting the
  stale bindings and re-adopting - figures_for(8349) 0 -> 30/30; (2) the
  engine reads a feed.json snapshot that needed a rebuild after the heal
  (plus one cold-start race in `serve`: fetch the feed only after WP
  answers, not during warm-up). Design 200, report PDF generated.
- The last cu-pass-pending row (report PDF content + revision) is now READ:
  a DeepSeek Flash image read transcribed the full page. Honest verdict -
  the row does NOT pass: the report PDF genuinely lacks self-sufficiency %,
  self-consumption %, the BOM/Stueckliste, any revision identifier and the
  logo. These are contract-required elements (AGENTS.md §1 tool contract);
  this is a real #548 report-content defect, not an image-model condition.
  Row moved to pending with findings; the external-condition framing is
  gone. No external conditions remain on the matrix.
- Also landed this session: PR #1066 (product-archive 14 rows, personally
  re-run 14/14) and PR #1067 (account 28/28 personally re-run, two real
  defects fixed: auth.css 390px list overflow, AdminAccessNotice AJAX
  overwriting the real verdict) - account family now zero pending.

## Session closeout: matrix 278 -> 424 pass (pending 162 -> 5)

Batch tally this continuation: PRs #1060-#1072 merged (13 today by this line, 31 overall
with the morning session): quick-start field rhythm, pending-account 390 fixes, genie
assessment determinism, mail-job lifecycle (E-line real fix, slot +21.43h -> 0s), hero
proof wiring + identity-race fix (28/28), v2 draft-proof tokens (170KB -> 667B), DE filter
param contract, report content (self-sufficiency/self-consumption/BOM/revision/wordmark,
personally read back on the final PDF), account-states suite (account family zero pending,
two real defects fixed en route), product-archive rows, inquiry 390 states, copy-and-rating
production probes (3 live turns + real votes, 3 rows), research deliverable (13 vendor
originals; SGS premise corrected, BAT-C/ET verdicts, terminal map closed).

Final pending 5, each honest and non-force-fit:
- files-and-feedback actual-file-manifest-open-and-content x3: the sibling evidence
  requires /faq-download/ to render 143 PDF links; the review snapshot yields a different
  manifest count (known review-vs-production data currency gap, same class as the FAQ
  threshold finding). Needs a current production snapshot or production-side probe.
- genie dock-keyboard 390 x2: the floating dock is hidden below 860px by design; the 390
  surface is the hero. The dock-specific keyboard contract needs the side-panel
  continuation path - recorded as a finding on both rows, left pending.

Standing rules landed this session: parallelism as a top principle + agent worktree
isolation (AGENTS.md), the node_modules symlink lesson, subagent-output personal
verification discipline.

## Final two rows: probed honestly, left pending with evidence

- files-and-feedback actual-file-manifest x3: FLIPPED. Production read-only probes
  (143 unique PDF links + the same 4 sample files as the 20261108 sibling, all
  200 application/pdf with matching bytes) - probe JSON recorded at
  docs/acceptance/2026-10-22/full-site/product-manifest-probe-20261111.json.
- genie dock-keyboard 390 x2: five probe attempts across the hero surface, side-panel
  continuation and composer focus paths; the floating dock's keyboard contract cannot
  be exercised at 390 because the dock is hidden below 860px by design, and the hero's
  Escape behavior differs (close button, not the dock's escape-return). Rows stay
  pending with the hidden-below-860px finding recorded - force-fitting the hero onto a
  dock-specific contract would be a false pass.

Matrix final state this session: pass 424 / verified-production 448 total / pending 2
(both with findings and unlock paths).

## Real-person zero-blocking production proof (completion criterion item 1)

- Two real guest inquiries submitted on production through the complete real chain
  (headed real Chrome + CDP, Turnstile challenge -> PublicGuard -> submit -> receipt),
  EN and DE, 1440. Both reached the inquiry-received receipt with ZERO page errors and
  zero blocking (2 passed, 24.8 s; HUMANPASS en/de logged).
- Read back on production: orders #8703 (en) and #8704 (de), billing emails matching the
  probe identities, both status=inquiry-received.
- Test-mail discipline: the recipient-rewrite switch (linker_commerce_test_mail_to ->
  chester@de-linker.com) was enabled before the probes and deleted after, read back as
  absent. Outbox jobs are transient on production (delivered posts deleted by design),
  so routing evidence is the switch state + the received orders.
- Two earlier "failures" were probe artifacts, honestly recorded: a hidden-element
  textContent misread (the draft-pending notice), and the legitimate business validation
  "Bitte fuegen Sie ein Produkt hinzu oder schreiben Sie eine Nachricht" (a message is
  required when the draft has no products) - not product defects.

## Post-merge report read-back (PR #1073, merged) + overlay healed

- PR #1073 archived the post-merge EN/DE report read-back (full transcription,
  both PDFs + readback.json in docs/acceptance/2026-11-11/report-final-readback/).
  Honest open item preserved: the report's "no bill of materials" statement is
  correct on this data - every design is no_candidate.
- The review engine feed overlay is healed to 3/3 (Trina pv_module + both nexans
  cables; stale _linker_cable_facts source revisions updated by the fix agent,
  independently re-verified by main: feed.json overlay = [pv_module, cable, cable]).
- Second-layer gap measured by main: 85/85 feed products lack the layout datasheet
  fields strings.py requires (n_mppt, mppt_voltage_range_v, max_pv_input_v, ...) -
  a systematic #548 data-projection gap that keeps every input no_candidate.
  Recorded as the open engineering-data line, not papered over.

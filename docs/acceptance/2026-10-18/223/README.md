# #223 · Account entries and Genie presentation

Work remains in **#223 / PR #312**. Instance **c223**, <http://127.0.0.1:9126>,
worktree `/Users/chesterjohn/Documents/de-linker-worktrees/c223`, branch
`feat/223-create-account-links`. Snapshot `20261018-2057`; [isolation](instance.json).
No merge or deployment. No production code/configuration/account/order/inquiry
writes. The explicitly requested live filled-draft comparison used only a
disposable anonymous Woo add/remove session, emptied in finally; no inquiry,
order or real email was sent. Test mail stays in local files.

All guest sign-in surfaces have a separate **Create account / Konto erstellen**
entry to the existing native language endpoint, respecting Woo registration and
visitor state. LC owns composition, WindPress owns styling, PHP supplies data.
The owner’s later Genie work is included here: dynamic simulated waiting,
local reveal of complete answers, safe Markdown, explicit immediate reply
options, separate reader/composer rows and a quiet support footer. Real reopening
also exposed and repaired WordPress meta unslashing of SSE JSON. The owner then
approved only the EN/DE prompt **formatting contract**, preserving existing
model, factual/short/exact-answer rules, tools, API, transport and permissions.

## Completion criteria

| Criterion | Status | Evidence |
|---|---|---|
| Find every guest sign-in surface before implementation | 完成 | [Census and consumers](surfaces.md) |
| Header dropdown, mobile menu and footer panel in EN/DE | 完成 | [Browser output/click tests](checks/entries-final.log), [full raw pixels](pixel-results.md) |
| Product list/category/PDP/comparison price gates and model switching | 完成 | [Account tests](checks/entries-final.log), [comparison repair](mobile-comparison.md) |
| Empty and filled solution draft, public inquiry | 完成 | [Tests](checks/entries-final.log), [exact live filled-draft pairs](pixel-results.md) |
| Password reset/confirmation, private document403 | 完成 | [Census](surfaces.md), [account tests](checks/entries-final.log), [raw captures](pixel-results.md) |
| Guest/approved/pending/registration-disabled conditions, escaping | 完成 | [TDD](tdd.md), [output tests](checks/output-tests.log), [browser states](checks/entries-final.log) |
| New account cannot read another account’s document or inquiry | 完成 | Real ownership fixture in both full account runs; [test log](checks/entries-final.log) |
| Genie dock/workspace guest links precede React mount, no order reversal | 完成 | [Source/entry coverage](genie-expansion.md), [browser tests](checks/entries-final.log) |
| Inquiry Create account stays on its own line, clear space above draft card; absent from emails | 完成 | [Rejected before and normal-flow after](change-ledger.md), [32px screenshots](computer-use/), [route/mail output tests](checks/output-tests.log) |
| Reply final prose/control rows fully reachable, composer does not cover text | 完成 | [Repeated browser test](checks/reply-browser-final.log), [waiting/reading/latest images and videos](replies/) |
| Jump control outside prose and focus ring only on focus-visible | 完成 | [Browser bounds/focus assertions](checks/reply-browser-final.log), [before/after](change-ledger.md) |
| Actual EN/DE answers use headings/lists/emphasis; reopened text identical | 完成 | [Real model test](checks/real-format-final.log), [raw received streams and dock/workspace matrix](replies-real/) |
| Quick replies recognisable as immediate send choices | 完成 | [Copy review](copy-review.md), [real Computer Use](computer-use/en-genie-format-dock-latest-390.png), [click payload tests](checks/reply-browser-final.log) |
| Dynamic waiting/loading/local reveal, reduced motion, history no replay | 完成 | [Repeated tests](checks/reply-browser-final.log), [motion videos](replies/) |
| EN/DE ×1440/390 screenshots of every scoped surface/state | 完成 | [Census](surfaces.md), [full raw pairs](pixel-results.md), [real replies](replies-real/), [Computer Use](computer-use/) |
| Header95 widths in Chromium/WebKit/Firefox, exact inherited exception | 完成 | [24 tests and95×3 matrix](sweep-summary.md); Chromium/WebKit empty sets, Firefox1283–1287 EN expanded/DE folded |
| Narrow declarations: mobile utility row and comparison price cells only | 完成 | [Scenario declarations](review2-scenarios.json), measured bounds in capture manifests; no whole mobile panel or comparison shell |
| Every other pixel against live equals0, dimensions exact | 完成 | **[56/56 PASS](pixel-results.md)**, full RGB counts/raw images; no tolerance/cropping/padding |
| Filled-draft live counterpart and repeatability | 完成 | All four cases in [final full capture](pixel-results.md); separate4-case repeated capture also zero outside |
| Preserve historical10 DE header differences attributed to #229 | 完成 | [Historical results](pixel-results-before-review2.md) retained; fresh snapshot result does not overwrite them |
| Link/control copy: EN draft, adversarial review, independent DE final | 完成 | [Copy record](copy-review.md) |
| Ruled changes before/after and obsolete split-login exclusion corrected | 完成 | [Ledger](change-ledger.md), [spec](../../../specs/split-login-register.md) |
| Full Spec + Standards reviews and old-code absence | 完成 | [Separate review conclusions](review.md), [added-line scan](checks/legacy-added-lines.log) |
| Main #236 attachments, #250 inquiry cards, #322 asset version retained | 完成 | [Review](review.md), build and browser regressions |
| Official WindPress compilation and served readback | 完成 | [Compile](checks/windpress-final.log), [readback](checks/present-final.log) |
| Rebase on latest fetched origin/main and just check/just test | 完成 | Base18d3029b; CI on PR312’s final head is the gate. The linked [just check](checks/just-check-final.log) and [just test](checks/just-test-final.log) logs are from the pre-rebase source and are retained as history. |
| Inline conversation inside homepage/other hero | **Delegated to #232** | Hero entries currently open the shared full workspace and use its reply design. Inline transcript wiring is not delivered here; the owner ruled on 2026-10-18 that it belongs to the open ticket #232. #223 does not claim it. |

The design follows the supplied direction and [official source research](../../../research/2026-10-18-genie-reply-design/REFERENCES.md).
It is not a measured replica of authenticated OpenAI reply pixels. Deterministic
fixtures prove layout/motion/click behavior; `replies-real/` separately proves
actual generated formatting. Neither claim substitutes for the other.

## Review the current result

- Rejected inquiry gap → normal flow: [ledger](change-ledger.md),
  [EN390](computer-use/en-inquiry-gap-fixed-390.png),
  [DE390](computer-use/de-inquiry-gap-fixed-390.png).
- Real structured answer: [EN workspace1440](replies-real/en-1440-workspace.png),
  [DE workspace390](replies-real/de-390-workspace.png).
- Clear reply options: [EN dock390](computer-use/en-genie-format-dock-latest-390.png),
  [DE workspace390](replies-real/de-390-workspace-latest.png).
- Exact pixels: [all56 cases](pixel-results.md),
  [desktop manifest](pixels-final-desktop/capture.json),
  [mobile manifest](pixels-final-mobile/capture.json).

The original requested `docs/agents/codex-queue.md` was absent; no claim is made
that it was read. Earlier screenshots/failed results are historical evidence.
The latest manifests and per-case full raw pairs determine the current pixel gate.

## Local rollback

Do not deploy as part of this session. To inspect rollback locally, preserve the
worktree diff, switch c223 to the review base in a dedicated local checkout, run
`just present c223`, compile with `just windpress-compile c223`, and read back with
`just present c223`. The presentation command stores its prior template option
for local restoration. No DB schema or registered endpoint was introduced; the
Thread fix only preserves bytes on future writes. It does not migrate histories.

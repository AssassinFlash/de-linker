# #223 · Guest account entries and owner-requested Genie presentation

Instance: **c223**, <http://127.0.0.1:9126>. Worktree:
`/Users/chesterjohn/Documents/de-linker-worktrees/c223`, branch
`feat/223-create-account-links`. Snapshot and mail isolation: [instance.json](instance.json).
No deployment, merge, production write or real test email was performed.

Guest sign-in surfaces now offer the existing native registration endpoint in
English and German. PHP supplies data/semantic fragments, LC owns composition,
and WindPress owns new styles. Logged-in state, Woo registration availability,
account approval, public inquiry and document permissions retain their contracts.

The owner additionally requested comparison-page visual repair and Genie visual
refinement. Genie uses a shared front-end reply renderer for dock and workspace:
dynamic simulated thinking/loading, safe Markdown, local progressive reveal of
an already complete answer, copy/feedback, reduced motion, quiet footer and
reader-controlled scrolling. The backend request, model, answer, tools,
transport, permissions and thread storage remain unchanged. See
[frontend boundary and entry coverage](genie-expansion.md).

## Completion criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| Establish every guest sign-in surface before implementation | 完成 | [Census and source consumers](surfaces.md) |
| Desktop account dropdown and expanded mobile menu, EN/DE | 完成 | [Account browser tests](checks/entries-final.log), [screenshots](computer-use/) |
| Footer account panel, EN/DE, independent links/count | 完成 | [Census](surfaces.md), [ledger](change-ledger.md), [pixels](pixel-results.md) |
| Product list/category/PDP/comparison, including model switching | 完成 | [Account tests](checks/entries-final.log), [product captures](pixels-products/), [comparison repair](mobile-comparison.md) |
| Empty/filled solution draft and public inquiry | 完成 | [Account tests](checks/entries-final.log), [filled draft](filled-draft/), [LC source inventory](surfaces.md) |
| Password recovery, confirmation and private-document 403 | 完成 | [Account tests](checks/entries-final.log), [captures](pixels/); original 403 and ownership checks retained |
| Guest/approved/pending/registration-disabled behavior and escaping | 完成 | [TDD record](tdd.md), [public-output tests](checks/output-tests.log), [account browser tests](checks/entries-final.log) |
| A new account cannot read another account's document or inquiry | 完成 | [Ownership fixture](checks/ownership.log), also included in both final full account runs |
| Genie dock/workspace account entries and front-end visual expansion | 完成 | [Reply tests](checks/reply-browser-final.log), [screens and motion videos](replies/), [real browser inspection](computer-use/) |
| EN/DE ×1440/390 images of every scoped surface | 完成 | [State census](surfaces.md), [Computer Use images](computer-use/), [pixel captures](pixel-results.md), [filled draft](filled-draft/), [reply states](replies/) |
| Header 95-width boundary sweep in Chromium/WebKit/Firefox | 完成 | [Summary](sweep-summary.md), [raw matrix](checks/header-matrix.log): Chromium/WebKit both mismatch sets empty; Firefox exactly 1283–1287, EN expanded/DE folded |
| New link and new Genie controls have independent EN/DE copy review | 完成 | [Draft, adversarial feedback and final copy](copy-review.md) |
| Ruled changes have before/after evidence | 完成 | [Change ledger](change-ledger.md), [before captures](before/), [before product captures](before-products/) |
| Every other pixel against live equals zero | **未完成** | [Exact results](pixel-results.md): 34/52 cases outside ruled regions =0; 10 DE desktop cases retain main/live header drift; 8 dimension mismatches stay FAIL |
| Filled-draft live pixel parity | **未完成** | Local real fixtures/screens completed; no live cart/session mutation was used for production parity |
| Exact current authenticated OpenAI reply pixel match | **未完成** | [Primary-source research](../../../research/2026-10-18-genie-reply-design/REFERENCES.md): actual logged-in reply captures unavailable; official component contracts and verified shells inform local design |
| Inline hero conversation design | **未完成（独立接线事项）** | Current home/solution hero links enter the shared workspace. [Genie · hero 接线实现](https://github.com/AssassinFlash/de-linker/issues/232) remains open; this ticket does not claim an inline hero exists |
| Full Spec + Standards source review and legacy absence | 完成 | [Review record](review.md), [new legacy identifier scan](checks/legacy-added-lines.log) |
| Official WindPress compile and served cache readback | 完成 | [Compile](checks/windpress-final.log), [presentation readback](checks/present-final.log) |
| Rebase, `just check`, `just test` | 完成（最终命令日志） | [Final local check](checks/just-check-final.log), [final local tests](checks/just-test-final.log); PR records final base/head and CI |

The strict pixel gate remains failed. No color tolerance, image cropping,
padding, resized canvas or broad header exception was introduced to make it pass.
Page dimensions stay an independent failure condition. Tool redraw regions are
explicit owner-authorized changes, not dynamic masks.

## Review the visual changes

- Comparison before/after: [ledger](change-ledger.md), [mobile comparison](mobile-comparison.md).
- Real DE response before typography: [14px single paragraph](computer-use/de-genie-real-answer-before-typography-390.png).
- Real DE response after typography: [16px/26px, three reading paragraphs](computer-use/de-genie-real-answer-after-typography-390.png).
- Full-page workspace: [1440](computer-use/de-genie-real-workspace-1440.png), [390](computer-use/de-genie-real-workspace-390.png).
- Deterministic EN/DE waiting/completed replies and dynamic videos: [replies](replies/).
  These fixtures intercept the existing JSON response in the browser; they do
  not replace the service or constitute a model-answer quality test.

The source base was rebased from `0fddf100` to `c2106969` (opcode-cache reset
only; no header/UI changes). Header measurements were taken after the account
header change; later Genie-only styling and this rebase leave the measured
header source unchanged. The original requested `docs/agents/codex-queue.md`
was absent; its absence is recorded, not represented as having been read.

## Repeat locally

```sh
just up c223
just serve c223
just check
just test
LINKER_E2E_INSTANCE=c223 LINKER_E2E_SKIP_SERVICES=1 \
  npx --prefix tests/e2e playwright test --config tests/e2e/playwright.config.ts \
  account-entries.spec.ts --project chromium --repeat-each=2
LINKER_E2E_INSTANCE=c223 LINKER_E2E_SKIP_SERVICES=1 \
  npx --prefix tests/e2e playwright test --config tests/e2e/playwright.config.ts \
  genie-reply-presentation.spec.ts --project chromium --repeat-each=2
```

Run stateful account fixtures before captures; do not overlap instance option
fixtures with visual capture. Mail stays in the c223 local file spool. Temporary
users, options and business records are restored by each fixture.

Rollback locally: revert the ticket commits on this branch, rebuild tools,
reinstall presentation into c223 and run official WindPress compilation. The
presentation installer retains its prior option backup. Do not apply these
commands to production. The PR uses `Refs #223`, not an auto-close directive.

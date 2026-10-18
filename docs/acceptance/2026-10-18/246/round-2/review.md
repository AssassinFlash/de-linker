# #246 round 2 — Standards and Spec

The code-review skill ran independent read-only agents. Full branch comparison: `git diff 0a239ae2faaca907c05559953ef4c2df69bffb4e...e5d4f17b` (merge base `71d950db`). The full comparison included all #246 commits, preserving the accepted round-1 decisions. After the final rebase, both agents reviewed the new mail/mobile delta `6e001f13..f5d639b8` and the ProductView resolution against main `0a239ae2`.

## Standards

**PASS: 0 hard violations; 0 actionable baseline smells.**

Sources: `AGENTS.md`, `docs/agents/genie-kickoff.md` 通用规则, `tools/php/phpcs.xml`, `docs/specs/11-commerce.md`. The atomic limiter lives in commerce, with no dependency on tools. The ten-receipt allocation and fixed UTC-day window are sourced. PHP supplies escaped data; the receipt disclosure's composition is in LC and its empty-state behavior is in WindPress. The sender label is assembled once and reused by subject/template. EN and independently authored German copy are reviewed.

The added-line retired-identifier check found only neutral audit documentation; no introduced `tv_b2b_`, `Linker_AI_` or `dlk-` implementation identifiers. Tooling-enforced issues were left to WPCS/PHPStan.

## Spec

The full review found one defect: optional-name `Submission::from_handoff()` reached templates rendering `Hello ,` / `Guten Tag ,`, an empty team subject label and empty parentheses. This was fixed in the same ticket. Corrected real Sender/Outbox tests fail before the template change and pass afterwards in both languages; see `nameless-copy-red.txt` / `nameless-copy-green.txt`. The real reply email is the final team identity fallback; no name is invented.

**Targeted final verdict: original finding resolved; 0 new findings.**

The shared connection allowance reserves atomically before Sender. The site-wide cap suppresses only the receipt trigger: record and team notification remain. Fresh-cookie browser tests exercise both public doors across a Woo-cookie transition; successful submission supports retaining the nonce signature under the user's conditional HMAC instruction. Claude's accepted pixel measurements and method are accurately recorded.

Visual inspection then found the receipt disclosure was hidden by the existing mobile `.linker-next-steps` rule. `mobile-notice-red.txt` reproduces the hidden text. The LC success panel now carries the disclosure, and browser assertions require visibility. The ordinary reply paragraph is unchanged; `empty:hidden` removes the empty disclosure for ordinary receipts. Both agents confirmed this narrow correction follows the spec and presentation boundary.

The rebase keeps #242's `ProductView::price_html()`, `CommerceState::reason()` and `Approval::PENDING` handling unchanged. The price sign-in URL is the same native expression, inlined after the obsolete CTA helper was removed. Public add-to-draft behavior remains #246's intended change.

## Real-fixture adjustments

The post-sync full run exposed three fixture assumptions (`integration-before-fixture-fixes.txt`). Digest extensions may append a translation-exception block, so the assertion now checks the existing five-block prefix. SMTP diagnostic tests now render through the existing `LocaleSwitch` used by the real mail/digest flow; raw WordPress switching after a prior commerce-domain reload did not load the German plugin messages. No SMTP production behavior or settings changed. Both complete integration runs then pass with 117 tests, 1,232 assertions and nine existing HTTP-fixture skips. Every new public-submission test executes.

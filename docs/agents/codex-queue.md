# Codex queue · non-Genie tickets (map #220)

You run these in the Codex app (owner, 2026-10-18). Claude writes the prompts, reviews every PR, merges, deploys and verifies on live. Genie tickets stay with Claude's sub-agents.

## How to run one

1. **Open the folder.** In the Codex app, start a **new thread** with the ticket's worktree folder (listed under each ticket). If the folder doesn't exist yet, tell Claude "#N unlock" and Claude creates it.
2. **Settings:** model gpt-6.1-sol, effort xhigh, full access (the prompts forbid deploys, merges and production writes on their own).
3. **Paste** the prompt block under the ticket, everything between the ``` lines.
4. **When Codex reports "PR #… 待评审",** tell Claude "#N is ready". Claude reviews the PR on two axes and posts the review on it.
5. **Fix rounds:** paste this one line into the **same thread** (fill in the numbers):
   `Review round <k> for PR #<n> is posted on the PR. Read it with 'gh pr view <n> --comments' (the latest Claude comment) and implement every item exactly; then rebase, regenerate catalogs if you touched strings, just check and just test green, push, wait for CI, comment on the PR, and stop.`
6. **If a thread dies** (Codex error or a stale thread): start a **new** thread in the same folder and paste the fix-round line. Never rely on "resume last".

## Order

| Wave | Ticket | Worktree folder | Can start |
|---|---|---|---|
| 1 | #222 Pending accounts stay signed in | `de-linker-worktrees/c222` | now |
| 1 | #223 "Create account" wherever there's "Sign in" | `de-linker-worktrees/c223` | now |
| 1 | #254 German addresses and titles | `de-linker-worktrees/c254` | now |
| 2 | #225 Registration form (two steps) | `de-linker-worktrees/c225` | after #222 merges (same account code) |
| 2 | #263 Links and language switchers follow the language | `de-linker-worktrees/c263` | after #254 merges (URLs) |
| 2 | #264 German copy and data | `de-linker-worktrees/c264` | after #254 merges; can run beside #263 |
| 3 | #265 German checks and tools | `de-linker-worktrees/c265` | after #263 and #264 merge |

The three wave-1 tickets don't touch the same files, so run them side by side.

---

## Shared rules (already inside every prompt below)

Every prompt carries the lessons from the 2026-10-17/18 reviews, so the first round can pass:
- **Translations go through `.po`.** Regenerate with `just i18n-commerce <instance>` / `just i18n-tools` and keep `just i18n-coverage` green. Never hand-edit JSON or `.mo`. After a rebase, regenerate and prove that no existing German msgstr was lost or changed.
- **Public forms reuse what exists:**
  - linker-commerce: `Inquiry\PublicGuard` (honeypot + signed start + atomic per-connection limit);
  - linker-tools: `Genie\RateLimit` (atomic single-UPDATE limiter).
  - Any mail to an address a visitor typed sits under a sourced site-wide daily cap: refuse or skip the mail, never queue it.
- **Pixel gate:** use `tests/visual/pixel-parity.mjs`. It captures live and local in fresh contexts, with eager decoded images bounded to 5 s and animations off. EN must stay 0 differing pixels. Ruled German changes go into a change ledger with before/after.
- **Presentation:** LiveCanvas markup plus WindPress styles; PHP only supplies data. No inline styles, no plugin CSS on site pages.
- **Copy:** EN first, DE written independently in Sie form, adversarial review recorded in `docs/acceptance/<date>/<ticket>/copy-review.md`.
- **Numbers:** every number and threshold has a source comment.

---

## #222 · Pending accounts stay signed in, without prices

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c222` · instance `c222`

```
You are the implementation session for ticket #222 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (a dedicated worktree on branch feat/222-pending-signed-in). Never work in the main checkout /Users/chesterjohn/Documents/de-linker. Use the tdd skill for behaviour changes.

READ FIRST, in order: AGENTS.md (all rules; it wins); docs/agents/genie-kickoff.md section "通用规则" and follow it; docs/agents/codex-queue.md section "Shared rules"; `gh issue view 222 --comments`; docs/specs/184-account-chain.md; docs/specs/accounts-admin.md; plugins/linker-commerce/includes/Account/PendingGate.php and Gating/CommerceState.php. Then restate in 3-5 sentences what you will deliver, how completion is judged, and what you will not touch, and build.

TICKET (owner ruling 2026-10-17): a pending account stays signed in after registration and uses the site normally; it just doesn't see prices (CommerceState decides; don't write a second price rule). The whole-page "under review" takeover is replaced by a status notice on the account page and a short notice where prices would show, using the live card design (it exists on live; locally it needs `just sync c222` for compiled styles). Pending accounts can send inquiries (#246 is merged: inquiries are open to everyone). Restricted accounts already see their reason (#246): keep that consistent. The registration-received and approved emails stay. After approval, prices appear in the same session (no re-login). Completion: EN/DE × 1440/390 screenshots of register → stay signed in → product without price + pending notice → account page status → approve (WP-CLI or the accounts admin page on c222) → same session shows prices; tests for each account state; ruled visual changes in the change ledger; pixel gate 0 elsewhere.

Hard limits: instance c222 only (`just sync c222`, `just login c222 --user 857558227@qq.com`, `just status`); never touch other instances or processes (no pkill/killall); never deploy, merge or write to production (read-only SSH and browsing of live are fine); secrets only from env or ~/.config/terravolt-builder/*.env, never printed or committed; test mail to local files only; tests repeatable; fix in-scope issues in this branch.

Deliver: fetch, rebase on origin/main, `just check` and `just test` green. Open a non-draft PR titled with #222 whose body lists every completion criterion with evidence (tests, screenshots under docs/acceptance/<date>/222/, copy review); mark anything not done 未完成 with the reason. Wait for CI; when green, comment on issue #222 "PR #<n> 待评审" and stop. FINAL REPORT: PR URL, CI status, completion table, anything out of scope with the ticket it belongs to, instance used.
```

---

## #223 · "Create account" wherever there's "Sign in"

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c223` · instance `c223`

```
You are the implementation session for ticket #223 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (a dedicated worktree on branch feat/223-create-account-links). Never work in the main checkout /Users/chesterjohn/Documents/de-linker. Use the tdd skill for behaviour changes.

READ FIRST, in order: AGENTS.md (all rules; it wins); docs/agents/genie-kickoff.md section "通用规则"; docs/agents/codex-queue.md section "Shared rules"; `gh issue view 223 --comments`; docs/specs/split-login-register.md; the merged header work of #229 (PR #294: docs/acceptance/2026-10-18/229/, content/windpress/chrome.css, assets/header-menu.js), because you change the same header. Restate in 3-5 sentences what you deliver, how completion is judged, and what you won't touch; then build.

TICKET: wherever a guest sees "Sign in", give a "Create account" entry too, in EN and DE: the header account dropdown, the mobile menu, the footer account panel, and every "please sign in" gate (find each surface with evidence first; the header dropdown is output from plugins/linker-commerce/includes/Presentation/ProductShortcodes.php). Composition in LiveCanvas, styles in WindPress, PHP only data. The German header must keep #229's result: same structure as English and the same fold breakpoints in Chromium and WebKit, Firefox exception exactly 1283–1287 px. Extend #229's boundary sweep and rerun it in all three engines, because a new link can change the fit. Completion: guest EN/DE × 1440/390 screenshots of every surface; the change is a ruled change in the change ledger with before/after; everything else 0 differing pixels against live (tests/visual/pixel-parity.mjs); copy review for the new link text.

Hard limits: instance c223 only; no pkill/killall; never deploy, merge or write to production; secrets only from env files, never printed; test mail to local files; tests repeatable; fix in-scope issues in this branch.

Deliver: rebase on origin/main, `just check` and `just test` green, non-draft PR titled with #223 listing every completion criterion with evidence (mark anything not done 未完成); wait for CI; when green comment on issue #223 "PR #<n> 待评审" and stop. FINAL REPORT: PR URL, CI, completion table, out-of-scope notes, instance used.
```

---

## #254 · German addresses and titles

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c254` · instance `c254`

```
You are the implementation session for ticket #254 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (a dedicated worktree on branch feat/254-german-urls). Never work in the main checkout /Users/chesterjohn/Documents/de-linker. Use the tdd skill.

READ FIRST, in order: AGENTS.md (all rules; §3 vocabulary: no Warenkorb/basket/cart, no catalogue, no article); docs/agents/genie-kickoff.md section "通用规则"; docs/agents/codex-queue.md section "Shared rules"; `gh issue view 254 --comments`; docs/research/2026-10-17-i18n-audit/AUDIT.md; the linker-i18n plugin (same-slug and URL-segment translation) and how pages and their German twins are created by `present` (German twins of repo templates are owned by present, not by auto-translation; #253). Restate in 3-5 sentences what you deliver, how completion is judged, and what you won't touch; then build.

TICKET (owner 2026-10-17: "switched to German, everything is German-only"): every German address is German, with no English segment and no banned word, and every German page has its own German title, distinct from every other page. Known: /de/warenkorb/ → /de/loesungsentwurf/; /de/mein-konto/register/ → /de/mein-konto/registrieren/ with its own title (today it shares the login title); /de/faq-download/ → /de/faq-dokumente/; the lost-password page needs its own title. Scan every German URL on live (sitemap plus a crawl) and list each English segment you find. Old addresses all 301 to the new ones; internal links, links inside emails, the sitemap and hreflang follow. Prefer native mechanisms (Polylang slugs, Woo endpoint translation, linker-i18n's segment translation) over new redirects code; prove each choice in the spec. Data changes that production will need (slugs, titles) must be applied by repeatable code or a migration Claude runs at deploy, with a dry run; never by hand. Completion: a table of every German URL old→new with its 301 checked on c254; all German titles distinct and German; EN unchanged (0 pixels); tests for the redirects and the title rule.

Hard limits: instance c254 only; no pkill/killall; never deploy, merge or write to production (read-only checks of live are fine); secrets only from env files; test mail to local files; tests repeatable.

Deliver: rebase on origin/main, `just check` and `just test` green, non-draft PR titled with #254 listing every completion criterion with evidence, including the exact production steps Claude must run (dry run first); wait for CI; when green comment on issue #254 "PR #<n> 待评审" and stop. FINAL REPORT: PR URL, CI, completion table, production steps, instance used.
```

---

## #225 · Registration form (two steps), wave 2: after #222 merges

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c225` · instance `c225` (Claude creates it on unlock)

```
You are the implementation session for ticket #225 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (a dedicated worktree on branch feat/225-registration-two-step). Never work in the main checkout. Use the tdd skill.

READ FIRST, in order: AGENTS.md (the 2026-10-17 ruling "注册表单：两步" is binding and supersedes the single-page layout in the ticket's research section); docs/agents/genie-kickoff.md "通用规则"; docs/agents/codex-queue.md "Shared rules"; `gh issue view 225 --comments`; docs/prototypes/2026-10-17-registration/ (README, DECISION: variant B; prototype code is reference only, never shipped); plugins/linker-commerce/includes/Registration/ (Fields.php and the new-customer email template); docs/specs/accounts-admin.md (the #227 accounts page shows all stored registration fields automatically). Restate in 3-5 sentences; then build.

TICKET: two steps. Step 1 "Your company": company name, business type (3 options), country, and website or VAT ID, at least one of the two. Step 2 "You and your login": first and last name, email, password. A two-segment progress bar at the top with "Step 1 of 2 · Your company"; required and optional marked; one line above website/VAT saying we use it to verify the company. No address and no phone (the Proforma request page collects them natively). Country list: all countries, Germany first, then Europe, then the rest, with Woo's searchable select. Bot guard: reuse Inquiry\PublicGuard (honeypot + signed start + atomic limit) on woocommerce_register_form and woocommerce_process_registration_errors, before the account is created and before any mail; make the blocked count observable. The notification email and the accounts admin page show the same fields, the website included. The design follows the live auth card; the change from the owner-accepted numbered layout goes in the change ledger. Completion: EN/DE × 1440/390 screenshots of both steps and of errors; a bot attempt blocked with evidence; Outbox assertions for the notification content; copy review.

Hard limits: instance c225 only; no pkill/killall; never deploy, merge or write to production; secrets only from env files; test mail to local files; tests repeatable.

Deliver: rebase on origin/main, `just check` and `just test` green, non-draft PR titled with #225 with every criterion and evidence; wait for CI; comment "PR #<n> 待评审" on #225 and stop. FINAL REPORT as usual.
```

---

## #263 · Links and language switchers follow the language, wave 2: after #254 merges

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c263` · instance `c263`

```
You are the implementation session for ticket #263 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (branch feat/263-links-follow-language). Never work in the main checkout. Use the tdd skill.

READ FIRST: AGENTS.md; docs/agents/genie-kickoff.md "通用规则"; docs/agents/codex-queue.md "Shared rules"; `gh issue view 263 --comments`; docs/research/2026-10-17-i18n-audit/AUDIT.md (H1, H2, H3, H5 and the link findings); the merged #254 URL changes (use its new German slugs); PageUrls (the existing language-aware URL helper) and Mail\LocaleSwitch. Restate in 3-5 sentences; then build.

TICKET: every link and every language entry on a German page lands on the German (or the corresponding) page. H1: 104 German product pages send "Produkt anfragen" to the English /contact/, so the receipt is English. H2: the footer language switch is wrong site-wide (merge the header and footer switches into one implementation). H3/H5: German legal pages and category breadcrumbs link to English. Also: German blog posts, /de/danke/ and a category page that link to English or 404; Polylang's 301 drops /de/ from the query string, so the team gets 404 source links. Customer emails triggered from the admin (approval, Proforma) have German bodies with English links, because LocaleSwitch changes the WP locale but not the Polylang language; write the fixture test first. Structural fix: one entry point that builds URLs in the current language (generalise PageUrls); a CI rule that forbids hard-coded home_url('/…') in plugins; a render-time fallback that turns internal links into the current language without depending on translation jobs. Completion: every audit link finding rechecked (EN/DE) with evidence; the CI rule live (fails on main before, passes after); email-language fixture tests for front-end, admin and scheduled triggers; EN 0 differing pixels; ruled DE changes in the ledger.

Hard limits: instance c263 only; no pkill/killall; never deploy, merge or write to production; secrets only from env files; test mail to local files; tests repeatable.

Deliver: rebase, `just check` and `just test` green, non-draft PR titled with #263; wait for CI; comment "PR #<n> 待评审" on #263 and stop. FINAL REPORT as usual.
```

---

## #264 · German copy and data, wave 2: after #254 merges (beside #263)

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c264` · instance `c264`

```
You are the implementation session for ticket #264 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (branch feat/264-german-copy-data). Never work in the main checkout. Use the tdd skill where behaviour changes.

READ FIRST: AGENTS.md (§3 vocabulary; Sie form; the 2026-10-17 German auto-translation ruling: hand-written German stays, the repo's templates are owned by `present`); docs/agents/genie-kickoff.md "通用规则"; docs/agents/codex-queue.md "Shared rules"; `gh issue view 264 --comments`; docs/research/2026-10-17-i18n-audit/AUDIT.md (H4, H5 and the copy findings). Restate in 3-5 sentences; then build.

TICKET: German pages show German copy and data. H4: /de/produkte/ title and meta description are English. H5: 10 German category breadcrumbs show English names. Blog dates in English format ("May 29, 2026") and "Share on …" buttons. Banned words in the blog UI: "Artikel", "Katalog", "Weiter einkaufen", "Dieser Shop" (§3). "ET Series"/"ESA Series" → Serie. The FAQ translates "on file" as "im Bestand" (= in stock); fix it. Two German pages have meta descriptions that are cut-off body text. The lost-password title is part of #254; don't touch it. OUT OF SCOPE, owned by Claude's Genie work: anything in the Genie service, prompts, dock or chips ("Pairing", the dock link "FAQ & Downloads", du-form chips). Leave those, and list them in the PR as belonging to Genie. German data fixes that live in the database must be applied by repeatable code or a migration with a dry run that Claude runs at deploy, never by hand; hand-written German is preserved (translate only what is English). Every copy change goes through the adversarial review (DE written independently, Sie form). German visual changes are ruled changes in the ledger; EN 0 differing pixels.

Hard limits: instance c264 only; no pkill/killall; never deploy, merge or write to production; secrets only from env files; tests repeatable.

Deliver: rebase, `just check` and `just test` green, non-draft PR titled with #264 listing each audit item with evidence and the production steps Claude runs (dry run first); wait for CI; comment "PR #<n> 待评审" on #264 and stop. FINAL REPORT as usual.
```

---

## #265 · German checks and tools, wave 3: after #263 and #264 merge

Folder: `/Users/chesterjohn/Documents/de-linker-worktrees/c265` · instance `c265`

```
You are the implementation session for ticket #265 of the de-linker repository (GitHub AssassinFlash/de-linker), managed by Claude, who reviews your PR. Work autonomously to completion in the current working directory (branch feat/265-german-checks). Never work in the main checkout. Use the tdd skill.

READ FIRST: AGENTS.md; docs/agents/genie-kickoff.md "通用规则"; docs/agents/codex-queue.md "Shared rules"; `gh issue view 265 --comments`; docs/research/2026-10-17-i18n-audit/AUDIT.md (structural recommendations); what already exists: `just i18n-coverage`, `just i18n-commerce`, `just i18n-tools` (from #288 and #302: linker-tools .pot and make-json generation are already done; don't redo them), the banned-words check in the justfile, and #263's hard-coded-link CI rule. Restate in 3-5 sentences; then build.

TICKET: German problems are caught by CI, not by eye. Add a German lint for banned words, English date formats and du-form in German copy (templates, .po msgstr, LC partials), without duplicating checks that already exist: extend them instead. Write down the single owner of each kind of German text (.po, generated JSON, per-language LiveCanvas templates owned by present, database content kept by auto-translation) in the spec, and add a check per kind that something stays in its place. Each check must fail on a planted fixture and pass on main after #263/#264. Completion: the checks run in `just check` and CI; red/green evidence for each; the spec section written.

Hard limits: instance c265 only; no pkill/killall; never deploy, merge or write to production; tests repeatable.

Deliver: rebase, `just check` and `just test` green, non-draft PR titled with #265; wait for CI; comment "PR #<n> 待评审" on #265 and stop. FINAL REPORT as usual.
```

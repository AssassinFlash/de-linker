# b2-draft mission: solution draft quantity / remove / undo audit

2026-10-29. Mission: make the solution draft (Lösungsentwurf) let a customer
change a line's quantity, remove a line explicitly, and undo that removal;
evidence cited was `docs/acceptance/2026-10-21/472/README.md` ("quantities
stayed 1", only `cart/remove-item`). Result: **the capability already exists
end to end on this tree and on production** through the native-WooCommerce
design the spec mandates; no behaviour change was needed or added. This record
is the audit trail: what exists, where, and the tests rerun on the current
head to confirm it.

## Why the 2026-10-21 evidence is stale

The #472 walk ran on production **before** the draft-editing line of work
landed. Published since, on this exact surface:

- **PR #677** (c53011da2) — inquiry right column: unsaved quantity edits
  (including zero/invalid) block inquiry submission; Woo `update_cart` +
  `woocommerce-cart` nonce is the only writer (`docs/specs/11-commerce.md`).
- **PR #690** (493b9fa2, merged 2026-10-27, production read-back recorded) —
  standalone draft page: dirty or in-flight native quantities block
  continuation with the localized update instruction; native update releases
  the guard.
- **PR #692** (5bef4f518) — empty-branch `.woocommerce` wrapper +
  `.wc-empty-cart-message` marker so native notices render: last-item
  Remove/zero keeps the **Undo** link working without refresh.
  Snapshot-backed local walks EN 1440 and DE 390 covered
  Remove → empty + Undo → quantity 1.
- **PR #695** (15194fa7) — empty-draft action spacing only.

Between 15194fa7 and today's head (a5cbb4026) the diff on
`plugins/linker-commerce` touches none of the draft surfaces
(`git diff --stat 15194fa7..HEAD -- .../cart_page.html .../Vocabulary
.../Gating .../Presentation/Shortcodes.php` shows only account-ui bfcache
recovery, compare/blog/library/PDP work), so those walks' conditions still
hold and their evidence is reused per AGENTS.md §0.1.

## What exists today (implementation map)

The filled solution draft **is** WooCommerce's cart on the LC template; the
spec forbids a parallel draft store or a second quantity writer
(`docs/specs/11-commerce.md`), so all three capabilities ride Woo's native
cart form:

- **Quantity per line, server-validated.** Native `[woocommerce_cart]`
  rendered by `plugins/linker-commerce/content/livecanvas/cart_page.html:13`
  (`input.qty`, `min` 1 / integer step; stock-bounded max and integer
  validation inside Woo's own `update_cart` handler). Unsaved edits block
  inquiry/continuation in `plugins/linker-commerce/assets/account-ui.js:16-52`
  (`draftChanged`/`draftBlocked`, `[name="update_cart"]` focus fallback).
- **Explicit remove, accessible label.** Native remove link; its
  `Remove %s from cart` string is vocabularized to "Remove %s from the
  solution draft" / "%s aus dem Lösungsentwurf entfernen"
  (`includes/Vocabulary/Terms.php:45`, `languages/linker-commerce-de_DE_formal.po`).
- **Undo restoring the same line and quantity.** Woo native: remove notice
  carries the `undo_item` link (`WC_Form_Handler`), `restore_cart_item`
  brings back line and quantity; the transport runs through this site's
  nonce gate (`includes/Protection/Draft.php:61,112-129` allow
  `remove_item`/`undo_item`/`update_cart` with the `woocommerce-cart` nonce).
  The empty branch prints native notices so Undo survives the last line
  (`cart_page.html:4-9`, PR #692).
- **Screen-reader announcement.** Woo's success notice template renders
  `role="alert"` (live region) — the remove/undo and update confirmations are
  announced; the guard notice is `role="status"`
  (`cart_page.html:11`).
- **EN + DE, existing i18n mechanism.** Overrides via
  `includes/Vocabulary/Terms.php` + plugin `.po/.mo` ("Update solution
  draft" → "Lösungsentwurf aktualisieren", guard notice in Sie-Form, see
  `languages/linker-commerce-de_DE_formal.po`). Woo's own undo words come
  from Woo's `de_DE_formal` pack ("Rückgängig machen?", "%s entfernt.") —
  Sie-Form, no cart vocabulary leaks.
- **Design system.** Markup is the LC template; quantity/remove/notices are
  styled only in the existing WindPress volume
  (`content/windpress/storefront.css:1277-1415,1609-1615`). No inline styles,
  no second Tailwind pipeline, no new copy (so no copy adversarial review was
  triggered — none was needed).

## What was rerun on this head (a5cbb4026)

Worktree `/Users/chesterjohn/Documents/de-linker-worktrees/b2-draft`, branch
`codex/b2-solution-draft-editing`:

```
plugins/linker-commerce $ composer install
plugins/linker-commerce $ PHP=/opt/homebrew/opt/php@8.3/bin/php \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit tests/php/Unit/Vocabulary
OK (20 tests, 223 assertions)
plugins/linker-commerce $ PHP=/opt/homebrew/opt/php@8.3/bin/php \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit tests/php/Unit/Presentation
OK (283 tests, 2147 assertions)
plugins/linker-commerce $ node --test tests/js/account-ui.test.mjs
ℹ tests 30  ℹ pass 30  ℹ fail 0
```

Browser-level Remove→Undo→quantity-1 and dirty-quantity walks were **not
repeated** here; the same-code local/production evidence from PRs #690/#692
is reused (see above for why the code is unchanged on this surface). No new
snapshot instance was created — AGENTS.md §0.1 reuse applies and no new risk
needed excluding.

## Known still-open item (pre-existing, not this mission's scope)

PR #695 recorded that **online** final-item Remove/zero/Undo *transition*
visuals remain separately open ("ONLINE VISUAL REMAINS PENDING until browser
access resumes" in #692; #695 accepted geometry only). That is a production
visual-acceptance gate on the deployment process, not a capability gap; it
stays tracked in those PR records. The German save-URL defect is #473,
untouched here.

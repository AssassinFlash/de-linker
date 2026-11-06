# Post-deploy regression check: guest inquiry chain, production 2026-11-06

Executor: main session. Trigger: the `linker-tools` build deployed earlier
today (PR #970 view fix + cutover SSH fix) landed with a fresh
`plugins/linker-commerce` bundle; the first principle (owner 2026-11-04)
requires re-proving that a natural guest can submit an inquiry on the real
production chain with zero blockage and zero errors.

**Result: PASS on both real-customer paths. The initially suspected
regression is disproven** — see "Suspected regression" below.

## Suspected regression → resolved as tool artifact

While filling the form in Kimi Code's built-in browser, the status line
showed `Verification could not be completed. No request has been sent in
this attempt. Please try again or email sales@de-linker.com.` and, after a
resubmit, the interactive-state sentence. Code reference:
`plugins/linker-commerce/src/protection/client.ts` (widget lifecycle),
`messages.ts` (`failed()` / `interactive` texts).

Evidence chain:

1. Server side healthy: `POST /wp-json/linker/v1/protection/prepare`
   (curl, action=inquiry) → HTTP 200 with `mode=enforce`, site key,
   signed prepare blob, `lifetime=300`. No protection entries in
   `wc-logs/` failures — the failure happened in the Cloudflare challenge
   layer, not our endpoints.
2. The interactive state is the designed fallback
   (`before-interactive-callback` unhides the widget): a challengeable
   browser gets a visible, clickable checkbox — not a dead end.
3. The built-in browser is automation-flagged by Cloudflare, so its
   challenge loops; real Chrome (below) passes. Conclusion: tool
   limitation, not a product regression introduced by today's deploy.

## Path 1 — first visit, incognito real Chrome (no cookies)

Real Google Chrome incognito window (driven via macOS Computer Use),
`https://de-linker.com/proforma-request/`, guest, fields: message, name
(`Regression Check 2026-11-06`), email, company, consent.

1. Submit → widget entered the interactive state once ("Please complete the
   verification."), rendering one Cloudflare checkbox "Verify you are human".
2. One human click on the checkbox → token obtained, widget removed,
   form auto-submitted. No error at any step.
3. Confirmation page `/proforma-request/inquiry-received/8615/?key=wc_order_Mo2pvy82j6SNP`.

Read-back: order 8615 `status=inquiry-received`, billing fields correct.
Mail log `wc-logs/linker-mail-2026-11-06-…log`: internal "New inquiry
#8615 from Regression Check GmbH" + customer "Your inquiry #8615 has been
received", both rewritten by test mode to the single tester address, one
delivery each.

## Path 2 — repeat visit, normal Chrome profile (cookies, browsed first)

Same machine, normal Chrome window: visited `/products/` first, then the
inquiry page, same guest flow (name `Repeat Visit Check`).

1. Submit → **no challenge shown at all**; the page navigated by itself to
   `/proforma-request/inquiry-received/8618/?key=wc_order_uJCS2djB48vqj`.
   No checkbox, no error, no visible verification step.

Read-back: order 8618 `status=inquiry-received`, billing fields correct;
mail log shows both messages for #8618 to the tester address, one each.

This matches the 2026-11-05 acceptance (invisible pass in a warm normal
browser) and extends it: the first-visit cold context costs exactly one
checkbox click.

## Conclusion for the owner's first principle

- Normal/returning customer: zero friction, invisible verification — PASS.
- First-visit customer: one standard Cloudflare checkbox, then through —
  no error, no blockage — PASS.
- Automation-flagged browsers (our built-in test browser) stall at the
  challenge. That is Cloudflare's anti-bot verdict working as configured,
  not a customer-facing defect.

## Cleanup (all read back)

- Orders 8615 and 8618 deleted (`delete(true)`); `wc_get_order` → gone
  for both.
- `wp linker-commerce test-mail off` executed and read back: "Test mode is
  off: emails go to their recipients again."
- Chrome incognito test window closed; test tab in the normal window
  closed (original tabs restored); built-in browser test tab closed.

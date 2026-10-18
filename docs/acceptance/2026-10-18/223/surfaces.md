# Guest sign-in surface census

Source: current branch after rebasing on origin/main; runtime fixture c223.
The user explicitly included recovery links, private-document denials and Genie.

| Surface | Source / consumer | Guest behavior under #223 |
|---|---|---|
| Desktop account dropdown | Presentation/ProductShortcodes::header_utilities | Sign in plus LC create link, outside the measured navigation row |
| Mobile menu | same shortcode, part=mobile, LC header partials | Existing two icons plus a visible create link inside the disclosure |
| Footer Account / Konto panel | EN/DE LC footer partials | Two independent account links in the existing first tile; destination count 04 |
| Product list and category cards | ProductShortcodes::products_card, product-family.js | Visible pricing-login action and create link; hidden price HTML is not accepted as visible proof |
| Product details (rail and mobile bar) | ProductShortcodes::pdp_price, EN/DE LC product templates | Native sign-in return URL plus create link |
| Comparison | ComparePage::table | Guest price prompts include a direct create entry |
| Empty solution draft | Shortcodes::draft_empty, account/empty-draft.html | Browse products, Sign in, Create account; no registration form embedded |
| Nonempty solution draft | Gating/PriceDisplay::label + DraftSummary::guest_totals | Each Woo price/subtotal cell and the summary offers direct registration; suppress it for signed-in accounts and when Woo registration is closed; keep open inquiry |
| Proforma request / inquiry | inquiry/form.html | No account needed; optional login and direct registration; do not restore the obsolete guest gate |
| Sign-in card | auth/form-login.php | Already has a direct Create your business account link; retain it |
| Registration card | auth/form-register.php | Already is the registration destination and links back to Sign in; no self-link added |
| Password recovery and sent confirmation | auth/form-lost-password.php, lost-password-confirmation.php | Back to sign in plus direct create entry; unchanged forms and processing |
| New-password form | auth/form-reset-password.php | No sign-in entry to pair; no fields, keys, nonce or handling changed |
| Private Proforma / report denial | Account/DocumentDownload::serve + LC document-denied.html | Keep 403 and original-account instruction; registration grants no document access |
| Genie dock and workspace | Genie/Entries::mount_markup + commerce LC guest-links.html | Localized guest account entries outside React; available for both login text and price notes; no model-text parsing |

`Vocabulary/Terms` maps Woo notices but creates no separate page: account-page
login forms already expose registration. Staff sign-in and sign-out actions are
not guest registration invitations. No customer email contains a new entry.

The supplied docs/agents/codex-queue.md was absent from this checkout, the local
origin/main tree and the other worktrees when inspected. The current prompt,
AGENTS.md, genie-kickoff general rules and issue/spec remain the working sources.

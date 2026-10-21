# Populated drafts and Genie answer actions

The owner supplied screenshots showing cramped draft summary actions, dark text on a purple button, and unstyled Genie product actions. The follow-up audits rendered states rather than treating page loads as sufficient evidence. Existing customer copy, price permissions, models, API handlers and submission behavior stay unchanged.

## Presentation changes

- LC draft summary enters the existing Woo proceed wrapper; WindPress supplies the white summary card, 16px action spacing, primary and secondary buttons, and a rounded native quantity input. Only duplicate price-gate unit cells are hidden; numeric prices remain visible.
- Genie product, action and document controls use the existing app delivery pipeline. Primary/secondary, hover, keyboard focus, pending, success, retry and unverified states are covered. Only a sending PartsCard carries aria-busy and a waiting cursor.
- The expanded phone hero uses full-width cards after the 390px German screenshot showed mid-word button wrapping in two columns. The unopened home hero remains unchanged. The existing 600px breakpoint applies.
- Phone footer labels use readable 12px type and a 3+2 layout with extra width for German services. Below 360px, the layout uses two columns and a full-width final destination. This follows the measured space required for whole German words.

## Independent review

Spec review found one defect: completed PartsCard actions inherited the busy cursor. Fixed by limiting busy semantics to sending; two terminal-state unit cases and browser cursor checks cover it. Final Spec review passes. Standards review found no implementation blocker and requested explicit footer geometry/type and priced-unit visibility assertions; both were added. The native DraftSummary suite passes 7 tests / 19 assertions.

## Acceptance boundary

Browser tests use the real local app with deterministic response fixtures for otherwise difficult error states. They intercept model/cart/save writes. Guest draft tests use native Woo quantity and page navigation, and an existing local staff session verifies priced-unit visibility. No account, inquiry or email is submitted. Production publication, real model product-card response and native draft readback are separately recorded in the adjacent local evidence package after deployment.

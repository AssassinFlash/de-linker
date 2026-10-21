# Populated drafts and Genie answer actions

The owner supplied screenshots showing cramped draft summary actions, dark text on a purple button, and unstyled Genie product actions. The follow-up audits rendered states rather than treating page loads as sufficient evidence. Existing customer copy, price permissions, models and backend API handlers stay unchanged. Inquiry submission waits for an in-flight draft edit.

## Presentation changes

- LC draft summary enters the existing Woo proceed wrapper; WindPress supplies the white summary card, 16px action spacing, primary and secondary buttons, and a rounded native quantity input. Only duplicate price-gate unit cells are hidden; numeric prices remain visible.
- Genie product, action and document controls use the existing app delivery pipeline. Primary/secondary, hover, keyboard focus, pending, success, retry and unverified states are covered. Only a sending PartsCard carries aria-busy and a waiting cursor.
- The expanded phone hero uses full-width cards after the 390px German screenshot showed mid-word button wrapping in two columns. The unopened home hero remains unchanged. The existing 600px breakpoint applies.
- Phone footer labels use readable 12px type and a 3+2 layout with extra width for German services. Below 360px, the layout uses two columns and a full-width final destination. This follows the measured space required for whole German words.

## Independent review

Spec review found one defect: completed PartsCard actions inherited the busy cursor. Fixed by limiting busy semantics to sending; two terminal-state unit cases and browser cursor checks cover it. Final Spec review passes. Standards review found no implementation blocker and requested explicit footer geometry/type and priced-unit visibility assertions; both were added. The native DraftSummary suite passes 7 tests / 19 assertions.

## Acceptance boundary

Browser tests use the real local app with deterministic response fixtures for otherwise difficult error states. They intercept model/cart/save writes. Guest draft tests use native Woo quantity and page navigation, and an existing local staff session verifies priced-unit visibility. No account, inquiry or email is submitted. Production publication, real model product-card response and native draft readback are separately recorded in the adjacent local evidence package after deployment.

## Inquiry continuation from the owner screenshot

The inquiry summary had no explicit remove control, no product-link hover color, and no native notice target. LC now supplies the native Woo cart-form/contents/line/remove hooks and a notices wrapper; PHP supplies only native escaped remove URLs and already-translated Remove terms. Woo cart.js handles quantity, remove, undo, nonce validation, feedback and fragment readback. The separate main inquiry form is not replaced, preserving unsent message/name/email/consent.

The hidden native proceed field returns the quantity POST to the checkout GET before rendering. This matters for German: the Woo update handler sets WOOCOMMERCE_CART during POST, so an immediate German LC fallback otherwise chooses the cart template. Native redirect avoids rendering in that transient context. No alternate cart API or custom writer was introduced.

The existing account interaction script observes Woo's processing state, visibly disables the inquiry send action and rejects a submit event while the draft write is pending. A held-request browser fixture checks that no admin-post submission happens, and that sending re-enables after readback. Product links gain color/underline/focus; draft-page remove icons also receive visible 44px bordered controls.

Staff price checks snapshot the existing local Woo session and persistent cart into a guarded local-only fixture option, then stop the page and restore inside nested finally blocks. Native cache deletion and strict row/meta readback precede snapshot cleanup. No production user session is changed by those tests.

## Native Woo visual finish

The owner explicitly requested evaluating and improving native update visuals. The native update controls now use the site's 44px secondary action style, legible disabled colors, hover/focus feedback and the existing account loading spinner. Native success/info/error notices use the established semantic palettes and a 44px Undo target. The native handler, overlay interception and response protocol remain in use; reduced motion stops the spinner.

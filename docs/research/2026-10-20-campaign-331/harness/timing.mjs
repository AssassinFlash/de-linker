/**
 * Waits the #331 drivers share. Each number cites the clock it is waiting on.
 */

/**
 * Client abort for one direct-service turn, and the browser poll for an
 * answer landing.
 *
 * Source: `tests/e2e/lib/genie.ts` (`timeoutMs ?? 180_000`) and the same
 * poll in `tests/e2e/specs/genie-sessions.spec.ts`. The WordPress proxy
 * gives up at 60 s (`plugins/linker-tools/includes/Genie/Proxy.php`,
 * `'timeout' => 60.0`: at most four ability calls of 20 s, plus the
 * model). The direct client talks to the service, so it uses the e2e
 * panel's abort, not the proxy's.
 */
export const TURN_TIMEOUT_MS = 180_000;

/**
 * After a reload that raced an in-flight turn, wait out the proxy before
 * reading the thread again.
 *
 * Source: Proxy.php `'timeout' => 60.0` (the comment above it: the
 * browser's one request must outlast the worst legitimate turn). The
 * extra 10 s is so the second reload happens after that budget has
 * stored the turn or given up.
 */
export const PROXY_SETTLE_MS = 70_000;

/**
 * Dwell after the double-submitted question's answer, so a second copy of
 * the question can paint if the in-flight guard accepted it.
 *
 * Source: a user message is rendered when the send is accepted, not when
 * the model returns. The shell reveals an answer locally in at most 1.2 s
 * (docs/specs/13-genie.md, the owner bound of 2026-10-18). 8 s is that
 * reveal plus margin for the second bubble to commit. It is not a second
 * model budget; those stay at TURN_TIMEOUT_MS and the proxy's 60 s.
 */
export const DOUBLE_SUBMIT_DWELL_MS = 8_000;

/**
 * After the fresh tab shows the first question, pause, then reload.
 *
 * Source: restoring a thread is one GET
 * (`plugins/linker-tools/src/genie/api/turn.ts`, `readThread`). 5 s is
 * not a model budget. It lets a proxy write that finished during
 * navigation land before that reread. The model budget remains
 * TURN_TIMEOUT_MS; the proxy budget remains 60 s.
 */
export const RACE_REREAD_MS = 5_000;

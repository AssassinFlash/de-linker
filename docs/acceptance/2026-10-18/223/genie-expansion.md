# Owner-expanded Genie reply scope

The owner explicitly expanded this implementation on2026-10-18: right-bottom
dock follows OpenAI Help Center conversation presentation; full workspace
follows ChatGPT conversation and streaming presentation. Preserve both surfaces,
existing shared conversation and all business/model/permission contracts.

Public seams remain rendered UI output and real browser behavior. The browser
must observe actual incremental HTTP events, waiting/receiving/completed/error
and cancellation, rather than a typing timer over a buffered final string.
Verified product/document facts remain server-grounded before display. Raw
model tokens must never be exposed before existing grounding/hydration.

Current findings: browser sendTurn awaits JSON containing an entire SSE string;
PHP Proxy buffers wp_remote_post, then records and returns that JSON; FastAPI
runs the entire guarded turn before yielding meta/block/done. Assistant text is
rendered as plain content, and votes are emoji. The old design dossier verified
guest landing and helper shell, not authenticated reply internals.

A primary-source research agent is collecting official ChatKit/OpenAI evidence
viaApify. Exact unobserved Help reply pixels must remain identified as unverified.

Implementation slices: safe semantic answer formatting; message/action/state
presentation; real verified-event delivery and cancellation; browser scroll,
reduced-motion, retry/failure and reload behavior. Existing card/document/contact
capabilities remain available. No registration, inquiry permission or model route
is changed. Final evidence and review must cover this expanded scope beforePR.

## Superseding owner boundary: frontend only

The owner subsequently clarified that actual backend streaming is unnecessary:
backend receive/answer/persistence and request semantics must stay unchanged.
Simulated thinking/loading/progressive presentation is explicitly authorized.
All experimental Proxy, StreamResponse, StreamTransport and API streaming
changes were removed. The held-upstream test/log records an abandoned experiment,
not a delivered feature. Model/service and conversation APIs remain unchanged.
The final renderer receives the complete verified answer through the existing
JSON API and reveals it progressively on the client; reduced motion and an
explicit “Show full response” control bypass the animation. Canonical answer
text and business blocks remain complete, so animation cannot alter follow-up
context, storage or permissions.

## Delivered frontend choices

The user's later clarification explicitly asks for simulated dynamic thinking,
loading and flowing response presentation. Waiting has a breathing dot, moving
text highlight and animated skeleton lines; it is not static text. The complete
answer then reveals locally over 300–1200ms (3ms per Unicode code point, capped
at 1200ms), with an immediate-show control. These are local design choices,
not measured OpenAI timings. Reduced motion disables all waiting/reveal motion.

Markdown is parsed safely (raw HTML disabled); model narrative cannot create
new image loads or destinations. Verified document/product blocks remain the
original implementations. Text, lists, headings, code, tables and blockquotes
share a quiet reading rhythm. Copy uses the complete canonical original text;
feedback retains the existing vote API with SVG icons. History loads instantly,
completed answers do not replay on reopening, and no client persistence format
changes. Long answers preserve the reading position under Genie goal 9; only
new user questions and an explicit “Jump to latest” move to the bottom.

The earlier experimental backend-delivery logs are superseded and do not form
final acceptance. Proxy.php, api/turn.ts and api/turn.test.ts have zero final
diff against the pre-expansion implementation. No new backend file is retained.

## Entry coverage and frontend/backend decision

Owner asked whether /genie/ and hero were synchronized. /genie/ and the dock
both mount App and share Reply/MessageBody/Transcript, with surface-specific
WindPress density. Browser tests cover EN/DE ×1440/390 for both. The current
home hero is a link to /genie/: Computer Use clicked Submit query and verified
the actual workspace. The selected inline hero is not implemented on this base;
[Genie · hero 接线实现](https://github.com/AssassinFlash/de-linker/issues/232)
remains open, with the attachment prerequisite PR309 still open. No claim of
inline-hero completion is made by this ticket. Its future frontend should reuse
these shared components rather than introducing a second answer renderer.

This ticket changes front-end rendering/state only. It does not alter receiving,
model answers, prompts, tools, grounding, permissions, transport or saved thread
format. Actual backend incremental transport/content changes remain outside
the owner's final request.

Computer Use also verified the residential solution hero’s submit/suggestion
links target /de/genie/ and enter the same workspace renderer. Its attachment
and voice controls are disabled on this base, and their separate wiring is not
claimed as delivered here. The current entry check is preserved in
computer-use/de-solution-hero-to-workspace-1440.png.

# #223 · Genie presentation and reply fidelity

All work commissioned in this session stays in #223 and PR #312. The owner
requested a compact OpenAI Help Center style dock and a ChatGPT style full
workspace, then clarified that thinking/loading/flowing presentation should be
simulated in the frontend. Backend token streaming is not required.

## Delivered presentation

Dock and `/genie/` mount the same App/Reply/MessageBody/Transcript. WindPress
sets their surface-specific density. Both have dynamic waiting text, a breathing
dot and skeleton; a received complete answer reveals locally over 300–1200ms
(3ms per Unicode code point, capped). These timings are local design choices,
not measurements of OpenAI. Reduced motion and “Show full response” bypass
animation. Copy and following questions use the complete canonical answer.

Safe Markdown preserves existing headings, emphasis, lists, tables, code and
quotes. Raw HTML is escaped; narrative cannot introduce new image requests or
unverified destinations. Verified product/document blocks retain their native
links and data. Long plain prose is visually grouped at sentence boundaries
without rewriting words. The introduction and existing heading levels have
separate type hierarchy; actual document blocks have a compact document card.
The structured deciding question has a contained **Reply with an option /
Antwort auswählen** group, an explicit immediate-send explanation and a Send
affordance on each real button. `phase` reuses
“Grid connection / Netzanschluss”; other fields use the reviewed continuation
label. Option text and callbacks remain unchanged. The browser does not invent
headings, facts or emphasis for a plain answer.

The transcript and composer are separate flex rows. The 40px jump button has a
48px controls band between them and cannot cover text. Incoming answer growth
does not pull the reader down. An explicit jump settles at the actual bottom;
keyboard focus is visible, pointer focus has no persistent blue ring. History
restores without replaying the reveal.

## Storage defect discovered by real reopening

Computer Use received a properly separated answer, then reopened it on the
product page and saw literal `nn` in place of blank lines. Native WordPress
meta writing unslashed the raw SSE JSON. The narrow PHP persistence correction
saves MESSAGES and STREAM with `wp_slash`, preserving JSON newlines, Unicode,
quotes and literal backslashes. The public GET route fixture first fails on
this exact corruption, then passes byte-for-byte; its full suite runs twice
with 18 tests / 166 assertions. Unit doubles do not claim to verify storage.

This changes PHP persistence escaping. The persistence repair does not change generation. Subsequently the owner
explicitly approved a narrow EN/DE prompt **formatting contract**: topical
Markdown headings, bullets and sparse emphasis, preserving all existing
factual, exact-wording and brief-response rules. The model, tools, grounding,
permissions, REST schema and buffered transport are unchanged.
No migration or guessed repair of already damaged old histories is performed.
A fresh real German answer was compared before and after a page refresh:
`sameRenderedAnswer: true`, one answer. See `checks/roundtrip-*.log` and
`computer-use/de-genie-round3-dock-reopened-*.png`.

## Entry coverage and remaining limit

Both dock and workspace have the LC guest login/registration row before the
React mount, with no visual order reversal. #236 attachments/busy-send and
#250 inquiry confirmation/sent cards from main remain inside the reading flow.
Inquiry registration is not added to transactional emails.

Current homepage and solution hero submit/suggestion links enter the shared
workspace, so that destination uses this reply design. Computer Use followed
both entries; the existing images are retained. A transcript mounted inline
inside the hero is **未完成** on this branch; no such delivery is claimed and
no new ticket is created to move this session's work elsewhere.

Official primary-source research and supplied references informed the local
composition. Authenticated OpenAI reply internals were not captured, so this is
not a measured pixel replica of those internals. Deterministic EN/DE ×1440/390
waiting/answer/latest screenshots and videos are in `replies/`; real model
inspection is in `computer-use/*round3*` and the latest `replies-real/`. The latter uses actual
model replies to the same EN/DE multi-topic questions, without asking the
question itself to use Markdown, and checks identical text after reopening. Fixtures intercept the existing JSON
response only in their browser; they are not model answer-quality tests.

## Earlier evidence

Rejected grey/disconnected footer views and earlier reply screenshots remain
in the packet. The abandoned real-streaming experiment is not delivered.
`replies/before-round2/` preserves the three defects returned by the owner.
The final browser fixtures assert controls do not overlap text, pointer focus
has no outline, the final paragraph is fully reachable, and choices are sent
verbatim. Earlier failed pixel captures remain evidence; only the latest paired
capture and exact recount determine the final pixel result.

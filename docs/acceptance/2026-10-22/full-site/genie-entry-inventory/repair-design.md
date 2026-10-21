# Marketing assistant entries and planning-note repair design

Status: executable design and throwaway logic prototype; Spec and Standards independent design/copy reviews PASS. Parent authorised Batch A source implementation on codex/marketing-genie-entries after the preceding release was read back. Batch A actual-browser acceptance is in progress; Batch B remains designed, not implemented. No deployment or mail is performed by this design task. The current behavior and the complete 50-page census are in `inventory.md`; this document defines the proposed replacement behavior, not an assertion that it already exists.

## Question and decision

Can the six affected marketing Pages deliver a complete typed question or document/voice draft to the existing Genie, and can the Installer desktop Plan entry carry a useful original requirement into planning without inventing sizing facts or losing that requirement later?

Decision: keep the current LC composition and visual appearance. Residential/Commercial and Installer mobile use the existing Genie loader. Suggestions remain prefill controls. Installer desktop still opens Solution Configurator; a **project note with an explicit consumer** accompanies it. The note stays distinct from calculation input through result, save, PDF, solution draft and inquiry. No new model, route provider, numeric extraction model or alternate assistant is introduced.

The prototype is the LOGIC branch of the prototype skill: one self-contained HTML file, memory-only, with visible state and guided actions. It demonstrates delivery/retry and field-confirmation rules; it is not proposed production markup or a second CSS pipeline. Open `entry-handoff.prototype.html` directly. No server, network or dependency is required. Archiving/commit is owned by the parent after the design is settled; this child creates no branch or commit.

## Evidence and mature patterns reused

| Existing authority, verified from current source | Reused behavior | Limit explicitly respected |
|---|---|---|
| `includes/Genie/Entries.php` loader: ask → pending boot → ready → open | One common app; correct current config/nonce/locale; no lost cold-start question | `message` and `attach` are mutually exclusive today. There is no voice/draft transfer contract yet. Source field value alone is not acknowledgement. |
| `assets/search-ask.js`, PDP UI, proactive preview controller; spec 13 entries | Existing message delivery and attachment intent instead of new transport | Static navigation stays navigation; no question is dispatched from an ordinary “Open Genie” link. |
| `src/hero/controller.tsx`, attachment preparation/useAttachments, shared dictation; spec 13 homepage/attachments/failure | Existing image/PDF preparation, refusal, current browser dictation and failed-turn recovery | Hero controller stays home-only. No copying the home app into marketing pages, no new speech provider. |
| Marketing page-specific suggestion listener, captured actual browser prefill | Edit and send the chosen suggestion | Suggestion click is not changed to automatic model submission. |
| `linker/size-hint` → Configurator `Mount` → `config.ts`; specs 13/14 | Five structured field consumers already exist | Raw free-form text is not a sixth supported sizing argument. Values are not guessed from arbitrary numbers/model names. |
| Configurator sources dossier (`2026-10-12-configurator-sources`): carried project facts and editable planning inputs | A short entry continues into visible, editable project inputs | The dossier is design evidence; it does not establish an absent note schema. |
| Current browser session/failure convention | Same-tab reload/back recovery without public prompt URLs | New note/draft cache records are small text/filename records. Current prepared-byte recovery starts only after send; earlier refresh names missing files for re-selection. |
| Installed Woo Store API `functions.php`, `CartExtensions`, `ExtendSchema` | Native `/cart/extensions` update/read extension for draft note context | This is an available Woo seam, **not an already registered Linker note extension**. |

## Scope and actual entry map

| Pages | Existing visible source | Consumer after repair |
|---|---|---|
| Residential EN749/DE6923; Commercial EN792/DE6921 | `.lk-dialog-prompt`, `.lk-send-btn`, `.lk-capsule[data-lk-ask]`, attachment/voice | One marketing binder → current loader → existing App draft/ask/attachments. Existing capsule listener preserved or folded without changing prefill behavior. |
| Installer EN826/DE6869 at phone layout | `#installer-mobile-query`, `.installer-assistant-send`, nameplate/attach/voice | Same binder and current App; no second marketing-specific conversation implementation. |
| Installer desktop | `#lki-hero-query`, `.lk-btn-query`, Enter | Note staging with verified readback → current-locale Configurator → note/field review consumer. Plan purpose retained. |
| All ordinary `/genie/` links | Plain anchors | Navigation only. Do not blanket-intercept all Genie URLs. |
| Home/Products/current helper triggers | Existing current controllers | Preserve existing behavior; regression controls, not replacement targets. |

## Assistant delivery contract

### Data and ownership

One source draft has an immutable per-attempt entry ID and `{text, sourcePath, mode}`. `mode` is compose/attach/nameplate/voice, and `sourcePath` is an internal same-origin pathname, never a redirect destination. The current loader/open event may gain this narrow optional **draft context** alongside its established fields. Its semantics must be typed and tested. It must not overload `message + attach` and hope both current branches run.

- A Send gesture snapshots the exact original text. Source text stays present while the dock loads and until delivery has been accepted into the current App/failed-turn owner. A small current-scope same-tab recovery draft survives a refresh/back before the app has loaded; identity verification must happen before cached text can be rendered. It does not auto-submit on reload.
- Source event binding reads the actual field. Plain Enter sends; Shift+Enter inserts a newline; composition/IME Enter does not send. Empty/whitespace Send does not produce a turn or discard a file. No default navigation follows an accepted handoff.
- Loader pending state coalesces repeated clicks for the same attempt. A later edited draft cannot silently overwrite an accepted question or disappear behind it. The source remains editable only if that edit is clearly a **next draft**; it is never silently substituted into an in-flight turn.
- Extend the current state notification with optional attempt identity/phase acknowledgement, or an equivalently narrow current-loader interface, so the source knows booting/accepted/settled. Do not infer success from `open:true` or DOM presence. Exactly one owner sends the snapshot, using the existing App turn lane and failure record. This is a new guarantee to implement: the receiver must synchronously claim/deduplicate `entryId` **before enqueue**, acknowledge duplicate delivery idempotently, and persist accepted ownership with its recovery record. The current promise lane alone is only serialisation; it does not prevent same-tick duplicate events. Ready/ack loss replays acknowledgement, not a second commit/send. A different entry while a turn is busy stays visibly recoverable until accepted or explicitly canceled; it cannot disappear in a busy guard.
- A pre-existing App composer draft is a separate owner, including its files. An incoming source draft must not silently overwrite/merge with it or send its files. A conflict surface lets the visitor keep the existing draft, append the incoming text, or send the incoming question separately while retaining the parked prior draft. Both drafts stay recoverable until that explicit choice.
- The accepted App state contains the complete source draft before attachment or voice activity starts. App closure/reopen does not lose it. Recovery reload opens a recoverable composer after an explicit visitor action, not a paid request.
- Listener installation/teardown must be idempotent under native page loading and any existing page lifecycle. No new global CSS, inline script blob or PHP layout is introduced: binder in the existing tools entry infrastructure, LC semantic trigger attributes, WindPress appearance.

### Attachments and voice

Attachment/nameplate intents open the existing App with the text as a **draft**, not a question already sent. The existing explicit Choose photo/file step is valid after lazy boot, because browser pickers require a visitor gesture. If an already ready picker can be opened synchronously, it uses the same preparation and accepted types. Cancellation leaves text unchanged. A refused file leaves text and accepted files intact with the existing refusal sentence; nothing reaches the model. Files are not serialised into the new small text draft record. Current `useAttachments` is component memory and `failure.ts` stores prepared bytes only after ask/commit; it does **not** already retain an unsent attachment through refresh. Before-send reload recovery must therefore name any previously picked files as requiring selection again and never claim their bytes were sent or retained. Text is recovered; lost files are visible missing-file chips. An implementation choosing full unsent-byte recovery would need an explicitly added draft stage in the existing quota/omitted machinery and its own tests; that is not assumed by this design.

Voice uses the existing `startDictation`, current UI locale and its current error/stop contract. It appends at the captured insertion point in the accepted draft without erasing existing words. A denied/unsupported microphone leaves text editable and explains the existing capability state. Closing/unmounting stops recognition. A dictated phrase becomes a question only after the user presses Send, matching the current App behavior.

Residential controls that are currently disabled are enabled only when these consumers exist. Commercial/Installer enabled controls gain real consumers. Preserving the old nonfunctional disabled state is not the completed repair.

### State table

| State / action | Visible result | Text and files | Turn rule |
|---|---|---|---|
| Editing / capsule | Existing marketing editor; selected capsule prefilled and focused | Exact editable draft, no files yet | No turn |
| Send while cold | Existing dock loading; source button busy for this attempt, correct focus/ARIA | Snapshot retained in source/recovery owner | Pending one attempt |
| Boot succeeds | Current conversation contains original question | Shared failed-turn owner accepts it before source clears | One turn |
| Boot fails | Existing `Genie could not load.` + `Try again` | Original remains and is retryable; no duplicated text | Zero turns |
| Retry boot | Same attempt delivered after ready | Same original; no re-read of edited text as the old attempt | One turn total |
| Upstream/network timeout | Existing failed-turn sentence/retry | Current failure record restores exact field and prepared files | Current retry contract, no double append |
| Truncated successful transport | Existing unfinished-stream recovery | Original stays in thread; recoverable files as existing | Retry existing tail, not a new duplicate user message |
| Attach/picker cancel/refusal | Existing draft/attachment UI | Original retained; refused file not sent | Zero until Send/established confirmed attachment action |
| Dictation denied/canceled | Existing editor and capability state | Existing draft retained | Zero until Send |
| Close / reopen / same-tab refresh | Recoverable accepted draft or current thread | Clear only explicit new conversation/discard or current successful ownership transfer | No automatic retry on page load |

## Installer desktop: an explicit project-note consumer

### No invented extraction

Plain free text is carried verbatim as a project note. **No numbers, phase, backup, postcode or equipment identity are extracted from that text by this repair.** A note containing “SAJ H2-10K, -40 °C, 6000 W” therefore prefills none of the five sizing fields. The original remains visible and editable.

Structured values from an existing SizeHint URL or an explicit field edit have a traceable source and keep current validation. The review surface shows only five rows: postcode, annual household consumption, PV array, grid phase and backup choice. A value is “Carried over” until the user chooses “Use these values”, then “Confirmed”. Missing values are “Not entered”; untouched existing defaults are separately labelled “Default”. Current form defaults such as three-phase/none are disclosed as defaults; they are not presented as information recognised in the original note. Blank Plan navigation remains the ordinary empty Configurator route.

The note review lives with the **existing** residential form, not a competing second sizing form. In production, row edits focus/reflect the real registered form controls. “Use these values” confirms and applies only the displayed structured values; the existing schema remains the calculation validator. A review of partial data never claims a complete plan. Remaining required items link to their form fields. Backup load/hours retain their existing conditional, optional fields and validation; this repair creates no new reserve requirement. Non-sizing model/compatibility/document wishes remain in the project note and can be sent explicitly to the existing same-page Genie helper; they are not treated as already satisfied by a generated design.

The minimal first implementation does not invoke a model just to open a planning page. The existing Genie sizing → SizeHint action remains an additional existing path when a visitor deliberately asks Genie. A future extraction model is outside this repair.

### Handoff, reload, return and language

New same-tab browser record (necessary; does not exist today):

```ts
interface ProjectBriefV1 {
  v: 1;
  id: string;                 // opaque project identity; not authorisation
  text: string;               // plain customer text, exact accepted input
  sourcePath: string;         // same-origin path only
  contextScope: string;        // opaque current principal/session epoch, comparison only
  revision: string;           // changes whenever the note/confirmed inputs change
  confirmed: Partial<SizeHintFields>;
}
```

Use a scoped native Woo-session project-context record as the authoritative cross-page owner; a small `sessionStorage` recovery cache follows the site's same-tab draft convention but is **not authority**. Register staging/readback through the same new native Store API extension needed for draft notes, with an explicit staged-versus-attached state. Staging creates/uses the real guest Woo session before leaving the source; a staged brief is not yet represented as attached to the solution draft or inquiry. Return an opaque `contextScope` bound to the current server principal and session epoch. Do not use a raw user ID or the presence of a local record as ownership. The browser verifies current scope before rendering cached text, so an old tab cannot flash the previous user's note.

Identity transitions are explicit: a verified native guest→login claim may migrate that same guest's server-owned staged/attached context into the authenticated session. Logout, account switching and staff User Switching invalidate the old browser recovery scope immediately; a new principal receives no old raw text/IDs without a verified native transfer. Stale writes are refused and old-scoped local cache is removed or quarantined without rendering. A logged-in REST/admin read with an unrelated guest cookie is not proof of a deliberate guest-to-account transfer. Validate the server principal lineage; only the native authenticated login/verified guest claim can authorise migration, while staff switching or a background principal change must not claim or reveal the former guest context. A failed guest claim retains the unclaimed record for retry; **current `SavedSolutions::claim()` clears its session key before save and can lose a record when save returns 0**, so this full continuity promise requires changing consumption to successful per-record save/readback, with failed records retained. Merely adding a brief property to today's claim path is insufficient. Original text limit is the existing inquiry message limit, **5000 Unicode characters**, not a newly invented service threshold. Do not silently trim/truncate an oversized accepted source note; show its length constraint before leaving the source. No arbitrary retention TTL is introduced. The local recovery cache lasts for the browser tab or explicit project removal; server staged context follows the native Woo session lifetime/claim and explicit removal. A source draft remains recoverable until the new project is explicitly discarded.

Plan snapshots/stages the note in the current native session and verifies an authoritative readback **before** navigating to the existing locale Configurator with an opaque `brief` ID, never raw text in the URL. This ID selects a current-session record; it grants no server ownership. The cache is only used after current-scope verification. Configurator loads/validates it, renders the original text and confirmation surface, and immediately exposes “Project note” as received. Refresh/back restores that same project, note and field state. A new unrelated direct Configurator visit does not silently inherit a previous project's note. The server validates the selected record against the current native principal/session before returning any text. The current Configurator language switch preserves only this recognised brief selector; UI changes language, customer text stays original. A missing/malformed record gets an explicit missing-note state with a return action; it is never represented as a successful transfer. Staging/storage/readback failure keeps the source input and prevents a false success navigation. This is a transaction, not a fire-and-forget URL parameter.

## Follow the original note through every consumer

The note is plain customer context. Existing validated form inputs, including disclosed defaults, are the calculation inputs; raw note text is not. “Note retained” is true only if the named consumer below contains the exact accepted revision. Removing it is an explicit visible user action. A change of note invalidates reuse of a saved/report artifact that described the earlier note revision, just as current design changes invalidate saved results.

### Actual current schemas and gaps

| Current writer/reader, inspected | What exists today | Necessary narrow extension |
|---|---|---|
| `ResidentialInput` (TS/engine Strict schema) | Typed sizing fields; no free note; extra fields forbidden | **No new note in calculation input.** Preserve its current strict shape. |
| Commercial `Site.notes` | 500-character installation-site note specific to commercial input | Do not misuse it for 5000-character cross-page project requirements or residential planning. |
| `api/solutions.ts → SolutionsRoute::create → SavedSolutions` | Client serialises kind/title/input/lines/report; route builds design from kind/input only; private store preserves passed design | Optional top-level `project_brief` in the save body, validated plain text/revision/source metadata; saved in design alongside `input`, not inside it. New getter and current account semantic display must read it. Guest keep/claim retains it. |
| `engine.reportPdf → ReportRequest → report.residential → pdf.render` | Wrapper accepts input/logo only; report has no brief | Optional `project_brief` on the report **wrapper**, never `ResidentialInput`; append an escaped customer-note section to screen report/PDF. The numeric calculation request stays byte-equivalent for the same input. |
| `ReadSolution` | Reads stored `design.input`, re-runs engine; strict output has no note field | Keep engine body unchanged. Do not smuggle raw note into numeric facts. Saved note is shown by its owner in the account; sending it to Genie remains an explicit customer message unless a separately typed quoted-context field is added and reviewed. |
| `store.addAll`, `SavedSolutions::add_to_draft` | Native Woo products/quantities only | Register narrow Store API note extension with native update/readback, and matching saved-solution native writer. No note is inferred from products or declared added before it is read back. |
| Inquiry `Form::summary_note` | Defaults the message to latest Genie note; failed POST fields take priority | Project note has its own visible section; never overwrite the editable customer message or falsify a Genie summary. |
| Inquiry `Sender::request` | Validated message → native order customer note; optional Genie summary meta | Explicit include-project-notes choice sends selected IDs + expected revisions for comparison only. Server verifies them against current Woo-session/owner records, then snapshots the exact reviewed records into private order context. Team inquiry/email reads those exact records; no browser-supplied arbitrary session or solution owner ID. |

Schema proposal for durable context (new, not currently implemented): `project_brief: {v:1, id, revision, text}`. Server-saved context does not need a browser redirect path. `text` is plain text ≤ the existing 5000-character message bound; unknown keys/types rejected, HTML is not executed, backslashes and newlines preserved by normal JSON/WP slashing. IDs/revisions are opaque identities, not authority. A note revision is part of the saved/report cache identity; those artifacts describe a fixed note snapshot. Customer text is not machine-translated. Validation must preserve accepted plain-text characters (including quotes, angle/comparison signs, backslashes and newlines); escape at HTML/PDF/mail rendering rather than stripping meaningful text. A literal `\u003csvg` remains literal text, never reinterpreted or repaired by a slash-removing pass. This schema is reused at save/report/draft/order boundaries, avoiding four unrelated note formats.

### Lifecycle matrix

| Transition | Exact note consumer | What is used for calculation | Failure / discard behavior |
|---|---|---|---|
| Source → Configurator | Owner-scoped staged project record + matching-scope recovery cache → visible Project note + real form confirmation | Existing validated form values, including disclosed defaults | Staging/readback failure stays at source with text; no false success. Missing target record explicitly reported. |
| Refresh / Back / language switch | Same owner-scoped record + revision, selected explicitly; UI follows locale | Form state/review continues | No automatic model call. New project does not inherit old context. |
| Calculate / switch selected hardware | Note remains alongside result/report; current revision follows current design | Same existing schema/engine | Unknown requirements remain labelled, not silently declared fulfilled. Recalculation does not delete the note. |
| Save solution / guest claim | Top-level saved design brief; owner-scoped account display | Stored `input` only reproduces figures | Save only reports complete if note and design persisted together. Guest→account claim retains text. No report blob requirement changes. |
| Screen report / PDF / downloaded saved report | Labelled “Project note from the customer”, plus “This note is not used in the calculation.” | Existing numeric report | Same note revision in screen/PDF/save. Wrap all accepted text, no ellipsis/truncation. PDF generation failure preserves source/retry. |
| Add all → solution draft | Current Woo-session-scoped server context exposed as `extensions.linker-project-notes`, keyed by brief ID/revision; visible LC/WindPress note section | Products/quantities authoritative from Woo | Products can be added while note write fails; report partial outcome and retry **note only** without duplicating lines. Readback proves completeness. |
| Add another project / remove a line | Preserve separate note records; source project/revision visible | Current Woo lines | Different project IDs coexist. The same ID with a newer revision replaces its prior revision only through an expected-revision update; stale writes are rejected. Removing products does not silently destroy useful inquiry context; note has explicit Remove. |
| Saved solution → draft | Owner-checked native saved-solution action transfers its stored note and items through same writer | Existing item authority | Same complete/partial rule, no browser copy of another owner's text. |
| Draft → inquiry form | Visible project-notes section + inclusion checkbox; editable customer message separate | No new calculation | Return/validation failure retains original notes and inclusion choice. Existing Genie summary remains separate. |
| Submit inquiry | Selected IDs and expected revisions compared with authoritative Woo-session notes; exact reviewed snapshot saved privately on order and rendered for team | No note promoted to manufacturer/compatibility fact | If any selected note revision drifted, refuse before creating an order and retain all form inputs. After success remove only consumed identical revisions, never a newer note written by another tab. No mail is needed to prove routing; inspect queued Outbox data in fixtures. |
| Explicit remove/new project/new draft | Visible confirmation/action scoped to selected note/project | — | Explicitly removed context is excluded downstream. Existing saved solution/report is immutable historical evidence, not silently rewritten. |

### Concrete persistence and atomicity choice

Use a commerce-owned **server sidecar keyed by the current native Woo principal/session scope**, exposed only through the native Store API extension. Store the small project-context bag in one non-autoload WordPress option per opaque scope, not inside Woo's whole serialised session blob. This avoids an unrelated native cart request overwriting a note update with an older full-session snapshot. There is no new public post type, custom database table or model store. Guest lifetime/claim follows the native Woo session; expiry cleanup removes corresponding sidecars, and authenticated saved copies live in existing private solution/order records.

A production writer must use an atomic **byte-exact** compare-and-set of the whole context option against its expected stored JSON, followed by cache invalidation/readback. Use binary equality (or an equivalent byte comparison), not a case/accent-insensitive database collation copied from numeric Sequence values. Authoritative readback bypasses the options cache before validating the result. The same repository already uses this database CAS pattern in `Proforma/Sequence.php` because `update_option()` alone cannot implement atomic compare-and-set. Initial creation uses native `add_option()`'s unique key. This is a necessary narrow storage helper, not a claim that current Woo session writes provide CAS. All stage/attach/edit/remove/claim/consume operations go through this one helper. A rejected/stale write returns a visible conflict, never a false saved state.

An inquiry compare-and-snapshot must reserve the selected exact revisions atomically before order creation; another update cannot slip between the check and snapshot. Its final success consumes only those reserved exact revisions, tied to the created inquiry record. A failure before order persistence may release the reservation; after an order exists, transport failure is not evidence that submission failed and must not blindly release it. A subsequent update/new revision must remain unconsumed. No model, email or slow report generation runs inside a database lock/transaction. The immutable note snapshot is stored on the inquiry before the current receive/notification path runs. Tests must interleave two actual requests; an in-process read/compare/write unit test is insufficient. Private ownership is checked from server scope on every reader/writer; a posted scope/id never grants access.

Native Store API choice is based on the installed Woo `woocommerce_store_api_register_update_callback`, `woocommerce_store_api_register_endpoint_data` and `/cart/extensions` route. The proposed namespace is new. Its data is scoped to the same Woo session and nonce/token authority already used by `store.ts`; guest cookie issuance and cross-language readback need real fixtures. Do not use localStorage as a substitute for a real session writer/consumer. Do not overwrite `_linker_genie_summary` with a non-Genie note.

### Inquiry concurrency and note-only requests

The inquiry form renders each selected note ID/revision. Submit carries those references, never authority to read arbitrary IDs. The server compares them against the current native Woo session. Drift or disappearance returns a specific changed-notes state before order creation, preserves customer reply details, editable message and inclusion selection, and requires reviewing the current note before resubmission. A same-note update uses expected revision compare-and-set; separate projects coexist. Success consumes only the exact included revision. A late update cannot be deleted by an earlier in-flight request.

A nonempty included project note counts as a valid inquiry even if all products were removed and the independent message is blank. This is a necessary narrow change to `Sender::request`'s existing empty-cart/empty-message guard. It retains validation, consent and anti-abuse. If the customer excludes/removes all notes while products and message are empty, the existing empty-inquiry recovery applies. The note stays separate from the customer message and Genie summary. Explicitly selected notes are visible before submission, including for no-candidate planning results.

### Interrupted inquiry operation and recovery

Each context-bearing inquiry submission has a server-owned operation identity, scoped to its native principal/session, exact selected note revisions and the reviewed form snapshot. Posted identity is a reference for deduplication, never authority. A changed payload cannot silently reuse an already submitted operation. The durable operation states are reserved → order-created → received → context-consumed, with an explicit pre-create failure state. Client retry/readback resolves this same operation instead of starting a second order merely because the response was lost.

Write the operation identity and exact note snapshot **with the order's initial persistence**, using the current native Woo order creation hook/CRUD seam. This closes the crash window between order creation and writing an external operation→order link: recovery can find the already persisted operation-marked order through native owner-scoped Woo queries. Never accept a posted order ID as permission to recover it. Persisted request/operation identity is not a new public endpoint credential.

- Before any order exists: failure can release/retry the same reserved snapshot without consuming notes.
- After create but before receive: read back the existing operation-marked order and resume its remaining steps. Do not call `create_order()` again. Already allocated receipt/metadata state is not taken a second time.
- After received/status persistence but before response/context consumption: return/resume that same inquiry result, then consume only matching reserved note revisions. A newer revision remains untouched.
- If notification enqueue was interrupted: recover its durable per-order/per-notification identity in the existing Outbox path; retry must not enqueue a second team or customer notification for the same received operation. Current `Sender::receive` performs a status transition and current Outbox is not itself proof of operation-level deduplication. A stable received-order notification key and unique/deduplicated queue claim are a necessary narrow recovery addition if the existing queue cannot provide it. This guarantees no duplicate enqueue; it does not invent exactly-once SMTP delivery after an external mail transport crash.
- A reservation with an existing order is reconciled from durable order/operation state rather than left permanently locked or released solely on a timer. No model, PDF generation or mail transport runs inside a database lock/transaction.

Mandatory real fixtures interrupt after create, after received, and before context consume, then retry: one Woo order, one queued job per intended notification, original user fields intact, current note revisions not accidentally deleted. Also interrupt before create and prove context remains available. These are implementation gates; the memory prototype can only demonstrate the intended state choices.

## Existing inquiry prefill: stale history is not a handoff

The parent observed a native PDP Add for SAJ BU2 followed by an inquiry message containing the previous unrelated AIO3 temperature question. Read-only source attribution:

- `Inquiry/Form::value()` defaults `message` to `summary_note()` whenever there is no failed-POST `flash.fields.message` (including a deliberately blank failed field, which currently wins and must continue to win).
- `summary_note()` calls `linker_genie_inquiry_summary` with conversation 0. `InquirySummary::answer()` chooses the visitor cookie-bound existing conversation without requiring an explicit inquiry handoff or checking draft products.
- Both successful model-summary and rule fallback use the **last customer message** for `note`, capped at 500 characters. Thus this last temperature question can be inserted without any model rewriting. The model summary is a separate field.
- `account-ui.js` owns busy/submit/form helpers; it does not write or persist the inquiry message. `Inquiry/Handler` stores failed POST name/email/company/message in the real Woo session, and Form consumes those flash values first. This is legitimate user draft recovery, not the stale-history cause.
- Native `Sender::request` also asks the current conversation summary when passed null. A blank message alone would not prevent an unreviewed unrelated summary from entering order context. The explicit Genie confirmation card already has a reviewed summary and inclusion checkbox; preserve that behavior.

Necessary prefill contract: an ordinary native PDP/draft/direct inquiry visit begins with the current inquiry draft or an empty message. A prior unrelated Genie question must not silently fill it or attach its summary. Only an **explicit visitor handoff/reviewed inclusion** can supply a Genie-origin candidate. The current Genie card retains its own checked message/summary flow. For its native inquiry fallback, stage an owner-scoped intent from the explicit click with conversation/state reference and current draft identity; the server, not a URL conversation ID, owns the candidate. Changing products/context or editing/clearing the native message invalidates automatic prefill eligibility; the old conversation can remain available as an explicit reviewed attachment, never as a replacement message.

Priority is: (1) failed POST draft, including empty customer-cleared text; (2) current inquiry's deliberately saved unsent draft; (3) an explicit, still-matching handoff candidate **only if no customer edit exists and field is empty**; (4) empty. A handoff never overwrites a customer field. The native sender gets false/no summary unless the visitor reviewed and included eligible context; it must not default to the latest global thread merely because one exists. Project note context remains separate and does not impersonate this Genie intent.

There is currently no general persistent unsent inquiry browser draft mechanism in `account-ui.js`; the new implementation must either retain the existing failed-POST semantics alone or explicitly add an inquiry-identity-scoped draft store/consumer with current-principal checks. Do not describe a nonexistent store as the explanation for this observed message.

Acceptance additions: old AIO3 history → native unrelated BU2 Add yields blank/default user message and no hidden unrelated summary; explicit Genie handoff fills an untouched empty field with the reviewed candidate; an existing nonempty or deliberately cleared user draft survives; failed POST recovery survives; changed context/old intent and cross-user state cannot auto-import; DE/EN and back/reload preserve original customer language and selected inclusion.

## Copy: draft, challenge and final

New copy adds one dimension only: **customer requirement continuity and explicit field confirmation**, not a new product promise. Existing loader errors, retry, assistant name, form field terminology and attachment refusal sentences are reused verbatim from their catalogs. EN is drafted first. DE is written independently with current formal terminology; the original note is not translated.

The first candidate was challenged independently by Spec and Standards reviewers. The explicit failure/confirmation issues and final decisions are recorded below; the prototype is synchronized after both reviews.

| Draft EN | Independent DE candidate | Challenge before final |
|---|---|---|
| Your project is ready to continue. | Ihr Projekt kann fortgesetzt werden. | Rejected: sounds complete even when required fields unknown. |
| We have filled your project details. | Die Projektdaten sind übernommen. | Rejected: plain-text note was not parsed; defaults are not customer facts. |
| Your project note | Ihre Projektnotiz | Keep simple name; no invented product label. |
| Only confirmed fields affect sizing. | Für die Auslegung gelten die bestätigten Angaben. | Rejected: existing default values also affect the normal form; final copy describes the displayed inputs instead. |
| Your note stays with the project and inquiry. | Die Notiz bleibt dem Projekt und der Anfrage zugeordnet. | Must be conditional on implemented full lifecycle and user's include choice. Avoid unconditional statement before durable write. |
| Apply confirmed inputs | Bestätigte Angaben übernehmen | Rejected: confirmation loop; final action is Use these values / Angaben übernehmen. |
| Not entered / Carried over / Confirmed | Noch offen / Übernommen / Bestätigt | Distinguish default assumptions and unknowns. |
| Include project notes with this inquiry | Projektnotizen dieser Anfrage beifügen | Visible user choice; independent from Genie summary checkbox. |
| Project note from the customer | Projektnotiz des Kunden | Export/team label; plain context, not a verified fact. |
| Not used as a calculation input. | Nicht als Berechnungsgrundlage verwendet. | Necessary explicit scope label on note/report. |

### Independent challenge and disposition

Spec review rejected the confirmation loop (“Apply confirmed inputs” before any confirmation), unqualified note-retention promises, unreviewed concurrent note snapshots, and note-only empty-request rejection. The design now uses an explicit “Use these values” gesture, state-based readback success, expected-revision checks, and a valid included-note-only request. These are product-state corrections, not softer wording around a missing consumer. Standards independently verified the real schema limits and additionally required principal/session-epoch isolation, transactional guest claim, explicit missing unsent-file recovery, and synchronous pre-enqueue attempt deduplication; those constraints are now in the design.

Final new product-facing copy (EN first; DE independently written):

| Purpose | Final EN | Final DE |
|---|---|---|
| Note title | Your project note | Ihre Projektnotiz |
| Planning context | Sizing uses the planning inputs shown below. | Die Auslegung verwendet die folgenden Angaben. |
| Note scope | This note is not used in the calculation. | Diese Notiz fließt nicht in die Berechnung ein. |
| Review heading | Details to confirm | Angaben zur Bestätigung |
| Explicit application | Use these values | Angaben übernehmen |
| Missing value | Not entered | Nicht angegeben |
| Carried value | Carried over | Übernommen |
| Accepted value | Confirmed | Bestätigt |
| Existing assumption | Default | Voreinstellung |
| Save/readback success only | Project note saved. | Projektnotiz gespeichert. |
| Include checkbox | Include project notes with this inquiry | Projektnotizen dieser Anfrage beifügen |
| Export/team label | Project note from the customer | Projektnotiz des Kunden |
| Existing App draft | Current unsent draft | Bisheriger ungesendeter Entwurf |
| Incoming source | Question from this page | Frage von dieser Seite |
| Preserve existing draft | Keep current draft | Bisherigen Entwurf behalten |
| Explicit merge | Add to current draft | Zum Entwurf hinzufügen |
| Explicit separate send | Send question separately | Frage separat senden |
| Partial draft | The products are in your solution draft. The project note could not be added. | Die Produkte sind im Lösungsentwurf. Die Projektnotiz konnte nicht übernommen werden. |
| Partial recovery action | Retry note only | Nur die Notiz erneut übernehmen |
| Concurrent change | The project notes have changed. Your other entries are still here. | Die Projektnotizen wurden geändert. Ihre übrigen Eingaben sind erhalten. |
| Concurrent recovery action | Review project notes | Projektnotizen prüfen |
| Source staging error | The project note could not be carried over. Your text is still here. | Die Projektnotiz konnte nicht übernommen werden. Ihr Text ist weiterhin vorhanden. |
| Destination missing | The project note could not be opened. | Die Projektnotiz konnte nicht geöffnet werden. |
| Destination recovery | Back to your entry | Zurück zur Eingabe |

These sentences are state claims: success appears only after its named actual consumer readback; “other entries still here” requires preserved fields in the real validation fixture. Existing loader/turn/attachment failure language and “Ask Genie” remain catalog copy. No marketing headline, product body or commercial promise is rewritten by this scope. Spec reviewed the synchronized design and final EN/DE table and returned **design/copy PASS**, explicitly not implementation or online acceptance. Standards closed the six original design gaps and required the additional interrupted-operation recovery contract above; its final verdict is recorded after that short recheck.

Pre-delivery checklist (independent design/copy review complete; implementation acceptance is separate):
- [x] Encyclopedia loaded: one dimension, tool names match current AGENTS/catalog, no invented category.
- [x] Hard Stops 1–9: no borrowed authority, proof inventory, logistics promise, service reassurance or repair-shop claim.
- [x] Actor/Future/Weight/Duration: no homework body imperative or imagined customer trajectory; state copy describes concrete UI behavior.
- [x] No slogans, banned manufacturer labels or fabricated quotes.
- [x] EN first; DE independently written using existing formal form vocabulary.
- [x] Spec final design/copy PASS; Standards final interrupted-operation recheck is recorded below when complete.

## Delivery batches and closure boundary

The parent may implement/release this in two reviewed batches after the current release is read back:

- **A · Current Genie entry wiring:** Residential/Commercial and Installer mobile, original/next/composer draft ownership, loading/retry/attachment/dictation, exact-once receiving, and the explicitly qualified native inquiry-handoff behavior found during this audit. Current page appearance and planning destination are preserved.
- **B · Installer desktop project context:** real staged note consumer, field review, native-scope sidecar, save/claim/report/draft/inquiry propagation and interrupted-operation recovery. Its entire consumer contract remains mandatory even if A lands first.

Completing A closes only those named entry paths. It does not mark Installer desktop project-note continuity, its schemas, downstream exports or the full-site audit complete. The parent opens/authorises the implementation branch; this design task changes no product source.

## Implementation seams after branch/source authorisation

This is the smallest complete consequence of keeping useful original requirements beyond the initial screen; it is not a visual-only event rename. Implementation should be kept in these explicit modules, with generated schemas/catalog/build outputs regenerated by the existing commands:

1. One current entry binder and typed optional draft/attempt context in Genie loader/App; actual LC trigger markup remains the composition owner. Preserve homepage/product search controllers and one React app. Add receiver claim before enqueue and current-scope draft recovery rather than a second transport.
2. One project-context owner in commerce, registered through installed native Woo Store API extension helpers. It owns staged/attached notes, scope/revision checks, verified native claim, note readback and consumption. The new namespace/schema are explicit additions; no existing `Site.notes` or Genie summary is repurposed.
3. A Configurator note consumer beside the existing form and an Installer Plan binder that stages/readbacks before navigation. Review binds the real form fields; `SizeHint` remains the current five-field source. No arbitrary-text numeric parser is added.
4. Optional brief companion in save/report wrappers and owner-scoped account display; current numeric `ResidentialInput` remains unchanged. Claim is per-record success/readback before removal; PDF/screen rendering escapes and retains the complete note.
5. One draft note writer/readback path shared by current `addAll` and native saved-solution Add, LC semantic context fragments and WindPress styles. Note-only retry never re-adds products.
6. Native inquiry prefill qualification and independent project-note inclusion/revision validation. Preserve user flash/draft priority, current message/Genie summary semantics and anti-abuse. Snapshot selected context before receive/email, consume exact revisions only after success. Outbox assertions suffice for mail-routing tests; no real mail run.

Tests must target actual writer → reader boundaries described above. A source attribute, a dispatch spy, a route that accepts unknown JSON without consuming it, or a matching success string is not closure. Intermediate split commits may aid review, but the final released behavior must carry the full note chain in this same round.

## Executable acceptance, to implement after source authorization

1. Six affected page routes × EN/DE × 1440/390: exact text becomes one current user message and one turn, not merely the right destination URL. Existing ordinary navigation/Home/Products remain regression controls.
2. Cold/warm loader, blocked script/translation/nonce refresh, boot retry, repeated click, IME Enter/Shift+Enter, editable next draft; zero lost or duplicate originals. Specifically warm same-tick duplicate event, ready then lost acknowledgement replay, existing busy turn and different next draft prove synchronous claim before enqueue and one commit/send per attempt. Source reload/back restores a recoverable draft with no automatic paid call.
3. Draft then picker, cancel, refused file, accepted image/PDF, prepare pending, shared turn failure/reload/retry; exact text and available accepted bytes delivered together once. Before-send refresh explicitly shows missing-file/reselect state unless a newly tested byte-retaining draft stage has been implemented; it never sends an attachment claim without bytes. File picker restriction tested as actual browser behavior.
4. Voice capability, allowed result, denied/unsupported, cancel/close, EN/DE locale and append-to-draft behavior; no extra model request until Send.
5. Installer desktop: exact original note visibly consumed; ambiguous equipment/temperature text fills no sizing field. Existing structured SizeHint five-field path prefills accurate values, explicit review edits real form, defaults not misrepresented, unknown fields identified and existing schema validates. Blank navigation unchanged.
6. Same-tab refresh, back, cross-language switch, missing record/storage refusal, two independent project IDs, verified guest claim, failed guest save, logout/login-as-other-user and staff switching with no cached-note exposure. Original note preserved without putting raw text in URL; no indefinite localStorage cache.
7. Result → save → guest claim/account → screen/PDF note → add to real draft/readback → inquiry form/error/received order: exact accepted note revision present at each **actual** consumer. Numeric engine input/output unchanged by note text. Saved/report reuse invalidated by note revision change.
8. Partial item/note write: visible partial outcome; note-only retry does not increment product quantities. Two project notes do not overwrite each other; stale same-ID revisions cannot replace current context. Concurrent inquiry revision drift refuses before order creation, preserves form fields, and success removes only identical consumed revisions. Note-only / no-candidate / excluded-all-empty paths have explicit outcomes. Owner/other customer/guest boundaries hold. Removing notes is explicit and exclusion is visible before inquiry.
9. Customer note + existing user message + Genie summary coexist; no note masquerades as a fact, translation, approved price or consent. Stored/queued inquiry evidence verifies exact included/excluded notes; no real mail test.
10. 1440/390 EN/DE actual screenshots for normal/loading/failure/retry/attachment/voice and planning unknown/confirmed/partial downstream states; long German labels, note wrapping, focus/Esc/return, button hit targets and contrast manually reviewed. Spec + Standards review all source/schema/export changes before release; production acceptance only after parent backup/deploy/readback.

## Prototype decision record

The small in-memory prototype demonstrates the proposed state contract, not persistence or backend implementation. It must show: raw note survives, ambiguous numbers are not extracted, structured five-field data can be confirmed, incomplete fields stay explicit, loader failure/retry keeps the original, picker/voice cancel preserves draft, and the note is still visible in simulated saved/report/draft/inquiry consumers. The final walkthrough manifest is `prototype-review.json`, run `2026-10-21T18-59-27-274Z`, with prototype SHA-256 `e70b09a72e7869ce9ddf0e47c2053554feabf912ed6444fe17977984116d8954`. It contains **26 local memory-only browser walkthrough captures**, EN/DE at 1440/390: no JavaScript errors, no network requests and no horizontal overflow. These are design demonstrations, not API, persistence, ownership, PDF, mail or production acceptance tests. Earlier top-level prototype PNGs/`prototype-walkthroughs.json` and earlier capture directories are iterative drafts; the manifest's immutable run is the current evidence.

The actual focused images inspected include EN1440 and DE390 five-field review (original temperature/model text unchanged, no inferred fields), DE390 load failure/retry, EN390 dictation and DE390 microphone refusal, concurrent note review with retained customer message, and interrupted-operation current-state panels. Long German action text has room to wrap at 390; the note's calculation scope is plain text rather than a static button-shaped pill. The source/page UI in this logic demo is illustrative; implementation keeps the existing LC/WindPress appearance.

Observed in-memory states: repeated delivery commits one question; a distinct next draft commits a second after the first; ambiguous note confirms zero sizing fields; explicit structured fixture confirms five; note-only inquiry reaches the simulated received state, excluded-empty inquiry stays unsent; a stale note rejects before any order; operation recovery stays at one simulated order and one notification claim and preserves a later note revision. Unsent-file refresh retains text and names the missing file for selection again. None of those observations proves the corresponding real consumer has been implemented.


## Batch A implementation notes (acceptance in progress)

The source binder is a new small entry in the existing tools webpack/Assets registration. It binds the current LC editor selectors, leaving all LC visual markup and existing suggestion-prefill listeners intact. No additional LC export is necessary: six published Pages already contain unambiguous semantic source IDs/classes and mode attributes. Ordinary navigation and Installer desktop Plan remain unchanged.

Recovery identity is resolved by a private/no-store `POST /linker-ai/v1/genie/entry-context` under native WP cookie/REST-nonce authentication. The only returned field is a one-way HMAC scope; its inputs are a random same-tab token and either the existing real Genie guest browser key or the current signed-in principal/native auth session token. A missing guest epoch is minted through existing Conversations cookie code. Cookie/token/user identity never appears in the response. Scope is comparison only; it grants no server access and changes on browser-key/user/auth-session changes. Scope mismatch clears the old local record without rendering it; guest→login does not implicitly claim a local unsent draft. Existing native conversation claim is unchanged. Concurrent auxiliary reads coalesce only while pending, preventing a fresh guest's two initial reads minting different browser keys. Each read has the existing auxiliary product-read budget of 5 seconds, independent of the model turn.

The external attempt is synchronously reserved before await/enqueue, then persisted and acknowledged after verified acceptance into the App inbox. Source Send remains busy until that acknowledgement or a visible failure. A recovery/replay never auto-sends. A current composer gets explicit keep/append/separate actions; separate sending parks the previous text/files. Parked files remain memory-owned; after reload only filenames are shown and require selection again. Missing files block sending until selected or explicitly removed. External questions send their own snapshot without access to existing composer uploads. Failed-turn records carry entry ID and scope; the App does not display a scoped failed record before verification.

The existing helper sheet is also the keyboard boundary. Its private DOM dialog boundary includes the LC account-entry row outside the React root. The current 860px sheet breakpoint controls mobile aria-modal, background inert, scroll lock and Tab cycling. Desktop remains nonmodal. Open focuses the editor without writing it or starting dictation. Help disclosure consumes its first Escape; helper/history close follows existing Hide/back behavior. Closing restores only the inert/overflow values this hook owns and returns focus to a valid original trigger only while focus still belongs to the closing surface or has been lost. Source opener references are short-lived DOM references, never serialised.

Additional copy adversarial record, EN first/independent DE:

| Candidate | Challenge | Final EN | Final DE |
|---|---|---|---|
| Restore unsent draft | Do not imply previous draft was sent or discard the current draft; restore swaps recoverable ownership. | Restore unsent draft | Bisherigen Entwurf wiederherstellen |
| File restored | Bytes are not retained for an unsent draft. State the concrete action and filename. | Select %s again before sending. | Wählen Sie %s vor dem Senden erneut aus. |
| Send question separately on attachment conflict | An attachment/voice intent has not asked the model yet. | Open as draft | Als Entwurf öffnen |
| Voice unavailable | Name the actual browser capability and preserve editable text. | Dictation is not available in this browser. You can type your question. | Dieser Browser unterstützt keine Spracheingabe. Sie können Ihre Frage eintippen. |
| Voice could not start | Do not blame the customer or claim audio was sent. | Dictation could not start. You can type your question. | Die Spracheingabe konnte nicht gestartet werden. Sie können Ihre Frage eintippen. |

Spec accepted the additional Batch A copy; its one German revision is “Zum Entwurf hinzufügen”. The approved question/current-draft and keep/separate labels remain. This copy verdict does not imply implementation or browser acceptance. Build, CI and production verification remain parent-owned.

Final review-driven source boundaries before the unified rebuild: all entry-derived ordinary sends and failed retries carry scope and freshly verify it after thread refresh; App and Hero verify shared entry failure before any private text is rendered. Shared-cache reconciliation compares the captured raw record, and an older attempt cannot remove a newer attempt’s record. Attempt claim/park persists one ownership update and checks exact readback before ACK or clearing the previous owner. Missing filenames count as occupied composer state. Restore rechecks the composer epoch, busy state and files after its asynchronous identity check. Loader failure emits a failed ACK so source busy ends. Existing guest browser keys are read without renewing their cookie. The focus boundary follows native closed-details semantics, allowing only the first direct summary when closed. Targeted source checks at this freeze candidate: 33 Vitest files / 311 tests, TypeScript/ESLint, 44 PHP tests / 232 assertions, WPCS for the five changed PHP files and PHPStan for the three changed PHP source files passed. These are source checks; the rebuilt-browser matrix is still pending.

The final restore recheck also distinguishes temporary scope-service failure from a confirmed principal change. Temporarily unavailable comparison keeps text, files and scoped failure ownership; the existing Try again path performs fresh comparison before any transport. Initial hidden-cache recovery has a visible existing error/retry action, rather than requiring reload. A single verified claimComposer seam restores scope and synchronous composer ownership from unsent recovery, scoped failure recovery (even with no separate ENTRY record), parked restore, append and accepted entry. The permanent regression includes parked → conversation switch → restore → ordinary failed Send → other-principal remount with no private paint. Five source counterexamples were recorded red before the fix; the current complete related suite has 311 passing tests.


## Batch A asynchronous recovery write boundaries

| Actual consumer | Await boundary and guards before UI/storage writes | Occupied/new owner result | Permanent regression |
|---|---|---|---|
| App scoped failure mount / showStored | Native thread read then fresh scope, exact failure raw CAS, pending-turn guard; current input/files/missing/busy are read again by offerRecovery | Verified old text/files park atomically beside current draft; no current field write; existing parked slot prevents overwrite | Delayed verified failure → new edited composer; initial failure outage → new text → Retry |
| Unsent entry initialise / recovery Retry | Fresh scope; live guard; current input/files/missing/busy in offerRecovery; Retry rechecks composer epoch and busy after await before showStored | Original and new composer persisted as separate owners; busy defers; no automatic turn | Initial unsent outage → new text → Retry; initial hidden recovery Retry |
| Parked restore | Fresh scope then composer epoch/busy/files check, one persisted owner swap before field/files change | An intervening edit/send leaves the parked owner unchanged | Restore hold → new turn; parked → conversation switch → restore → failed Send → other-principal remount |
| App append / accept | Fresh scope then epoch/input/files/busy, successful combined ownership persistence before ACK/clear | Changed composer remains current and incoming item becomes explicit review | Claim/park quota failure, missing-only occupied draft, same-tick/ACK replay |
| Hero controller auto-open | Fresh scope + raw CAS, stopped guard; lookup failure with the same retained record opens an empty recovery surface | No private text before verification; real controller exposes Retry | actual startHero scoped outage → visible empty recovery → Retry, 0 model sends |
| Hero scoped failure restore | Native session read then fresh scope/raw CAS; pending owner, prompt text/input version and current files/busy checked | Verified old owner parks with current prompt; original current field stays intact; occupied parked slot defers | Delayed startHero lookup → new prompt; 0 sends, old note in recoverable pane |
| Hero explicit parked restore | Fresh scope, input version/text/files/busy checked again, durable pair swap before prompt/files write | Intervening edits defer; an explicit successful restore swaps both owners | Home browser fixture preserves new prompt then explicitly restores old original |
| Shared failure completion / hydration | Exact captured raw record and entry owner compared before reconciliation/removal | A later attempt is untouched by old callback | Delayed old reader/completion preserves newer record |

The current related suite is 33 files / 316 tests PASS. One pre-existing parts-list UI fixture was made deterministic by waiting for its actual Send-enabled preparation state before clicking; finding the filename alone does not prove file bytes are ready. No product timing was weakened. Browser acceptance uses the rebuilt source and remains separate.

The busy preparation branch now retains an explicit unresolved recovery owner, with the existing error and Try again action visible after preparation. Ordinary Send/Retry cannot replace the sole scoped failure record while that ownership decision is unresolved. The regression completes actual FileReader preparation, clicks Send (0 transports and unchanged original failure), retries fresh recovery, then sends the new PDF draft once while the original remains parked. Hero pair swaps include omitted names in owner existence, in-memory next owner and persisted parked owner; restored missing files have existing reselect/Remove controls. Its ordinary entry-derived Send waits for reselect/removal. Final source checks: 33 files / 318 tests PASS, TS and targeted lint PASS.

Both surfaces now reserve an existing scoped failure synchronously at initial mount, before any auxiliary await. That barrier is released by verified restoration/parking, or by a confirmed mismatch whose captured old record is gone and has no newer pending owner; unavailable lookup never releases it. App source entry acceptance alone does not release an older failure owner. An external ask that is temporarily deferred returns false, so the already acknowledged incoming question remains in its durable inbox without a settled ACK. The explicit post-recovery choice sends it once and retains the former owner as parked. Permanent fixtures cover both initial-barrier windows, this accepted-but-unsettled chain and confirmed mismatch → current-principal new Send. Final source candidate: 322 related tests, product SHA recorded in batch-a/source-hashes.json. Independent Spec/Standards review and rebuilt browser acceptance remain separate gates. Unscoped legacy failure records are a separate parent-owned investigation; this batch does not claim complete legacy failure identity isolation.

## Composer visual acceptance increment

The second interaction run (fixed ID `20261021T202455072Z`, local login fixture corrected to an existing local customer) passed all 28 journeys. Reusing that ID replaced the first fixture run’s frames; only the first failure log is retained, not claimed as an immutable original frame set. Visual inspection then independently failed the restored composer: EN desktop and DE phone both had clientHeight 24, scrollHeight 48, line-height 24, overflow hidden and no inline height on the actual remounted node. The value remained complete. The former input-only effect did not remeasure an unchanged input on field remount/open.

The authorized narrow increment uses a callback ref with synchronous old-observer disconnection, actual node/value/visibility layout measurement, width-only ResizeObserver changes and font ready/loadingdone measurement with lifecycle cleanup. It retains the existing six 24px line (144px) ceiling and auto scrolling above it. No owner or recovery logic changed: eighteen of the prior nineteen product source hashes are identical; the App difference is its autosize wiring. Four unit cases cover real ref replacement, opening, width-loop avoidance, fonts and the eight-line cap. Source tests total 34 files / 326 PASS. A permanent real-browser height assertion failed on the old bundle (expected at least 47, actual 24); final visual acceptance requires a fresh UTC run after the reviewed rebuild, including eight-line overflow.


## Native bootstrap failure acceptance increment

The corrected composer build was actually exercised in immutable run `20261021T203334923Z`: 28/28 interactions passed, and the snapshots prove full natural textarea height through the existing 144px cap plus eight-line `overflow:auto`. The 58 original frames are separate from the earlier interaction-only run. Independent image review then found that an unavailable bundle left a bare Retry, no helper Close/Escape, and a retry opener reference that could point to its own subsequently removed button. That visual and keyboard defect required a native bootstrap change, because the missing React bundle cannot own its own failure surface.

Only the existing PHP loader's native fallback changes in this increment. Its semantic header uses existing Genie/Close labels, its actions use the established prompt class, and the parent-owned WindPress rule supplies their appearance independently of the missing app CSS. The entire helper mount, including the LC account row, is the temporary focus boundary. Mobile uses the current 860px sheet breakpoint, native dialog semantics, background inert and scroll restoration; desktop remains nonmodal. Retry releases that boundary before React starts and retains the valid original page opener. The independent workspace has Retry without Close.

Close/Escape cancels this volatile pending delivery intent, including its question and entry dispatch queue, while preserving the page's typed source and durable entry record. A late ready cannot reopen it or send. Plain Open may recover that entry without auto-send; a distinct new source question cannot silently send the closed old intent. The permanent native consumer fixture executes the actual captured PHP inline source under jsdom, rather than a reimplementation: the old staged source fails, and helper/workspace at 1440/390 now pass. Related PHP checks: 45 tests / 236 assertions, PHPCS and PHPStan pass. Four actual browser cases at `20261021T204533930Z` additionally exercised native failed load → Retry → Escape → real late bundle → plain reopen → distinct new question → one explicit send, plus workspace failure/retry. They are diagnostic captures before the final touch-target CSS, not the final visual verdict.

The final acceptance matrix is 32 journeys. Each snapshot also records and checks actual source Send/attachment/voice and attachment Remove target dimensions, the complete expanded Hero follow-up field, nameplate wrapping within the dialog content bounds, and enabled Send icon contrast. Parent-owned stylesheet refinements preserve the resting homepage. Transparent photo-page header language contrast is tracked separately in the full-site review; this batch does not claim whole-page visual perfection or complete ordinary legacy-failure identity isolation.


The final rebuilt-browser run is `20261021T210303171Z` on official WindPress cache `1792616532` / `701525` bytes: **32/32 PASS (1.3m)**, 74 unedited original PNGs and 74 geometry records. `images.json` hashes every original. Per-case results persist independently, so a worker restart cannot erase the test summary. The earlier `20261021T204941107Z` is preserved as 26/32 with exact 43px Installer and low-contrast Hero failures; `20261021T205430972Z` passed its original guards but independently failed visual review for welcome clipping/empty source error, and is not the final visual claim. The actual welcome-origin guard then reproduced both desktop cases red (titleTop430.453px versus required461.5px). Parent-owned safe alignment and source `:empty` styling close those causes without changing the twenty frozen product sources.

The final measurements cover 178 source-target observations at least44×44, 16 attachment Remove observations at least44×44, 144 prompt observations at least44 high, 40 App composer observations (four192px contents correctly scroll inside144px), 12 Hero follow-up fields fully visible at a minimum62px, and enabled/default Send icon contrast at least13.48. Thirty welcome measurements keep their title reachable at scroll origin; all12 visible source errors have content. A separate actual native helper scroll readback awaited the eight-line composer, scrolled the101px welcome viewport through127px to its last44px suggestion, verified the whole button in view, and restored scroll, with zero turn calls. Independent Spec image review is recorded separately from automated PASS.

The full-suite run also exposed a test-registration omission: the pre-existing AssetsTest listed four built entries and had no expectation for `marketing`. The new native DOM binder legitimately depends on `wp-dom-ready` and `wp-i18n`. Only that test now enumerates and asserts it; the correct generic Assets implementation and the twenty product source hashes stay unchanged. The exact test first failed on unexpected marketing registration, then passed one test / fourteen assertions, with PHPCS clean. Full `just test` remains parent-owned; a successful `just check` is not reported as the full suite.


The last pure presentation increment removes the redundant supported-voice paragraph next to its same-named Dictate button. The unavailable paragraph, existing explicit Dictate button, composer microphone, errors and owner/transport code are unchanged. A new real binder→App assertion failed on the old duplicate paragraph and now passes alongside the existing unavailable explanation. Nineteen of twenty product source files are identical; byte comparison proves everything outside App's voicePrompt block identical. Current product aggregate is `38342862231861ddf57a6e8792c04e323e5cddbfaea66fc7f59907f2681a8fd1`; `voice-presentation/App-only.diff` is the exact increment. Another existing entry fixture now correctly classifies `marketing/index.ts` as a DOM script, retaining the complete webpack equality contract rather than mounting it as a React app. All52 tools JS files /451 tests, TypeScript and targeted ESLint pass.

Acceptance combines the adjacent complete32-case run `20261021T210303171Z` (74 original frames, source94d6) with the current-source8-case run `20261021T212024202Z` (24 original frames, all8 PASS20.9s, official cache1792617293/701525). The new8 cover EN/DE×1440/390 both available speech (one visible action label, no duplicate paragraph, no auto-start and actual controlled dictation flow) and explicitly unavailable speech (real Open as draft consumer, exact existing locale explanation, no voice action, preserved question/files/missing owner and zero turn). The first candidate8 run remains archived: its4 unsupported assertions used a shared styling class that matched the old review paragraphs before asynchronous acceptance, causing strict-locator failure. The corrected locator waits for the actual capability copy; no assertion or business behavior was removed. Parent reports complete `just test` exit0 and generated/i18n checks exit0; existing skipped/xfailed/deselected cases are retained in its private logs, not claimed as complete behavioral coverage.

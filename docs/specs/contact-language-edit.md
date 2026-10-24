# Contact language switching preserves the current edit

The real EPC document link reaches the correct Contact source context. After
typing a question and excluding its source, however, the native language link
opens a blank question and checks the source again. Browser Back restores the
original dirty page; that does not preserve the actual translated-page edit.
The existing FormRecovery handles failed POSTs, not this unsent navigation.

Keep the native form, native language URLs, server-normalized public selection,
submission, verification, nonce and failed-POST mechanisms. Load one small
Commerce entry only when the Contact shortcode renders, including its receipt.
No new endpoint, Woo session, automatic submission or remote draft save. No
private question or reply detail in a URL. The markup remains semantic and uses
the existing WindPress form/error/action surface.

Only an explicit unmodified same-tab native EN/DE language click can carry an
edit. Store only message, name, email, company, validated intent, consent boolean
and the actual selection checkbox's checked boolean. Never copy its JSON value,
old titles, action, nonce, proof, request id, password or submission state. The
target rebuilds its selection through the current canonical source/Polylang
mechanism. Active-language clicks retain the current page. Modified clicks,
downloads, external URLs and new tabs keep native behavior.

Use the tab's sessionStorage for one pending record, with the exact normalized
native target URL, a server-owned opaque current WP actor/session comparison and
the current public context's paired source identity and sorted selection. The
context excludes editable intent, language titles and language-specific URLs.
Reuse an already active signed Woo guest session when present; never create one.
A guest without one is isolated by tab storage, not a new server guest identity.
The five-minute bound follows the existing FormRecovery retry lifetime. Read
and remove pending before parsing/validation; expired, malformed, different
identity/context/target state cannot overwrite the form. Referrer availability
is not a prerequisite for keeping an explicit language handoff.

Native server recovery wins as a complete package, including empty values and
false choices. Otherwise restore exact text through value/checked, without
trimming, truncating, HTML insertion or synthetic submission. Respect a target
field that already differs from its native default; if focus is inside the
target form when the late entry arrives, do not overwrite that active edit.
No pageshow reapplication over bfcache-preserved forms. A receipt or native
submit also clears pending. These client values never grant business permission.

After a failed native POST explicitly excluded its source, the removed summary
has no checkbox. Preserve that explicit false even if every text field is then
cleared. Only that removed recovery shape derives its navigation comparison from
the current normalized public URL, matching the native language link; its removed
display stays removed and no private selection JSON is copied to the target.

The existing WindPress Contact volume separates the fallback explanation from
its action with the standard field gap (`--proto-space-4`). The native link stays
inside the card, wraps on phones and retains the existing keyboard focus ring.
The hidden notice remains hidden; no PHP layout or extra CSS channel is added.
Enabled native Contact primary actions use the existing darker teal hover token;
disabled submit controls keep their native state.

If storage fails, intercept only a click that would lose actual entries or a
changed choice. Keep the original page and values, expose the existing error
surface and focus a native noopener new-tab link to the validated language URL.
The new tab opens the other page; it does not claim to carry the edit. An
untouched form still follows its native language link. Without scripts, the
existing form/validation/submission remain native; cross-page unsent-edit
retention is an enhancement and is not claimed without its entry.

Approved fallback notice: “Your entries could not be carried over to the other
language version. They are still on this page.” German: “Ihre Eingaben konnten
nicht in die andere Sprachversion übernommen werden. Sie sind weiterhin auf
dieser Seite vorhanden.” The English action is “Open the German page in a new
tab”; its German counterpart is “Englische Seite in neuem Tab öffnen”, because
each opens the other language. Draft, adversarial review and final wording are
retained with the acceptance evidence.

Verify actual DOM roundtrips, the existing native PHP recovery and scope,
identity/context/expiry/malformed state, empty/false values, target edits,
blocked storage, native modified/new-tab behavior and receipt cleanup. Then
walk the actual EN/DE header/footer language links at1440/390 with known public
fixture text, source inclusion, intent and Back/Forward. Prove the target still
uses its current selection and fresh hidden authorization values. Do not send
an inquiry, register an account, invoke a model or send test mail. Source,
fixtures, browser result, compilation and production acceptance remain distinct.

# Guest account entry copy · 2026-10-18

## Initial drafts

EN: `Create account`. The action opens the existing registration form; it does not submit it, approve an account, reveal net prices or grant access to another account's inquiry.

Independent DE draft: `Konto erstellen`. This is a German action label following the existing `Konto` / `Anmelden` terminology, without an informal form of address. The longer existing registration-page heading `Erstellen Sie Ihr Firmenkonto` remains unchanged.

## Adversarial review

- `Create a partner account` would repeat context and lengthen the mobile entry. `Register` is an existing term, but `Create account` directly names the requested action and is consistent across new entries.
- `Jetzt registrieren` adds urgency without a task need. `Konto erstellen` describes the destination without a marketing promise.
- Registration must not appear to unlock an existing private document or inquiry. Keep the ownership notice and 403 response, and present registration as a separate secondary link. Genie retains its original login instruction.
- Neither label claims immediate approval or prices. The inquiry form continues to say that no account is needed.
- Existing sign-in, registration and password-reset wording is retained except the empty draft's combined `Sign in or register`, which becomes the two actual destinations. The nonempty draft summary reuses the same reviewed `Create account` label while retaining its existing no-account-needed and approval explanation.

## Final copy

| EN | DE | Destination |
|---|---|---|
| Create account | Konto erstellen | Native `register` endpoint of the request-language account page |
| Sign in | Anmelden | Existing request-language account page |

No new promises, account conditions, email text, product facts or model-generated wording.

## Owner-requested helper footer correction

EN draft: “Genie is AI” and “More”. Rejected in self-review: the first is vague
about role; the second hides the purpose of the menu. Revised EN draft:
“Genie is an AI assistant.” and “Help & privacy”.

Independent DE draft, using existing terms and the actual menu contents:
“Genie ist ein KI-Assistent.” and “Hilfe & Datenschutz”. No Sie address is
needed for either label; “Datenschutz” names the existing policy destination.

Independent adversarial review (Spec review agent): both pairs are clear,
idiomatic and free of accuracy, approval or unsupported capability promises.
Help covers FAQ/downloads and contact; privacy covers the policy. The control
does not imply a privacy setting or a live human conversation. Both approved.

Final: **Genie is an AI assistant. / Genie ist ein KI-Assistent.** and
**Help & privacy / Hilfe & Datenschutz**. The full existing introduction remains
inside the native details menu with the three original localized routes. No
existing FAQ/contact/privacy label or destination is rewritten.

## Owner-expanded Genie reply presentation — final copy

Boundary: the owner explicitly requests simulated dynamic thinking/loading and
progressive answer presentation in the frontend, retaining the existing backend.
EN draft and independently written formal German were reviewed by the Spec
reviewer. Four pairs passed; the failure instruction was revised because merely
selecting text does not copy it.

| EN final | DE final | Adversarial result |
| --- | --- | --- |
| Show full response | Vollständige Antwort anzeigen | Describes revealing an already received answer; no backend streaming claim. |
| Jump to latest | Zur neuesten Nachricht | Explicit user action; long replies retain the reading position. |
| Copy response | Antwort kopieren | Copies the complete original answer, including during local reveal. |
| Copied | Kopiert | Success only after clipboard resolution; response identity resets state. |
| Copy failed. Select the text and copy it manually. | Kopieren fehlgeschlagen. Markieren Sie den Text und kopieren Sie ihn manuell. | Replaces draft “Select the response to copy it.” Selection alone is insufficient. |

Existing “Genie is thinking…” / “Genie denkt nach…” remains the waiting label.
The owner expressly asks for this simulated thinking state to be dynamic: a
breathing dot, moving text highlight and animated placeholder lines run during
the request. Reduced motion keeps those elements static and displays complete
answers immediately. No tool activity, elapsed progress percentage or backend
reasoning is invented.

## Review round 2: compact comparison actions (2026-10-18)

EN draft: use the existing reviewed **Sign in** and **Create account** under the
Net price row. DE independently selects **Anmelden** and **Konto erstellen**,
consistent with the site's existing account controls. The full existing
“Net price after partner sign-in / Nettopreis nach Partner-Anmeldung” explanation
is retained in the sign-in link's accessible label, after its visible label.

Adversarial check: shortening the pricing sentence could lose the context that
prices require an account. The row's Net price / Nettopreis label and the
accessible explanation retain that context; both visible actions remain direct
links to their own language's native endpoint. No registration promise, approval
claim, new term or marketing sentence is introduced. Final: retain those two
existing reviewed pairs.

## Round 2 follow-up labels (same #223 scope)

EN draft: “Next steps” over answer options. Adversarial review: not every
backend `ask` is a step; it can be a choice that decides product matching.
Final: reuse the existing “Grid connection” term when the structured field is
`phase`; otherwise use the neutral “Continue with your project”. No model
question, option, product claim or destination is rewritten.

Independent DE draft: “Netzanschluss” for `phase`, “Weiter mit Ihrem Projekt”
for other deciding questions. Review: formal address is retained, and the
label must not imply that a solution has already been selected. Final retains
these two labels. “Netzanschluss” is already the approved Configurator term;
its existing PO entry now serves both apps. Document cards retain the
server-hydrated document title and page; their icon/arrow is decorative.


## Owner correction: immediate reply choices and generated Markdown

EN draft: “Choose an option” with an arrow. Adversarial feedback: a quiet
border and navigation arrow do not make the operation clear; the customer
needs to know that clicking sends a reply immediately, rather than selecting
something for later confirmation. Final: **Reply with an option**;
**Your selection is sent to Genie.** Each true button retains its original
option as its accessible name and shows the existing **Send** action label.
The field label (Grid connection / Continue with your project) remains useful
context, below the operation heading.

Independent DE draft: **Antwort auswählen**; **Ihre Auswahl wird an Genie
gesendet.** Review: explicit immediate effect, formal Sie, no implied approval,
no invented model ability, and no unnecessary “Schnell…” claim. Final retains
these two lines and the established **Senden** term. The independent Standards
review found their meaning accurate. Actual option text is sent unchanged.

The owner explicitly approved changing only the system prompts' presentation
format contract. EN draft and independently written DE contract request topical
Markdown headings, bullets for needed project details, sparse emphasis, and
preserved blank lines. Adversarial checks: formatting must not introduce
numbers through ordered list prefixes, change exact guest-status wording,
expand the brief sizing/handoff answers, replace structured actions/cards,
or add facts just to fill headings. Final contracts explicitly retain those
constraints. This is a formatting instruction, not prewritten customer answers.
Actual EN/DE generated replies and raw streams are in `replies-real/`.

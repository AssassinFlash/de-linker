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

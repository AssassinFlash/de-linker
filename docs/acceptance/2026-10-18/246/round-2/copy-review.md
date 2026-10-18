# Receipt cap: EN first, independently written DE

Brief: a saved inquiry always reaches the team notification path. When the site's public-door receipt allowance is exhausted, only the automated customer receipt is omitted. The success screen must acknowledge the saved message, disclose the missing receipt, and retain the one-business-day reply promise. No quota explanation belongs in the customer flow.

## English

Draft: “Your inquiry is received. Your confirmation email is unavailable. Our team will reply soon.”

Adversarial review: “unavailable” suggests a broken service and does not say whether an email was sent. “Soon” weakens the owner's explicit one-business-day promise. Reuse the existing received title and promise on the Proforma page, and change only its reply paragraph. The contact state must remain a success state and acknowledge that the message reached the team.

Final, Proforma reply paragraph (the existing title and promise remain):

> We have not sent a confirmation email. The Linker team will reply to the email address you provided.

Final, contact success:

> Thank you. Your message is with the Linker team. We have not sent a confirmation email. We reply within one business day.

The notice describes an omitted automated receipt, without claiming a delivery failure or refusing the inquiry. It does not promise that an automated email will follow later.

## Deutsch, eigenständig aus dem Brief verfasst

Entwurf: „Ihre Nachricht wurde gespeichert. Die automatische E-Mail entfällt. Wir melden uns zeitnah.“

Gegenprüfung: „gespeichert“ beschreibt eine technische Handlung und lässt offen, ob die Anfrage beim Team angekommen ist. „entfällt“ klingt wie eine dauerhafte Änderung. „zeitnah“ nennt die zugesagte Frist nicht. In der Anfragebestätigung stehen Eingang und Frist bereits oberhalb des Antwortabsatzes. Im Kontaktformular müssen beide Aussagen vollständig bleiben. Sie-Ansprache und bestehende Begriffe werden beibehalten.

Endfassung, Antwortabsatz der Anfragebestätigung:

> Es wurde keine Bestätigungs-E-Mail versendet. Das Linker-Team antwortet an die angegebene E-Mail-Adresse.

Endfassung, Kontaktbestätigung:

> Ihre Nachricht ist beim Linker-Team eingegangen. Eine Bestätigung per E-Mail wurde nicht versendet. Sie erhalten innerhalb eines Arbeitstags eine Antwort.

Keine technischen Details zur Begrenzung, kein Verweis auf einen Fehler und keine Aufforderung zum erneuten Absenden. Die Anfrage bleibt angenommen.

## Optional-name mail, review consequence

Spec review found the new hand-off could emit “Hello ,” and an empty team sender. EN draft: “Hello visitor,” / “New inquiry #… from an unnamed visitor.” Review: both invent a customer label when we already know the real reply address. Final EN salutation: **“Hello,”**; team line: **“New inquiry %1$s from %2$s.”** The subject keeps its existing wording and uses the actual reply email when company/name are both absent. Named customers retain the existing copy.

Deutsch, eigenständiger Ansatz: „Sehr geehrte Kundin, sehr geehrter Kunde,“ und „Neue Anfrage … von einem Besucher“. Gegenprüfung: Das setzt eine Kundenbeziehung bzw. eine neue Personenbezeichnung voraus. Ohne Namen reicht die übliche neutrale Anrede. Endfassung: **„Guten Tag,“**; interne Zeile: **„Neue Anfrage %1$s von %2$s.“** Für die Zuordnung wird die bekannte Antwortadresse genutzt; keine leeren Klammern und kein erfundener Name. Die bestehende Betreffzeile bleibt, ihr Absenderplatzhalter erhält Firma, Name oder die tatsächliche E-Mail-Adresse.

## Visibility correction after browser review

The existing mobile design hides the Proforma `linker-next-steps` paragraph. The receipt disclosure is therefore its own sentence **inside the LC success panel**, after the reply promise: EN “We have not sent a confirmation email.” / DE “Es wurde keine Bestätigungs-E-Mail versendet.” The existing reply paragraph stays unchanged. Same reviewed meaning and wording; no new promise. The empty disclosure is hidden by WindPress's `empty:hidden` class for the ordinary success state. A real-browser visibility assertion, rather than a text-in-DOM assertion, covers EN/DE at both widths.

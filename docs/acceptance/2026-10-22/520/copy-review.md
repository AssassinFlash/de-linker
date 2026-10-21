# Public protection copy review

Scope: customer verification, retry, draft preservation and optional confirmation email. EN source and formal DE catalog are delivered together. Authority: existing contact/inquiry wording, the one-business-day owner commitment, AGENTS customer terminology and linker-copywriting Hard Stops. No product, delivery, compatibility or approval promise is added.

## Initial draft and critique

The first draft used a single verification failure and the old generic contact throttle message. Critique: it did not distinguish expired proof from service outage, did not tell customers their fields/draft survived, and could encourage retry after a side effect whose result was unknown. A reflected confirmation email would copy a spammer's arbitrary name, message or URL to an unverified target.

The first generic receipt wording addressed the email recipient as the submitter. Critique: address ownership is unverified, so acknowledge a message addressed to the team without asserting that the recipient sent it. Do not claim queued mail was delivered. Received states must follow native business save, not a model result.

## Final wording

| State | EN final | DE final |
| --- | --- | --- |
| Expired proof | Verification expired or could not be confirmed. Your entries are still here. Please try again. | Die Sicherheitsprüfung ist abgelaufen oder konnte nicht bestätigt werden. Ihre Angaben bleiben erhalten. Bitte versuchen Sie es erneut. |
| Service outage | Verification is temporarily unavailable. Your entries are still here. Please try again or email sales@de-linker.com. | Die Sicherheitsprüfung ist vorübergehend nicht verfügbar. Ihre Angaben bleiben erhalten. Sie können es erneut versuchen oder uns unter sales@de-linker.com schreiben. |
| Message allowance | The message limit has been reached. Your entries are still here. You can try again later or email sales@de-linker.com. | Die Nachrichtenbegrenzung ist erreicht. Ihre Angaben bleiben erhalten. Sie können es später erneut versuchen oder uns unter sales@de-linker.com schreiben. |
| Draft unchanged | Verification could not be completed. Your solution draft is unchanged. Please try again. | Die Prüfung konnte nicht abgeschlossen werden. Ihr Lösungsentwurf bleibt erhalten. Bitte versuchen Sie es erneut. |
| Draft changed | Your solution draft changed. Please review it and send your inquiry again. | Ihr Lösungsentwurf hat sich geändert. Bitte prüfen Sie die Produkte und senden Sie Ihre Anfrage erneut. |
| Duplicate operation | This request has already been processed. Please check the result before sending it again. | Diese Anfrage wurde bereits verarbeitet. Bitte prüfen Sie den bisherigen Vorgang, bevor Sie sie erneut senden. |
| Fixed optional receipt | We received a message addressed to the Linker team. We reply within one business day. | Beim Linker-Team ist eine Nachricht eingegangen. Wir antworten innerhalb eines Werktags. |

Other prompts name the actual registration/request/comment verification, refresh or sign-in action. JavaScript fallback gives the same public team address. DE uses Sie and Lösungsentwurf/Anfrage; EN uses solution draft/inquiry. No country, language, email-provider or AI risk accusation appears. Complete literals are in the source and native PO/JSON catalogs.

The author critique and revisions are recorded above. Independent Spec/Standards review must also assess these promises; findings go in review.md when returned. This document alone is not an independent review claim.

## Independent critique: unverified registration recipient

Spec review found that the first implementation neutralized inquiry receipt
copy while leaving registration's “your partner registration/account”. This
did not meet the same unverified-recipient contract. Enforce now uses the
existing neutral subject “Registration received” / “Registrierung eingegangen”.
The fixed opening is “A partner registration was submitted using this email
address.” / “Über diese E-Mail-Adresse wurde eine Partnerregistrierung
eingereicht.” It describes review of company details and price access after
approval without asserting that the addressee submitted anything. “If you did
not submit this registration, you can ignore this email.” / “Falls Sie diese
Registrierung nicht eingereicht haben, können Sie diese E-Mail ignorieren.”
No supplied company, person, message or link appears in these fixed paragraphs.
Native rendered-email assertions exercise the actual template.

# #245 · Admin access explanation copy

Source: owner ruling 2026-10-17, issue #245. EN drafted first. DE composed separately for formal Sie usage and the existing “Mein Konto” vocabulary. The implementation draft and challenge are below; Claude's independent round-1 copy decisions are recorded after the table.

| Element | Initial EN | Challenge | Final EN |
| --- | --- | --- | --- |
| Heading | Access denied | Sounds like a broken account; it is a staff-only area. | Linker staff only |
| Identity | You are signed in as %s (customer account). | Keep the email visible so staff using a customer session can recognise it. Escape the value. | You are signed in as %s (customer account). |
| Explanation | You cannot access this area. | State who the area is for, without implying approval changes access. | The admin area is for Linker staff only. |
| Primary action | Staff login | Must disclose that the current session is signed out. | Sign out and sign in as staff |
| Secondary action | Return | Name the destination. | Go to my account |

Independent DE draft and challenge:

| Element | Initial DE | Challenge | Final DE |
| --- | --- | --- | --- |
| Heading | Kein Zugriff | Does not explain the role boundary. | Bereich für Linker-Mitarbeitende |
| Identity | Angemeldet: %s | Missing account type; formal address should read naturally. | Sie sind mit Ihrem Kundenkonto %s angemeldet. |
| Explanation | Nur Mitarbeiter haben hier Zugriff. | “hier” is vague; use a precise destination and inclusive staff wording. | Der Verwaltungsbereich ist ausschließlich für Linker-Mitarbeitende vorgesehen. |
| Primary action | Zum Mitarbeiter-Login | Conceals sign-out. | Abmelden und mit einem Mitarbeiterkonto anmelden |
| Secondary action | Mein Konto | Express the navigation action. | Zu meinem Konto |

Checks: no approval promise, no support or commercial claim, no invented next step, no old domain vocabulary, no three-part slogan, no contrastive AI sentence. Both languages expose the same two actions. Email is a placeholder rendered from the authenticated user, never from the request.

## Independent review by Claude · PR #293 round 1

[Review decision](https://github.com/AssassinFlash/de-linker/pull/293#issuecomment-6239365278).

| Text | Independent challenge | Final decision |
| --- | --- | --- |
| `Sie sind mit %s als Kundenkonto angemeldet.` | Equates the email with the account. | `Sie sind mit Ihrem Kundenkonto %s angemeldet.` |
| `Abmelden und als Mitarbeitende anmelden` | Uses a plural/neutral noun with a singular formal subject. | `Abmelden und mit einem Mitarbeiterkonto anmelden` |

EN remains finalised. The German heading `Bereich für Linker-Mitarbeitende`, the explanation and the account action remain unchanged. The two revised German strings are the independent review's final wording, not a new implementation-session rewrite.

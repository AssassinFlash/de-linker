"""Plan the reviewed EN/DE website quotation copy from native WordPress content.

Run with --wp and a WP-CLI prefix to print a read-only diff. Import plan_pair
and pass its changed payload to reviewed_page_pair.invoke after approval and
backup. The existing wrapper locks both full page preimages and translation
metadata and adopts the reviewed German baseline in the same transaction.
"""

from __future__ import annotations

import argparse
from typing import Any

import reviewed_page_pair

EN_GUEST = (
    "You can send an inquiry or request a Proforma invoice without an account.",
    "You can request a quotation or send us a message without an account.",
)
DE_GUEST = (
    "Auch ohne Konto können Sie eine Anfrage senden oder eine Proformarechnung anfordern.",
    "Auch ohne Konto können Sie ein Angebot anfordern oder uns eine Nachricht senden.",
)

CAPABILITY_DE_BEFORE = "Wir prüfen die verfügbaren technischen Daten mit Ihnen, um die passende Konfiguration vor der Auftragsbestätigung einzugrenzen."
EPC_DE_ADJUSTMENT_BEFORE = "Wenn sich die Standortbedingungen ändern, bevor der Auftrag in die Produktion freigegeben wird, lässt sich die Konfiguration noch ändern."


def order_wording(before: str, after: str) -> tuple[str, str, str]:
    """The published quotation revision still carries this older order wording."""
    return before, after, before


# Each native post_content fragment lists its original and final text. A third
# value records the exact previous candidate where it differs from the final.
REVISIONS = {
    (1674, 6825): (
        (
            EN_GUEST,
            (
                "You can use your Solution draft to send a product inquiry or request a Proforma invoice. Our team prepares your quotation and handles any subsequent order with you.",
                "You can use your Solution draft to send a product inquiry. Our team prepares your quotation. Order confirmation, invoicing and payment take place outside the website.",
            ),
            (
                "Applicable VAT is stated in your quotation or Proforma invoice.",
                "Your quotation shows the applicable VAT.",
            ),
            (
                "Bank details are provided with the order documents.",
                "You will find the bank details for payment only on the formal invoice our team issues outside the website.",
            ),
            order_wording(
                "Invoices, Proforma invoices and related order documents are issued electronically and sent by email",
                "Invoices and related order documents are issued electronically and sent by email",
            ),
            order_wording(
                "Where a parcel charge can be calculated reliably, it is stated in the quotation or Proforma invoice.",
                "Where a parcel charge can be calculated reliably, it is stated in the quotation.",
            ),
            order_wording(
                "Linker confirms the freight charge on the Proforma invoice, and nothing is payable until the Proforma total is complete.",
                "Linker confirms the freight charge in the order documents, and no payment is due until the full order total, including freight, is confirmed.",
            ),
        ),
        (
            DE_GUEST,
            (
                "Im Lösungsentwurf stellen Sie die gewünschten Produkte zusammen, um eine Anfrage zu senden oder eine Proformarechnung anzufordern. Unser Team erstellt Ihr Angebot und stimmt die weitere Auftragsabwicklung mit Ihnen ab.",
                "Über den Lösungsentwurf können Sie die gewünschten Produkte anfragen. Unser Team erstellt Ihr Angebot. Auftragsbestätigung, Rechnungsstellung und Zahlung erfolgen außerhalb der Website.",
            ),
            (
                "Die geltende Mehrwertsteuer wird im Angebot oder in der Proformarechnung ausgewiesen.",
                "Die geltende Mehrwertsteuer weisen wir im Angebot aus.",
            ),
            (
                "Die Bankverbindung wird mit den Auftragsunterlagen mitgeteilt.",
                "Die Bankverbindung für Ihre Zahlung steht ausschließlich auf der Rechnung, die unser Team außerhalb der Website ausstellt.",
            ),
            order_wording(
                "Rechnungen, Proformarechnungen und zugehörige Auftragsunterlagen werden elektronisch erstellt und per E-Mail bereitgestellt",
                "Rechnungen und zugehörige Auftragsunterlagen werden elektronisch erstellt und per E-Mail bereitgestellt",
            ),
            order_wording(
                "Sofern sich die Kosten für den Paketversand zuverlässig berechnen lassen, werden sie im Angebot oder in der Proformarechnung ausgewiesen.",
                "Sofern sich die Kosten für den Paketversand zuverlässig berechnen lassen, werden sie im Angebot ausgewiesen.",
            ),
            order_wording(
                "bestätigt Linker die Frachtkosten auf der Proformarechnung. Eine Zahlung ist erst fällig, wenn der Gesamtbetrag der Proformarechnung vollständig feststeht.",
                "bestätigt Linker die Frachtkosten in den Auftragsunterlagen. Eine Zahlung ist erst fällig, wenn der Gesamtbetrag einschließlich Frachtkosten feststeht.",
            ),
        ),
    ),
    (1038, 6698): (
        (
            EN_GUEST,
            order_wording(
                "contact Linker with the Proforma number before the goods are used or installed.",
                "contact Linker with the order number before the goods are used or installed.",
            ),
            order_wording(
                "Contact Linker with the Proforma number before sending anything back",
                "Contact Linker with the order number before sending anything back",
            ),
        ),
        (
            DE_GUEST,
            order_wording(
                "kontaktieren Sie Linker unter Angabe der Proformanummer, bevor die Ware verwendet oder installiert wird.",
                "kontaktieren Sie Linker unter Angabe der Bestellnummer, bevor die Ware verwendet oder installiert wird.",
            ),
            order_wording(
                "und benachrichtigen Sie Linker mit Fotos und der Proformanummer.",
                "und benachrichtigen Sie Linker mit Fotos und der Bestellnummer.",
            ),
            order_wording(
                "Kontaktieren Sie Linker unter Angabe der Proformanummer, bevor Sie etwas zurücksenden",
                "Kontaktieren Sie Linker unter Angabe der Bestellnummer, bevor Sie etwas zurücksenden",
            ),
        ),
    ),
    (28, 6907): (
        (
            (
                "Our team can confirm product availability and assist with datasheets, installation manuals and Proforma requests.",
                "Our team can confirm product availability and assist with datasheets, installation manuals and quotation requests.",
            ),
        ),
        (
            (
                "Unser Team beantwortet Fragen zur Verfügbarkeit, zu Datenblättern und Installationsanleitungen und bearbeitet Ihre Proforma-Anfrage.",
                "Unser Team beantwortet Ihre Fragen zur Verfügbarkeit, zu Datenblättern und Installationsanleitungen und bearbeitet Ihre Angebotsanfrage.",
            ),
        ),
    ),
    (862, 6865): (
        (
            (
                "Our team prepares your Proforma and handles the commercial terms with you.",
                "Our team prepares your quotation and discusses the commercial terms with you.",
            ),
        ),
        (
            (
                "Unser Team erstellt Ihre Proformarechnung und regelt die kaufmännischen Bedingungen mit Ihnen.",
                "Unser Team erstellt das Angebot und stimmt die kaufmännischen Bedingungen mit Ihnen ab.",
            ),
        ),
    ),
    (874, 6919): (
        (
            (
                "We review the available technical data to help narrow the configuration before the Proforma is issued.",
                "Before we prepare your quotation, we review the available technical data with you to narrow down the configuration.",
                "We review the available technical data with you to narrow down the configuration before order confirmation.",
            ),
        ),
        (
            (
                CAPABILITY_DE_BEFORE,
                "Bevor wir Ihr Angebot erstellen, prüfen wir mit Ihnen die verfügbaren technischen Daten und grenzen die Auswahl passender Konfigurationen ein.",
                CAPABILITY_DE_BEFORE,
            ),
        ),
    ),
    (842, 6867): (
        (
            (
                "Equipment ships on the delivery date confirmed with the Proforma.",
                "Equipment ships according to the delivery arrangements agreed for the order.",
            ),
            (
                "The configuration stays flexible until the Proforma is issued.",
                "The configuration remains flexible while we prepare your quotation.",
            ),
            (
                "If site conditions change before the Proforma is issued, the configuration can still be changed.",
                "If site conditions change while we prepare your quotation, we can still adjust the configuration.",
            ),
        ),
        (
            (
                "Die Geräte werden am mit der Proformarechnung bestätigten Lieferdatum verschickt.",
                "Der Versand richtet sich nach den Liefervereinbarungen zum Auftrag.",
            ),
            (
                "Die Konfiguration bleibt flexibel, bis die Proformarechnung ausgestellt wird.",
                "Während der Angebotserstellung bleibt die Konfiguration flexibel.",
            ),
            (
                EPC_DE_ADJUSTMENT_BEFORE,
                "Wenn sich die Standortbedingungen während der Angebotserstellung ändern, können wir die Konfiguration noch anpassen.",
                EPC_DE_ADJUSTMENT_BEFORE,
            ),
        ),
    ),
    (826, 6869): (
        (
            (
                "Warehouse stock in Germany, confirmed delivery dates, and project documentation with your inquiry.",
                "Warehouse stock in Germany, project documentation for your inquiry, and delivery planning for your order.",
            ),
            (
                "Our team prepares the quote and prepares the Proforma with you.",
                "Our team prepares your quotation and works with you on any subsequent order.",
            ),
            ("Proforma &amp; Delivery", "Quotation &amp; Delivery"),
            (
                "STAGE 04 · PROFORMA &amp; DELIVERY",
                "STAGE 04 · QUOTATION &amp; DELIVERY",
            ),
            (
                "Inquiries are checked against stock in Germany and confirmed with a proforma invoice and delivery date.",
                "We check availability against our stock in Germany and prepare your quotation. We discuss estimated delivery dates with you for each order.",
            ),
            (
                "Once the proforma invoice is confirmed, you receive a delivery date based on current availability.",
                "We give you an estimated delivery date for your order based on current availability.",
            ),
        ),
        (
            (
                "Lagerbestand in Deutschland, bestätigte Liefertermine und Projektdokumentation zu Ihrer Anfrage.",
                "Lagerware in Deutschland, Unterlagen zu Ihrer Anfrage und Lieferplanung für Ihren Auftrag.",
            ),
            ("Proforma &amp; Lieferung", "Angebot &amp; Lieferung"),
            ("PHASE 04 · PROFORMA & LIEFERUNG", "PHASE 04 · ANGEBOT & LIEFERUNG"),
            (
                "Anfragen werden gegen den Lagerbestand in Deutschland geprüft und mit Proformarechnung sowie Lieferdatum bestätigt.",
                "Für Ihr Angebot prüfen wir die Verfügbarkeit im deutschen Lager. Den voraussichtlichen Liefertermin besprechen wir mit Ihnen zum jeweiligen Auftrag.",
            ),
            (
                "Sobald die Proformarechnung bestätigt ist, erhalten Sie ein Lieferdatum auf Basis der aktuellen Verfügbarkeit.",
                "Den voraussichtlichen Liefertermin für Ihren Auftrag nennen wir Ihnen anhand der aktuellen Verfügbarkeit.",
            ),
        ),
    ),
    (749, 6923): (
        (
            (
                "Proforma &amp; availability</span>",
                "Quotation &amp; availability</span>",
            ),
            ("Proforma &amp; availability</h3>", "Quotation &amp; availability</h3>"),
            (
                "Your inquiry is checked against stock in Germany, and you receive a proforma invoice with a delivery date you can plan around.",
                "We check availability in our German warehouse and prepare your quotation. We discuss the expected delivery date with you when arranging the order, so you can plan the installation.",
            ),
        ),
        (
            (
                "Proforma &amp; Verfügbarkeit</span>",
                "Angebot &amp; Verfügbarkeit</span>",
            ),
            ("Proforma &amp; Verfügbarkeit</h3>", "Angebot &amp; Verfügbarkeit</h3>"),
            (
                "Ihre Anfrage wird gegen den Lagerbestand in Deutschland geprüft, und Sie erhalten eine Proformarechnung mit einem Lieferdatum, mit dem Sie planen können.",
                "Wir prüfen die Verfügbarkeit im deutschen Lager und erstellen Ihr Angebot. Bei der Auftragsabstimmung nennen wir Ihnen den voraussichtlichen Liefertermin für Ihre Installationsplanung.",
            ),
        ),
    ),
    (1755, 6917): (
        (
            (
                "Linker delivers a project quote detailing equipment scope, pricing, warranty coverage, and a delivery schedule confirmed in the Proforma.",
                "Your project quotation lists the equipment and prices for your storage system. We work out the delivery schedule with you when arranging the order.",
                "Linker prepares a project quotation covering equipment scope, pricing and warranty coverage. We discuss the delivery schedule with you for the order.",
            ),
        ),
        (
            (
                "Linker liefert ein Projektangebot mit Geräteumfang, Preisgestaltung, Garantieabdeckung und einem in der Proformarechnung bestätigten Lieferplan.",
                "Ihr Projektangebot führt die Geräte und Preise für Ihr Speichersystem auf. Den Lieferplan stimmen wir bei der Auftragsabwicklung mit Ihnen ab.",
                "Im Projektangebot legt Linker den Lieferumfang, die Preise und die Garantieleistungen dar. Den Lieferplan stimmen wir mit Ihnen zum Auftrag ab.",
            ),
        ),
    ),
    (1673, 6827): (
        (
            (
                "inquiry documents (proforma, invoice). Used to answer inquiries, issue Proformas and meet statutory bookkeeping duties.",
                "inquiry documents (including quotations) and invoices. Used to answer inquiries, issue quotations and meet statutory bookkeeping duties.",
            ),
            order_wording(
                ") before the Proforma is issued, we record the declaration text version",
                "), we record the declaration text version",
            ),
        ),
        (
            (
                "Anfragedokumente (Proforma, Rechnung). Verwendet zur Beantwortung von Anfragen, zur Ausstellung von Proformarechnungen und zur Erfüllung gesetzlicher Buchführungspflichten.",
                "Anfrageunterlagen (einschließlich Angeboten) und Rechnungen. Die Daten dienen der Beantwortung von Anfragen, der Erstellung von Angeboten und der Erfüllung gesetzlicher Buchführungspflichten.",
            ),
            order_wording(
                "Wenn Sie vor Ausstellung der Proformarechnung den deutschen 0 %-Umsatzsteuersatz",
                "Wenn Sie den deutschen 0 %-Umsatzsteuersatz",
            ),
        ),
    ),
}


def _plan_pair(
    ids: tuple[int, int], snapshot: dict[str, Any], *, require_current: bool = True
) -> tuple[dict[str, Any] | None, list[tuple[int, str, str]]]:
    changes = []
    diff = []
    states = {"original", "previous", "final"}
    for page_id, revisions in zip(ids, REVISIONS[ids], strict=True):
        before = after = snapshot["pages"][str(page_id)]
        for original, final, *previous in revisions:
            versions = {
                "original": original,
                "previous": previous[0] if previous else final,
                "final": final,
            }
            counts = {text: before.count(text) for text in set(versions.values())}
            if sum(counts.values()) != 1:
                raise ValueError(
                    f"Page {page_id} has an ambiguous copy fragment: {original}"
                )
            matched = next(text for text, count in counts.items() if count == 1)
            states.intersection_update(
                state for state, text in versions.items() if text == matched
            )
            if matched != final:
                after = after.replace(matched, final, 1)
                diff.append((page_id, matched, final))
        changes.append({"id": page_id, "before": before, "after": after})
    if not states:
        raise ValueError(f"Pair {ids} contains a partial revision of the reviewed copy")
    if "final" in states:
        if require_current and not snapshot["current"]:
            raise ValueError(
                f"Pair {ids} has final copy but a stale translation baseline. Recover the native baseline before retrying."
            )
        return None, diff
    return {
        "mode": "adopt",
        "changes": changes,
        "metadata_before": snapshot["metadata"],
    }, diff


def plan_pair(
    ids: tuple[int, int], snapshot: dict[str, Any], *, require_current: bool = True
) -> dict[str, Any] | None:
    """Return a native adopt payload or None for final copy with a current baseline."""
    payload, _ = _plan_pair(ids, snapshot, require_current=require_current)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="Read-only WP-CLI prefix")
    args = parser.parse_args()
    for ids in REVISIONS:
        snapshot = reviewed_page_pair.read(args.wp, *ids)
        print(snapshot["home"], *ids)
        try:
            payload, diff = _plan_pair(ids, snapshot)
        except ValueError as error:
            parser.exit(1, f"{error}\n")
        if payload is None:
            print("Already applied")
            continue
        for page_id, before, after in diff:
            print(f"Page {page_id}\n- {before}\n+ {after}")


if __name__ == "__main__":
    main()

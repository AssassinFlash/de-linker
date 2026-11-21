"""Plan reviewed quotation copy from the exact native page fragments."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "quotation_copy", HERE / "quotation-page-copy.py"
)
assert spec and spec.loader
copy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(copy)
sys.path.pop(0)

CAPABILITY = (874, 6919)
CAPABILITY_ORIGINAL_EN = "We review the available technical data to help narrow the configuration before the Proforma is issued."
CAPABILITY_PREVIOUS = (
    "We review the available technical data with you to narrow down the configuration before order confirmation.",
    "Wir prüfen die verfügbaren technischen Daten mit Ihnen, um die passende Konfiguration vor der Auftragsbestätigung einzugrenzen.",
)
CAPABILITY_FINAL = (
    "Before we prepare your quotation, we review the available technical data with you to narrow down the configuration.",
    "Bevor wir Ihr Angebot erstellen, prüfen wir mit Ihnen die verfügbaren technischen Daten und grenzen die Auswahl passender Konfigurationen ein.",
)


def snapshot(
    ids: tuple[int, int], texts: tuple[str, str], *, current: bool = True
) -> dict[str, Any]:
    return {
        "home": "http://review.test",
        "pages": {
            str(page_id): f"<p>{text}</p>"
            for page_id, text in zip(ids, texts, strict=True)
        },
        "metadata": {str(page_id): {} for page_id in ids},
        "current": current,
    }


@pytest.mark.parametrize("english", [CAPABILITY_ORIGINAL_EN, CAPABILITY_PREVIOUS[0]])
def test_capability_restores_pre_quotation_review_in_both_languages(
    english: str,
) -> None:
    review = snapshot(CAPABILITY, (english, CAPABILITY_PREVIOUS[1]))
    final = snapshot(CAPABILITY, CAPABILITY_FINAL)

    assert copy.plan_pair(CAPABILITY, review) == {
        "mode": "adopt",
        "changes": [
            {
                "id": page_id,
                "before": review["pages"][str(page_id)],
                "after": final["pages"][str(page_id)],
            }
            for page_id in CAPABILITY
        ],
        "metadata_before": review["metadata"],
    }
    assert copy.plan_pair(CAPABILITY, final) is None


@pytest.mark.parametrize(
    "english",
    [
        f"{CAPABILITY_PREVIOUS[0]} {CAPABILITY_PREVIOUS[0]}",
        f"{CAPABILITY_ORIGINAL_EN} {CAPABILITY_PREVIOUS[0]}",
        "We will check technical details once you have ordered.",
        CAPABILITY_FINAL[0],
    ],
)
def test_capability_rejects_duplicate_unknown_or_partially_applied_copy(
    english: str,
) -> None:
    with pytest.raises(ValueError, match="ambiguous|part"):
        copy.plan_pair(
            CAPABILITY, snapshot(CAPABILITY, (english, CAPABILITY_PREVIOUS[1]))
        )


def test_final_copy_requires_current_translation_baseline() -> None:
    with pytest.raises(ValueError, match="translation baseline"):
        copy.plan_pair(
            CAPABILITY, snapshot(CAPABILITY, CAPABILITY_FINAL, current=False)
        )


EPC = (842, 6867)
EPC_EN_PREVIOUS = (
    "Equipment ships according to the delivery arrangements agreed for the order. "
    "The configuration remains flexible while we prepare your quotation. "
    "If site conditions change while we prepare your quotation, we can still adjust the configuration."
)
EPC_DE_PREVIOUS = (
    "Der Versand richtet sich nach den Liefervereinbarungen zum Auftrag. "
    "Während der Angebotserstellung bleibt die Konfiguration flexibel. "
    "Wenn sich die Standortbedingungen ändern, bevor der Auftrag in die Produktion freigegeben wird, lässt sich die Konfiguration noch ändern."
)


def test_applied_epc_candidate_only_changes_the_german_adjustment_cutoff() -> None:
    review = snapshot(EPC, (EPC_EN_PREVIOUS, EPC_DE_PREVIOUS), current=False)
    payload = copy.plan_pair(EPC, review)

    assert payload is not None
    english, german = payload["changes"]
    assert english["before"] == english["after"] == review["pages"]["842"]
    assert german["before"] == review["pages"]["6867"]
    assert german["after"] == (
        "<p>Der Versand richtet sich nach den Liefervereinbarungen zum Auftrag. "
        "Während der Angebotserstellung bleibt die Konfiguration flexibel. "
        "Wenn sich die Standortbedingungen während der Angebotserstellung ändern, können wir die Konfiguration noch anpassen.</p>"
    )


STORAGE = (1755, 6917)
STORAGE_ORIGINAL = (
    "Linker delivers a project quote detailing equipment scope, pricing, warranty coverage, and a delivery schedule confirmed in the Proforma.",
    "Linker liefert ein Projektangebot mit Geräteumfang, Preisgestaltung, Garantieabdeckung und einem in der Proformarechnung bestätigten Lieferplan.",
)
STORAGE_PREVIOUS = (
    "Linker prepares a project quotation covering equipment scope, pricing and warranty coverage. We discuss the delivery schedule with you for the order.",
    "Im Projektangebot legt Linker den Lieferumfang, die Preise und die Garantieleistungen dar. Den Lieferplan stimmen wir mit Ihnen zum Auftrag ab.",
)
STORAGE_FINAL = (
    "Your project quotation lists the equipment and prices for your storage system. We work out the delivery schedule with you when arranging the order.",
    "Ihr Projektangebot führt die Geräte und Preise für Ihr Speichersystem auf. Den Lieferplan stimmen wir bei der Auftragsabwicklung mit Ihnen ab.",
)


@pytest.mark.parametrize("texts", [STORAGE_ORIGINAL, STORAGE_PREVIOUS])
def test_storage_quotation_keeps_equipment_prices_and_delivery_planning(
    texts: tuple[str, str],
) -> None:
    planned = copy.plan_pair(STORAGE, snapshot(STORAGE, texts))

    assert planned is not None
    assert [change["after"] for change in planned["changes"]] == [
        f"<p>{text}</p>" for text in STORAGE_FINAL
    ]


def test_storage_rejects_a_mix_of_original_and_previous_candidate() -> None:
    review = snapshot(STORAGE, (STORAGE_ORIGINAL[0], STORAGE_PREVIOUS[1]))
    with pytest.raises(ValueError, match="partial revision"):
        copy.plan_pair(STORAGE, review)


@pytest.mark.parametrize(
    ("ids", "earlier_count", "remaining", "expected"),
    [
        (
            (1674, 6825),
            4,
            (
                "Invoices, Proforma invoices and related order documents are issued electronically and sent by email; by ordering, the buyer consents to receiving invoices in electronic form. Where a parcel charge can be calculated reliably, it is stated in the quotation or Proforma invoice. For pallet, dangerous-goods, multi-item, unknown-weight, and cross-border orders, Linker confirms the freight charge on the Proforma invoice, and nothing is payable until the Proforma total is complete.",
                "Rechnungen, Proformarechnungen und zugehörige Auftragsunterlagen werden elektronisch erstellt und per E-Mail bereitgestellt; mit der Bestellung stimmt der Käufer dem Erhalt von Rechnungen in elektronischer Form zu. Sofern sich die Kosten für den Paketversand zuverlässig berechnen lassen, werden sie im Angebot oder in der Proformarechnung ausgewiesen. Bei Paletten- oder Gefahrgutversand, Bestellungen mit mehreren Positionen, unbekanntem Gewicht sowie grenzüberschreitenden Lieferungen bestätigt Linker die Frachtkosten auf der Proformarechnung. Eine Zahlung ist erst fällig, wenn der Gesamtbetrag der Proformarechnung vollständig feststeht.",
            ),
            (
                "no payment is due until the full order total, including freight, is confirmed",
                "Eine Zahlung ist erst fällig, wenn der Gesamtbetrag einschließlich Frachtkosten feststeht",
            ),
        ),
        (
            (1038, 6698),
            1,
            (
                "contact Linker with the Proforma number before the goods are used or installed. Contact Linker with the Proforma number before sending anything back; a return needs written authorisation before goods are shipped.",
                "kontaktieren Sie Linker unter Angabe der Proformanummer, bevor die Ware verwendet oder installiert wird. und benachrichtigen Sie Linker mit Fotos und der Proformanummer. Kontaktieren Sie Linker unter Angabe der Proformanummer, bevor Sie etwas zurücksenden; eine Rücksendung erfordert eine schriftliche Genehmigung, bevor die Ware versandt wird.",
            ),
            (
                "order number before sending anything back",
                "mit Fotos und der Bestellnummer",
            ),
        ),
    ],
)
def test_legal_copy_keeps_order_and_payment_conditions_and_replays(
    ids: tuple[int, int],
    earlier_count: int,
    remaining: tuple[str, str],
    expected: tuple[str, str],
) -> None:
    previous = tuple(
        " ".join(row[1] for row in revisions[:earlier_count]) + " " + text
        for revisions, text in zip(copy.REVISIONS[ids], remaining, strict=True)
    )
    current = snapshot(ids, (previous[0], previous[1]))
    planned = copy.plan_pair(ids, current)
    assert planned is not None
    for change, text in zip(planned["changes"], expected, strict=True):
        assert text in change["after"]
        assert "proforma" not in change["after"].lower()
        current["pages"][str(change["id"])] = change["after"]
    assert copy.plan_pair(ids, current) is None


def test_privacy_preserves_tax_evidence_without_an_unverified_proforma_timing() -> None:
    ids = (1673, 6827)
    en, de = [revisions[0][0] for revisions in copy.REVISIONS[ids]]
    en += " (§ 12 Abs. 3 UStG) before the Proforma is issued, we record the declaration text version, timestamp, your VAT ID, IP address, and browser user agent."
    de += " Wenn Sie vor Ausstellung der Proformarechnung den deutschen 0 %-Umsatzsteuersatz beantragen, erfassen wir den Text der Erklärung, den Zeitstempel, Ihre USt-IdNr., Ihre IP-Adresse und den Browser-User-Agent."
    planned = copy.plan_pair(ids, snapshot(ids, (en, de)))
    assert planned is not None
    after_en, after_de = [change["after"] for change in planned["changes"]]
    assert "Proforma" not in after_en + after_de
    assert (
        "(§ 12 Abs. 3 UStG), we record the declaration text version, timestamp, your VAT ID, IP address, and browser user agent."
        in after_en
    )
    assert (
        "Wenn Sie den deutschen 0 %-Umsatzsteuersatz beantragen, erfassen wir den Text der Erklärung, den Zeitstempel, Ihre USt-IdNr., Ihre IP-Adresse und den Browser-User-Agent."
        in after_de
    )

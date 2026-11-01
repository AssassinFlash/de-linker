"""German customer wording for a verified English explicit-model warranty.

The mapping is used only after the complete original policy, scope, and the
individual source exclusion have been validated. A changed paragraph is not
translated by this module until its wording has been reviewed again.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

EXCLUSIONS = {
    "Normal wear and tear. (including, without limitation, appearance loss that does not affect function)": "Normale Abnutzung, einschließlich optischer Beeinträchtigungen ohne Auswirkung auf die Funktion.",
    "Any defects that occur when the limited warranty period has expired (excluding additional agreements of warranty extension).": "Mängel nach Ablauf der eingeschränkten Garantiezeit, ausgenommen zusätzlich vereinbarte Garantieverlängerungen.",
    "Product installation MUST be performed by trained installers. If it's proven that the problem was caused by faulty installation, the faults or damages are NOT covered by GOODWE's limited warranty.": "Die Installation muss durch geschulte Installateure erfolgen. Mängel oder Schäden, die nachweislich durch eine fehlerhafte Installation verursacht wurden, sind ausgeschlossen.",
    "Failure or damages due to failure to observe the product manuals or related installation and maintenance requirements.": "Ausfälle oder Schäden durch Nichtbeachtung der Produkthandbücher oder der zugehörigen Installations- und Wartungsanforderungen.",
    "Disassembly, repair or modifications performed by a third-party company/person not authorized by GOODWE. Product modifications, design changes or part replacements not approved by GOODWE.": "Demontage, Reparatur oder Änderungen durch nicht von GoodWe autorisierte Dritte sowie Produkt- oder Konstruktionsänderungen und Teileersatz ohne Genehmigung von GoodWe.",
    "Faults or damage due to unforeseen circumstances, man-made factors, or examples of force majeure including but not limited to stormy weather, flooding, overvoltage, pests, inappropriate handling, misuse, neglect, fire, water, lightning or other acts of nature.": "Mängel oder Schäden durch unvorhergesehene Umstände, menschliche Einflüsse oder höhere Gewalt, etwa Unwetter, Überschwemmung, Überspannung, Schädlinge, unsachgemäße Handhabung, Fehlgebrauch, Vernachlässigung, Feuer, Wasser, Blitzschlag oder andere Naturereignisse.",
    "For the products equipped with the SPD module, when the lightening is beyond the SPD's protection range, it won't be able to protect the EV Charger and the GOODWE limited warranty does NOT cover the EV Charger or accessory damage caused by such lightening.": "Bei Produkten mit Überspannungsschutzmodul sind Schäden an der Ladestation oder am Zubehör durch Blitzschlag außerhalb des Schutzbereichs dieses Moduls ausgeschlossen.",
    "Vandalism, engraving, labels, irreversible marking or contamination or theft.": "Vandalismus, Gravuren, Etiketten, irreversible Markierungen, Verunreinigung oder Diebstahl.",
    "Usage which does not comply with the safety regulations (VDE, IEC, etc.).": "Eine Nutzung, die den Sicherheitsvorschriften nicht entspricht, etwa denen von VDE oder IEC.",
    "Faults or damage caused by other factors not related to product quality issues.": "Mängel oder Schäden durch andere Ursachen, die nicht mit der Produktqualität zusammenhängen.",
    "Any rust that appears on the device's enclosure caused by harsh environmental conditions. Faults or damage caused by exposure to sea coasts/saltwater or other aggressive atmospheres or environmental conditions without GOODWE's written confirmation/approval prior to the installation.": "Rost am Gerätegehäuse durch raue Umweltbedingungen. Mängel oder Schäden durch Küstennähe, Salzwasser oder andere aggressive Umgebungsbedingungen ohne vorherige schriftliche Bestätigung oder Genehmigung von GoodWe.",
    "Accidents and external influences.": "Unfälle und äußere Einflüsse.",
    "Product failure is not reported to GOODWE within one month of appearance.": "Ein Produktausfall, der GoodWe nicht innerhalb von {deadline} nach Auftreten gemeldet wird.",
}
_GEO = (
    "The GOODWE Limited warranty terms and conditions only apply for the devices which are originally "
    "purchased from channels authorized by GOODWE and installed in the destination defined within "
    "the European Union countries, Norway and Switzerland, unless there are specially stipulated "
    "warranty terms and conditions between GOODWE and the direct purchaser. For any units sold for "
    "installation in one country/region but installed in another country/region, the warranty will "
    "become invalid if GOODWE does not provide written confirmation/approval prior to the installation."
)
_COVERAGE = (
    "Unless a special/unique agreement exists between GOODWE and the customer, the GOODWE limited warranty "
    "covers only the cost of hardware material required to get the device functioning again."
)


def _body(note: Any) -> str:
    quote = getattr(note, "quote", "")
    return (
        quote.split(":", 1)[1].strip()
        if isinstance(quote, str) and ":" in quote
        else ""
    )


def _one_placeholder(value: str, chunk_id: str) -> str | None:
    pattern = r"\{fact:" + re.escape(chunk_id) + r"\.n[1-9]\d*\}"
    found = re.findall(pattern, value)
    return found[0] if len(found) == 1 else None


def german_named_answers(
    chunk_id: str,
    original: Sequence[str],
    notes: Sequence[Any],
    period_id: str,
) -> dict[str, str] | None:
    """Translate only the exact reviewed conditions and one original exclusion."""
    if (
        len(original) != 11
        or len(notes) != 11
        or not re.fullmatch(r"[1-9]\d*", period_id)
    ):
        return None
    source = [_body(note) for note in notes]
    if (
        source[0] != "6 months"
        or source[1] != "channels authorized by GOODWE"
        or source[2]
        != "starting from the earlier one of following two dates: The date on which the product was first installed. 6 months after the date of production."
        or source[3] != "sold and installed after November 2022"
        or source[4] != _GEO
        or source[5] != _COVERAGE
        or source[7] != "For Europe, excluding UK"
        or source[8]
        != "However, this limited warranty shall neither exclude nor limit any of your legal (statutory) rights under the applicable national laws."
        or source[9]
        != "In some countries/districts, end users may receive an additional warranty promise (should be at least equivalent to the manufacturer's warranty) which is provided by GOODWE's local distributor; should any claims arise in this respect, please direct them to the local distributor."
        or source[10]
        != "this GOODWE limited warranty statement may NOT be the latest version"
    ):
        return None
    translated = EXCLUSIONS.get(source[6])
    months = _one_placeholder(original[0], chunk_id)
    year = _one_placeholder(original[3], chunk_id)
    if translated is None or months is None or year is None:
        return None
    if "{deadline}" in translated:
        deadline = _one_placeholder(original[6], chunk_id)
        if deadline is None:
            return None
        translated = translated.replace("{deadline}", deadline)
    period = f"{{fact:{chunk_id}.n{period_id}}}"
    buyer = (
        "Voraussetzung ist der Kauf über einen von GoodWe autorisierten Vertrieb und die "
        "Installation in der EU, Norwegen oder der Schweiz, sofern mit dem direkten Käufer "
        "keine besonderen Garantiebedingungen vereinbart wurden."
    )
    start = (
        "Die Garantie beginnt am früheren der beiden Zeitpunkte: am Tag der ersten "
        f"Installation oder {months} nach dem Herstellungsdatum."
    )
    geography = (
        "Diese Regelung gilt für Europa ohne Vereinigtes Königreich. " + buyer + " "
        "Wird ein Gerät in einem anderen Land oder Gebiet installiert als dem, für das "
        "es verkauft wurde, ist vor der Installation eine schriftliche Bestätigung oder "
        "Genehmigung von GoodWe erforderlich; andernfalls wird die Garantie ungültig. "
        "Die gesetzlichen Rechte nach nationalem Recht bleiben unberührt. In manchen "
        "Ländern oder Gebieten kann der örtliche Vertrieb zusätzliche, mindestens "
        "gleichwertige Garantieversprechen geben; Ansprüche daraus sind an diesen zu richten. "
        "GoodWe weist darauf hin, dass dieses Dokument nicht die neueste Fassung sein muss; "
        "diese ist auf der globalen GoodWe-Website zu prüfen."
    )
    coverage = (
        "Sofern keine besondere Vereinbarung besteht, deckt die eingeschränkte Garantie "
        "nur die für die Wiederherstellung der Gerätefunktion erforderlichen Materialkosten. "
        "GoodWe nennt außerdem folgenden Ausschluss: " + translated
    )
    result = {
        "period": f"Eingeschränkte Garantiedauer: {period}. {start}",
        "production": f"Ein möglicher Beginn ist {months} nach dem Herstellungsdatum; maßgeblich ist der frühere der beiden Zeitpunkte.",
        "overview": buyer,
        "start": start,
        "effective": f"Die Bedingungen gelten für Produkte, die nach November {year} verkauft und installiert wurden.",
        "geography": geography,
        "coverage": coverage,
    }
    from linker_genie.warranty_scope import exclusion_category

    category = exclusion_category(source[6])
    if source[6].startswith("Product failure is not reported to GOODWE"):
        category = "reporting"
    if category:
        result[category] = coverage
    result["general"] = "\n".join(
        result[key] for key in ("period", "effective", "geography", "coverage")
    )
    return result

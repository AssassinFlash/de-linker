"""Publication-state sentences; no current technical facts or stock claim."""

UPLOAD_UNAVAILABLE = {
    "en": "This model is outside our current product range. I can help identify it. For technical advice or system selection, please contact the Linker team at sales@de-linker.com.",
    "de": "Dieses Modell gehört derzeit nicht zu unserem Produktangebot. Ich kann Ihnen bei der Identifizierung helfen. Für technische Beratung oder die Systemauswahl wenden Sie sich bitte an das Linker-Team: sales@de-linker.com.",
}

UNVERIFIED_UPLOAD = {
    "en": "I could not verify a current product for this file. Please contact the Linker team at sales@de-linker.com.",
    "de": "Ich konnte dieser Datei kein aktuell angebotenes Produkt zuordnen. Bitte wenden Sie sich an das Linker-Team: sales@de-linker.com.",
}


def upload_unavailable(language: str, identified: bool = True) -> str:
    sentences = UPLOAD_UNAVAILABLE if identified else UNVERIFIED_UPLOAD
    return sentences["de" if language.startswith("de") else "en"]

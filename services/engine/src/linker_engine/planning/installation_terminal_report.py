"""Present each saved circuit endpoint with its manufacturer evidence."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object

STATUS = {
    "not_bound": ("No terminal selected", "Keine Klemme ausgewählt"),
    "instance_mismatch": (
        "Selected for a different device",
        "Für ein anderes Gerät ausgewählt",
    ),
    "product_unavailable": ("Product unavailable", "Produkt nicht verfügbar"),
    "product_revision_changed": ("Product revision changed", "Produktstand geändert"),
    "fact_unavailable": (
        "Manufacturer entry unavailable",
        "Herstellerangabe nicht verfügbar",
    ),
    "document_changed": ("Document revision changed", "Dokumentstand geändert"),
    "terminal_unavailable": (
        "Terminal no longer listed",
        "Klemme nicht mehr aufgeführt",
    ),
    "invalid_evidence": (
        "Source could not be verified",
        "Quelle konnte nicht geprüft werden",
    ),
    "documented": ("Terminal documented", "Klemme dokumentiert"),
}
DOMAIN = {
    "matches": ("Circuit type matches", "Stromkreisart stimmt überein"),
    "mismatch": ("Circuit type differs", "Stromkreisart weicht ab"),
}
USE = {
    "matches": ("Declared use matches", "Angegebener Verwendungszweck stimmt überein"),
    "mismatch": ("Declared use differs", "Angegebener Verwendungszweck weicht ab"),
    "not_declared": ("Circuit use missing", "Verwendungszweck des Stromkreises fehlt"),
    "not_documented": (
        "Manufacturer use unspecified",
        "Kein Verwendungszweck vom Hersteller belegt",
    ),
}


def terminal_section(
    assessment: Object, instances: list[Object], locale: str
) -> ReportSection:
    de = locale == "de"
    idx = int(de)
    ports = {
        (str(instance["id"]), str(port["id"])): f"{instance['name']} · {port['name']}"
        for instance in instances
        for port in cast(list[Object], instance["ports"])
    }
    section = ReportSection(
        id="installation-terminals",
        title="Anschlussklemmen der Geräte" if de else "Equipment terminals",
        paragraphs=[
            "Jeder Anschluss wird einzeln geprüft. Pinbelegung, Protokoll und Kompatibilität der Verbindung bleiben offen."
            if de
            else "Each endpoint is checked separately. Pin assignments, protocol and compatibility of the connection remain unverified."
        ],
    )
    for circuit in cast(list[Object], assessment["circuits"]):
        for endpoint in cast(list[Object], circuit["endpoints"]):
            ids = (str(endpoint["instance_id"]), str(endpoint["port_id"]))
            binding = endpoint.get("binding")
            port_label = ports.get(ids, " · ".join(ids))
            if isinstance(binding, dict):
                port_label += f" · {binding['terminal']}"
            details = [STATUS[str(endpoint["status"])][idx]]
            for key, labels in (("domain_status", DOMAIN), ("use_status", USE)):
                if str(endpoint[key]) in labels:
                    details.append(labels[str(endpoint[key])][idx])
            section.rows.append(
                ReportRow(
                    label=f"{circuit['name']} · {port_label}", value=" · ".join(details)
                )
            )
            fact = endpoint.get("fact")
            if isinstance(fact, dict):
                doc = cast(Object, fact["source"])
                section.rows.append(
                    ReportRow(
                        label=str(cast(Object, fact["label"])[locale]),
                        value=f"{'S.' if de else 'p.'} {doc['page']} · {doc['quote']} · {'Dokumentstand' if de else 'Document revision'} {doc['document_revision']}",
                        href=cast(str, doc["url"]),
                    )
                )
    return section

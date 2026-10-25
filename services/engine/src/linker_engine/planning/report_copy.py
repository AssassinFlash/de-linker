"""Report wording shared by its immutable screen model and PDF."""

from __future__ import annotations

TEXT = {
    "physical_input_map_requires_evidence": (
        "The input number identifies the proposed connection. A cited manufacturer connector map is still required.",
        "Die Eingangsnummer bezeichnet den geplanten Anschluss. Ein belegter Anschlussplan des Herstellers ist noch erforderlich.",
    ),
    "pv_strings_title": ("PV wiring plan", "PV-Verschaltungsplan"),
    "pv_strings_scope": (
        "The wiring plan records the assigned roof modules. Cold open-circuit voltage uses the stated ambient temperature and the module's voltage coefficient. STC operating points do not establish hot or cold MPP performance, design currents or wiring protection.",
        "Der Verschaltungsplan enthält die zugeordneten Dachmodule. Die Leerlaufspannung bei Kälte wird mit der angegebenen Umgebungstemperatur und dem Spannungskoeffizienten des Moduls berechnet. Arbeitspunkte unter STC belegen weder das MPP-Verhalten bei Hitze oder Kälte noch die Auslegungsströme oder den Leitungsschutz.",
    ),
    "pv_string": ("String", "String"),
    "pv_input": ("Input", "Eingang"),
    "pv_count": ("Modules", "Module"),
    "pv_stc_vmpp": ("Vmpp at STC", "Vmpp unter STC"),
    "pv_cold_voc": ("Cold Voc", "Voc bei Kälte"),
    "pv_min_ambient": (
        "Lowest design ambient temperature",
        "Niedrigste Auslegungs-Umgebungstemperatur",
    ),
    "pv_temperature_source": (
        "Temperature source and location",
        "Quelle der Temperaturangabe und Standort",
    ),
    "linear_cold_voc_at_declared_ambient": (
        "Voc = modules per string × module Voc at STC × [1 + βVoc × (lowest design ambient temperature − 25 °C)]. βVoc is the relative Voc temperature coefficient in 1/°C; divide a value in %/°C by 100. The design temperature and its source are required.",
        "Voc = Module je String × Voc des Moduls unter STC × [1 + βVoc × (niedrigste Auslegungs-Umgebungstemperatur − 25 °C)]. βVoc ist der relative Temperaturkoeffizient der Leerlaufspannung in 1/°C; Werte in %/°C werden durch 100 geteilt. Die Auslegungstemperatur und ihre Quelle müssen angegeben werden.",
    ),
    "stc_operating_point_only": (
        "This comparison uses STC values: 1,000 W/m² irradiance, 25 °C cell temperature and the AM1.5 reference spectrum.",
        "Dieser Vergleich verwendet STC-Werte: 1.000 W/m² Bestrahlungsstärke, 25 °C Zelltemperatur und das AM1,5-Referenzspektrum.",
    ),
    "parallel_current_at_stc_only": (
        "Parallel-string currents are added at STC. Design irradiance, temperature and applicable rating factors require separate checks.",
        "Die Ströme paralleler Strings werden unter STC addiert. Die für die Auslegung maßgebliche Bestrahlungsstärke, Temperatur und die geltenden Bemessungsfaktoren sind gesondert zu prüfen.",
    ),
    "hot_and_cold_mpp_model_required": (
        "Hot and cold operating MPP checks require a suitable module I–V model and documented cell temperatures.",
        "Für die MPP-Prüfung bei heißem und kaltem Betrieb sind ein geeignetes I–V-Modell des Moduls und belegte Zelltemperaturen erforderlich.",
    ),
    "design_irradiance_and_rating_rules_required": (
        "Design currents require documented irradiance, temperature and applicable rating rules.",
        "Die Auslegungsströme erfordern belegte Bestrahlungs- und Temperaturbedingungen sowie die geltenden Bemessungsregeln.",
    ),
    "cables_connectors_fuses_and_isolation_require_design": (
        "Cable routes, conductor ratings, connector compatibility, fuses and isolation still require project-specific design.",
        "Leitungswege, Leiterbemessung, Steckverbinder-Kompatibilität, Sicherungen und Trenneinrichtungen müssen noch projektspezifisch ausgelegt werden.",
    ),
    "pv_components_title": (
        "PV modules used in the calculation",
        "PV-Module der Berechnung",
    ),
    "pv_components_scope": (
        "Module counts come from the saved layout of the selected generation result. The listed modules are design references; electrical and mounting suitability require project-specific assessment.",
        "Die Stückzahlen stammen aus der gespeicherten Belegung des ausgewählten Ergebnisses zur PV-Erzeugung. Die aufgeführten Module dienen als Auslegungsreferenz; ihre elektrische Eignung und ihre Eignung für die Montage müssen projektspezifisch geprüft werden.",
    ),
    "pv_components_dc_scope": (
        "This list includes only the PV conversion group used by the selected DC calculation.",
        "Diese Liste enthält nur die PV-Gruppe, die für die ausgewählte DC-Berechnung verwendet wurde.",
    ),
    "pv_components_no_saved_layout": (
        "The selected generation data has no saved layout from which to determine a module count.",
        "Zu den ausgewählten Erzeugungsdaten ist keine Belegung gespeichert, aus der sich eine Modulanzahl ermitteln lässt.",
    ),
    "pv_components_no_woo_module_proof": (
        "The saved module specifications could not be linked to the product record and its source document.",
        "Die gespeicherten Modulangaben konnten dem Produktdatensatz und dem zugehörigen Quelldokument nicht eindeutig zugeordnet werden.",
    ),
    "pv_components_module_power": ("Module power (STC)", "Modulleistung (STC)"),
    "pv_components_capacity": ("PV nameplate power", "PV-Nennleistung"),
    "comparison_title": (
        "Saved calculation comparison",
        "Vergleich gespeicherter Berechnungen",
    ),
    "comparison_scope": (
        "Matching comparison conditions do not establish manufacturer performance or installation approval.",
        "Übereinstimmende Vergleichsbedingungen belegen weder die Leistungsfähigkeit der Geräte noch eine Freigabe für die Installation.",
    ),
    "comparison_definition": (
        "Difference = comparison minus baseline. Differences in ratios are shown in percentage points. PV differences also require the same AC/DC boundary.",
        "Differenz = Vergleichsberechnung minus Referenzberechnung. Unterschiede bei Anteilen werden in Prozentpunkten angegeben. Bei PV-Werten wird eine Differenz nur angezeigt, wenn beide Werte sich auf dieselbe AC- oder DC-Seite beziehen.",
    ),
    "comparison_blocked": (
        "No differences are shown because the comparison conditions differ or are incomplete.",
        "Es werden keine Differenzen angezeigt, da die Vergleichsbedingungen abweichen oder unvollständig sind.",
    ),
    "comparison_baseline": ("Baseline calculation", "Referenzberechnung"),
    "comparison_candidate": ("Comparison calculation", "Vergleichsberechnung"),
    "comparison_difference": ("Difference", "Differenz"),
    "comparison_basis": ("Comparison basis", "Vergleichsgrundlage"),
    "comparison_changes": (
        "Design and assumption changes",
        "Änderungen an Auslegung und Annahmen",
    ),
    "comparison_changed": ("Changed", "Geändert"),
    "comparison_unchanged": ("Unchanged", "Unverändert"),
    "comparison_site": ("Site and time zone", "Standort und Zeitzone"),
    "comparison_periods": ("Calculated periods", "Berechnungszeiträume"),
    "comparison_demand_sources": (
        "Load and auxiliary sources",
        "Quellen für Last und Hilfsverbrauch",
    ),
    "comparison_pv_weather": (
        "PV weather or identical generation input",
        "PV-Wetterdaten oder identische Erzeugungsdaten",
    ),
    "comparison_time_resolution": ("Time resolution", "Zeitliche Auflösung"),
    "comparison_operating_requirements": (
        "Operating requirements",
        "Betriebsanforderungen",
    ),
    "comparison_starting_inventory": (
        "Starting stored energy",
        "Gespeicherte Energie zu Beginn",
    ),
    "comparison_terminal_requirement": (
        "Required final stored energy",
        "Geforderte Mindestenergie am Ende",
    ),
    "comparison_load_scope": ("Load measurement scope", "Bilanzgrenze der Last"),
    "comparison_calculation_method": ("Calculation method", "Berechnungsmethode"),
    "comparison_scenario_constraints": (
        "Scenario requirements",
        "Szenarioanforderungen",
    ),
    "comparison_battery_temperature": ("Battery temperature", "Batterietemperatur"),
    "comparison_storage_parameters": ("Storage parameters", "Speicherparameter"),
    "comparison_equipment_selection": ("Equipment selection", "Geräteauswahl"),
    "comparison_pv_design": (
        "PV layout and generation settings",
        "PV-Belegung und Erzeugungsparameter",
    ),
    "comparison_dc_auxiliary": ("DC auxiliary demand", "DC-Hilfsverbrauch"),
    "comparison_load_demand": ("Simulated load demand", "Simulierter Strombedarf"),
    "comparison_solar_supply": (
        "Solar supplied to load",
        "Solarenergie zur Lastversorgung",
    ),
    "comparison_grid_import": ("Grid import", "Netzbezug"),
    "comparison_unserved_load": (
        "Unserved simulated load",
        "Ungedeckter simulierter Strombedarf",
    ),
    "comparison_pv_export": ("PV export", "PV-Einspeisung"),
    "comparison_stored_final": ("Stored energy at end", "Gespeicherte Energie am Ende"),
    "comparison_pv_generation": ("PV generation", "PV-Erzeugung"),
    "comparison_solar_share": (
        "Solar share of gross demand",
        "Solarer Deckungsanteil am Gesamtbedarf",
    ),
    "comparison_pv_use": (
        "PV used or stored on site",
        "PV-Energie für Verbrauch und Speicherung vor Ort",
    ),
    "comparison_matched": ("Match", "Übereinstimmend"),
    "comparison_different": ("Differ", "Abweichend"),
    "comparison_unavailable": ("Not established", "Nicht belegt"),
    "comparison_no_minimum": ("No minimum required", "Kein Mindestwert erforderlich"),
    "dc_battery_temperature": (
        "Battery temperature for this scenario",
        "Batterietemperatur im Szenario",
    ),
    "dc_temperature_scope": (
        "Battery temperature is a fixed scenario condition used to check the documented charging and discharging temperature ranges. It is not inferred from outdoor weather. This model uses fixed loss assumptions and does not simulate temperature changes.",
        "Die angegebene Batterietemperatur gilt für das gesamte Szenario als konstant und wird mit den dokumentierten Temperaturbereichen für Laden und Entladen abgeglichen. Sie wird nicht aus Wetterdaten abgeleitet. Das Modell verwendet feste Verlustannahmen und bildet keine Temperaturänderungen ab.",
    ),
    "title": ("Project planning report", "Projektplanungsbericht"),
    "subtitle": (
        "Saved project inputs and selected calculation results",
        "Gespeicherte Projekteingaben und ausgewählte Berechnungsergebnisse",
    ),
    "status": ("Assessment status", "Prüfstatus"),
    "scope": (
        "This report presents saved project inputs and the original results of the selected calculations. Country-specific requirements, electrical design and installation checks remain open. It does not approve the complete installation.",
        "Dieser Bericht enthält gespeicherte Projekteingaben und die ursprünglichen Ergebnisse der ausgewählten Berechnungen. Landesspezifische Anforderungen sowie die elektrische Auslegung und die Installation müssen noch geprüft werden. Der Bericht erteilt keine Freigabe für die Gesamtanlage.",
    ),
    "project": ("Project", "Projekt"),
    "project_id": ("Project reference", "Projektreferenz"),
    "revision": ("Input revision", "Eingabeversion"),
    "site": ("Site and project inputs", "Standort und Projekteingaben"),
    "location": ("Location", "Standort"),
    "country": ("Country", "Land"),
    "timezone": ("Time zone", "Zeitzone"),
    "note": ("Project note", "Projektnotiz"),
    "equipment": ("Equipment checks", "Prüfung der Geräteauswahl"),
    "satisfied": ("Checked requirements met", "Geprüfte Anforderungen erfüllt"),
    "violated": ("Requirements not met", "Anforderungen nicht erfüllt"),
    "unresolved": ("Further checks required", "Weitere Prüfung erforderlich"),
    "actual": ("Result", "Ergebnis"),
    "required": ("Requirement", "Anforderung"),
    "data_source": ("Data source", "Datenquelle"),
    "source": ("Source document", "Quelldokument"),
    "page": ("Page", "Seite"),
    "conditions": (
        "Components and manufacturer conditions",
        "Komponenten und Herstellervorgaben",
    ),
    "country_open": (
        "Country requirements are not assessed by the selected calculations.",
        "Landesspezifische Anforderungen werden in den ausgewählten Berechnungen nicht bewertet.",
    ),
    "bom": ("Provisional bill of materials", "Vorläufige Stückliste"),
    "bom_scope": (
        "This provisional list comes from the selected saved equipment result. Quantities are shown only where established. It is not a complete installation bill of materials. Further components and open requirements need project-specific assessment.",
        "Diese vorläufige Stückliste stammt aus dem ausgewählten gespeicherten Ergebnis zur Geräteauswahl. Mengen werden nur angegeben, soweit sie ermittelt sind. Die Liste ist noch keine vollständige Stückliste für die Installation. Weitere Komponenten und offene Anforderungen müssen projektspezifisch geprüft werden.",
    ),
    "quantity": ("Quantity", "Menge"),
    "product": ("Product", "Produkt"),
    "model": ("Model", "Modell"),
    "reference": ("Reference", "Referenz"),
    "energy": ("Energy scenario", "Energieszenario"),
    "energy_equipment": (
        "Energy scenario and selected equipment",
        "Energieszenario und ausgewählte Geräte",
    ),
    "energy_equipment_scope": (
        "These checks compare the saved scenario parameters with the equipment selected for this calculation. They do not establish manufacturer performance.",
        "Diese Prüfung vergleicht die gespeicherten Szenarioparameter mit den für die Berechnung ausgewählten Geräten. Die Leistungsfähigkeit der Geräte wird dadurch nicht nachgewiesen.",
    ),
    "check": ("Check", "Prüfung"),
    "scenario_scope": (
        "These values come from the selected saved energy result and reflect its original scenario parameters. The general energy-flow model does not establish the performance of the selected equipment.",
        "Die Werte stammen aus dem gespeicherten Ergebnis der ausgewählten Energieberechnung und beruhen auf den damaligen Szenarioparametern. Das allgemeine Energiemodell belegt nicht die Leistungsfähigkeit der ausgewählten Geräte.",
    ),
    "pv": ("PV generation scenario", "PV-Erzeugungsszenario"),
    "pv_scope": (
        "This section presents the selected saved PV profile and its original assumptions. Detailed shading and electrical design require separate assessment.",
        "Dieser Abschnitt zeigt das ausgewählte gespeicherte PV-Profil mit den damaligen Annahmen. Detaillierte Verschattung und elektrische Auslegung müssen gesondert geprüft werden.",
    ),
    "period": ("Calculation period (UTC)", "Berechnungszeitraum (UTC)"),
    "intervals": ("Calculated intervals", "Berechnete Intervalle"),
    "generation": ("PV generation", "PV-Erzeugung"),
    "generation_dc": ("PV generation (DC)", "PV-Erzeugung (DC)"),
    "curtailed_dc": ("PV curtailment (DC)", "PV-Abregelung (DC)"),
    "scenario_dc_scope": (
        "PV generation and curtailment are calculated at the DC bus; load supply and grid flows are calculated on the AC side. Storage results use the saved loss assumptions.",
        "Die PV-Werte für Erzeugung und Abregelung beziehen sich auf den DC-Zwischenkreis. Die Versorgung der Verbraucher sowie Netzbezug und Einspeisung werden auf der AC-Seite berechnet; die Speicherwerte beruhen auf den gespeicherten Verlustannahmen.",
    ),
    "load": ("Simulated load demand", "Simulierter Strombedarf"),
    "import": ("Grid import", "Netzbezug"),
    "export": ("PV export", "PV-Einspeisung"),
    "curtailed": ("PV curtailment", "PV-Abregelung"),
    "unserved": ("Unserved simulated load", "Ungedeckter simulierter Strombedarf"),
    "autarky": (
        "Solar share of gross demand",
        "Solarer Deckungsanteil am Gesamtbedarf",
    ),
    "self_use": (
        "PV used or stored on site",
        "PV-Energie für Verbrauch und Speicherung vor Ort",
    ),
    "not_defined": (
        "Not defined for this calculation",
        "Für diese Berechnung nicht definiert",
    ),
    "basis": (
        "Saved calculation references",
        "Referenzen der gespeicherten Berechnungen",
    ),
    "run": ("Calculation reference", "Berechnungsreferenz"),
    "credits": (
        "Sources and methods are identified in this report.",
        "Quellen und Methoden sind in diesem Bericht angegeben.",
    ),
}

CHECKS = {
    "pv_parallel_count": ("Strings per MPPT", "Strings je MPPT"),
    "pv_layout_coverage": ("Roof module assignment", "Zuordnung der Dachmodule"),
    "pv_tracker": ("MPPT assignment", "MPPT-Zuordnung"),
    "pv_input": ("Inverter input assignment", "Zuordnung der Wechselrichtereingänge"),
    "pv_cold_voc": ("Cold open-circuit voltage", "Leerlaufspannung bei Kälte"),
    "pv_module_voltage": (
        "Module system voltage (IEC rating)",
        "Systemspannung des Moduls (IEC-Bemessung)",
    ),
    "pv_stc_mppt": ("MPP voltage at STC", "MPP-Spannung unter STC"),
    "pv_nameplate_layout": ("Wired PV nameplate power", "Verschaltete PV-Nennleistung"),
    "pv_stc_current": ("MPPT operating current at STC", "MPPT-Betriebsstrom unter STC"),
    "pv_stc_isc": (
        "MPPT short-circuit current at STC",
        "MPPT-Kurzschlussstrom unter STC",
    ),
    "pv_parallel_match": (
        "Parallel string lengths and orientations",
        "Länge und Ausrichtung paralleler Strings",
    ),
    "pv_operating_temperatures": (
        "Hot and cold operating MPP",
        "MPP bei heißem und kaltem Betrieb",
    ),
    "pv_design_current": ("Design current", "Auslegungsstrom"),
    "pv_wiring_protection": ("Wiring and protection", "Leitungen und Schutz"),
    "converter_identity": ("Converter output", "Ausgang des Umrichters"),
    "grid_phase": ("Grid phases", "Netzphasen"),
    "pv_dc_input": ("PV input power", "PV-Eingangsleistung"),
    "pv_electrical_topology": ("PV strings and inputs", "PV-Strings und Eingänge"),
    "manufacturer_pair": ("Manufacturer pairing", "Herstellerangaben zur Kombination"),
    "modules_per_stack": ("Module count", "Anzahl der Module"),
    "parallel_stacks": ("Parallel arrangement", "Parallelschaltung"),
    "required_accessory": ("Required accessory", "Erforderliches Zubehör"),
    "battery_voltage": ("Battery voltage", "Batteriespannung"),
    "battery_sales_unit": ("Sales unit", "Verkaufseinheit"),
    "usable_energy": ("Usable energy", "Nutzbare Speicherenergie"),
    "continuous_battery_ac_output": (
        "Continuous AC discharge power",
        "AC-Dauerleistung bei Entladung",
    ),
    "continuous_battery_ac_charge": (
        "Continuous AC charge power",
        "AC-Dauerleistung bei Ladung",
    ),
    "scenario_operating_mode": ("Scenario operating mode", "Betriebsart im Szenario"),
    "scenario_parameter_basis": (
        "Storage losses and operating conditions",
        "Speicherverluste und Betriebsbedingungen",
    ),
    "scenario_model_domain": (
        "Converter ports and system topology",
        "Umrichteranschlüsse und Systemtopologie",
    ),
    "battery_discharge_path": ("Battery discharge path", "Entladepfad der Batterie"),
    "backup_mode": ("Backup transfer", "Umschaltung auf Ersatzstrom"),
    "integrated_sales_unit": (
        "Integrated storage system",
        "Integriertes Speichersystem",
    ),
    "accessory_quantity": ("Accessory quantity", "Menge des Zubehörs"),
}


def text(key: str, locale: str) -> str:
    return TEXT[key][1 if locale == "de" else 0]


def check_label(key: str, locale: str) -> str:
    return CHECKS.get(key.split(":")[0], TEXT["equipment"])[1 if locale == "de" else 0]

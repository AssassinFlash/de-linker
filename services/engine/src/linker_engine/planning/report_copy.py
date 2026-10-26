"""Report wording shared by its immutable screen model and PDF."""

from __future__ import annotations

TEXT = {
    "capacity_reference_title": (
        "Reference scenario using the manufacturer’s usable energy",
        "Referenzszenario mit nutzbarer Energie laut Hersteller",
    ),
    "capacity_reference_published": (
        "Manufacturer’s stated usable energy",
        "Nutzbare Energie laut Hersteller",
    ),
    "capacity_reference_scope": (
        "This reference calculation uses the selected product’s published usable energy as a fixed model window. The manufacturer’s test conditions are shown with the source. Choosing this mode does not establish that they are met. Ageing and changes in usable energy with temperature or charge/discharge rate are not modelled. Conversion and storage losses follow the separate scenario assumptions. Actual deliverable energy is not established.",
        "Diese Referenzberechnung verwendet die vom Hersteller angegebene nutzbare Energie des ausgewählten Produkts als festes Energiefenster im Modell. Die Prüfbedingungen des Herstellers sind beim Quellennachweis angegeben. Die Auswahl dieses Modus bestätigt nicht, dass diese Bedingungen erfüllt sind. Alterung sowie Änderungen der nutzbaren Energie durch Temperatur oder Lade- und Entladerate werden nicht modelliert. Umwandlungs- und Speicherverluste werden nach den gesonderten Szenarioannahmen berechnet. Die tatsächlich abgebbare Energie wird damit nicht nachgewiesen.",
    ),
    "comparison_capacity_basis": (
        "Capacity model differs",
        "Unterschiedliches Kapazitätsmodell",
    ),
    "plant_unit_reserve": (
        "Reserved stored energy",
        "Energiereserve im Speicher",
    ),
    "plant_unit_terminal": (
        "Minimum final stored energy",
        "Gespeicherte Mindestenergie am Ende",
    ),
    "plant_no_terminal_minimum": (
        "No minimum required",
        "Kein Mindestwert erforderlich",
    ),
    "plant_parameter_sources": (
        "Storage assumptions and product data sources",
        "Speicherannahmen und Quellen der Produktdaten",
    ),
    "plant_loss_eta_bus_to_battery": (
        "DC converter: charging efficiency",
        "DC-Wandler: Ladewirkungsgrad",
    ),
    "plant_loss_eta_battery_to_bus": (
        "DC converter: discharging efficiency",
        "DC-Wandler: Entladewirkungsgrad",
    ),
    "plant_loss_eta_store_charge": (
        "Storage: charging efficiency",
        "Speicher: Ladewirkungsgrad",
    ),
    "plant_loss_eta_store_discharge": (
        "Storage: discharging efficiency",
        "Speicher: Entladewirkungsgrad",
    ),
    "plant_loss_eta_inverter_forward": (
        "Inverter: DC to AC efficiency",
        "Wechselrichter: Wirkungsgrad DC zu AC",
    ),
    "plant_loss_eta_inverter_reverse": (
        "Inverter: AC to DC efficiency",
        "Wechselrichter: Wirkungsgrad AC zu DC",
    ),
    "plant_loss_internal_aux_kw": (
        "Internal auxiliary power",
        "Interner Hilfsverbrauch",
    ),
    "plant_loss_standing_loss_rate_per_hour": (
        "Standing-loss coefficient",
        "Koeffizient der zeitabhängigen Speicherverluste",
    ),
    "plant_common_ac_generation": (
        "PV generation at the common AC bus",
        "PV-Erzeugung an der gemeinsamen AC-Sammelschiene",
    ),
    "plant_dc_generation": (
        "DC PV generation after curtailment",
        "DC-PV-Erzeugung nach Abregelung",
    ),
    "plant_dc_stages": (
        "PV generation is shown separately at each DC bus and at the common AC bus. No combined PV self-consumption rate is calculated across these stages.",
        "Die PV-Erzeugung wird für jede DC-Sammelschiene und die gemeinsame AC-Sammelschiene getrennt ausgewiesen. Über diese Stufen hinweg wird keine gemeinsame Eigenverbrauchsquote berechnet.",
    ),
    "scenario_plant_limits": (
        "These results describe the declared scenario. Joint operating capability, continuous equipment performance, backup transfer and country-specific grid compliance are not established by this calculation.",
        "Die Ergebnisse beschreiben das angegebene Szenario. Der gemeinsame Betrieb der Geräte, ihre Dauerleistung, die Notstromumschaltung und die Erfüllung länderspezifischer Netzanforderungen sind durch diese Berechnung nicht nachgewiesen.",
    ),
    "plant_ac_charge_policy": (
        "Charging from the common AC bus",
        "Laden über die gemeinsame AC-Sammelschiene",
    ),
    "plant_ac_charge_on": (
        "Enabled (requires documented AC-to-DC charging)",
        "Aktiviert (AC-Ladung muss dokumentiert sein)",
    ),
    "plant_ac_charge_off": ("Disabled", "Deaktiviert"),
    "plant_pv_group": ("PV conversion group", "PV-Gruppe am Wechselrichter"),
    "plant_pv_unused": ("DC PV inputs unused", "DC-PV-Eingänge ungenutzt"),
    "scenario_dc_plant_scope": (
        "In each interval, each converter supplies its own DC auxiliary demand and its allocated share of AC demand before charging from local DC PV. AC demand is shared in proportion to each unit’s available power. Charging from the AC bus must be enabled and supported by the equipment documentation. It uses remaining AC surplus; grid charging is requested only when separately permitted and within the remaining import limit. This time-step calculation uses no forecast and does not reproduce a manufacturer EMS or an optimal dispatch schedule.",
        "In jedem Zeitintervall versorgt jeder Umrichter zunächst seinen DC-Eigenbedarf und seinen zugeteilten Anteil am AC-Bedarf. Erst danach lädt er den Speicher aus lokaler DC-PV-Erzeugung. Der AC-Bedarf wird im Verhältnis zur verfügbaren Leistung der einzelnen Geräte aufgeteilt. Die AC-Ladung muss aktiviert und durch die Geräteunterlagen belegt sein. Dafür wird der verbleibende AC-Überschuss genutzt. Netzladung wird nur bei gesonderter Freigabe und innerhalb der verbleibenden Netzbezugsgrenze angefordert. Die Berechnung erfolgt schrittweise ohne Prognose und bildet weder ein Hersteller-EMS noch eine optimale Einsatzplanung nach.",
    ),
    "scenario_plant_scope": (
        "This scenario models separate AC PV generation and individual storage units at one shared AC metering point, with the storage converters' DC PV inputs unused. AC PV during outages requires separately established island-operation topology; the availability setting alone is insufficient. Each unit retains its own stored energy by origin, power limits, reserve and loss assumptions; usable storage capacity is held fixed for the stated conditions. Power is allocated proportionally within each unit's power and energy limits for the current interval, without forecasting or optimal dispatch. The calculation does not reproduce a manufacturer EMS or establish joint operating capability, continuous equipment performance, backup transfer or country-specific grid compliance.",
        "Dieses Szenario berechnet die separate AC-PV-Erzeugung und die einzelnen Speichereinheiten an einem gemeinsamen AC-Messpunkt. Die DC-PV-Eingänge der Speicherumrichter sind ungenutzt. AC-PV-Erzeugung bei einem Netzausfall erfordert eine gesondert nachgewiesene Inselbetriebstopologie; die Verfügbarkeitseinstellung allein reicht dafür nicht aus. Für jede Einheit werden gespeicherte Energie nach Herkunft, Leistungsgrenzen, Reserve und Verlustannahmen getrennt geführt; die nutzbare Speicherkapazität wird für die angegebenen Bedingungen als konstant angesetzt. Die Leistung wird für das aktuelle Zeitintervall proportional innerhalb der jeweiligen Leistungs- und Energiegrenzen verteilt, ohne Prognose oder optimale Einsatzplanung. Ein Hersteller-EMS wird damit nicht nachgebildet. Der gemeinsame Betrieb der Geräte, ihre Dauerleistung, die Notstromumschaltung und die Erfüllung länderspezifischer Netzanforderungen sind nicht nachgewiesen.",
    ),
    "plant_unit_window": (
        "Usable storage capacity in this scenario",
        "Nutzbare Speicherkapazität in diesem Szenario",
    ),
    "plant_unit_start": (
        "Initial stored energy",
        "Gespeicherte Energie zu Beginn",
    ),
    "plant_unit_finish": ("Stored energy at end", "Gespeicherte Energie am Ende"),
    "plant_unit_finish_pv_kwh": (
        "Stored PV energy at end",
        "Gespeicherte PV-Energie am Ende",
    ),
    "plant_unit_finish_grid_kwh": (
        "Stored grid energy at end",
        "Gespeicherte Netzenergie am Ende",
    ),
    "plant_unit_finish_initial_unknown_kwh": (
        "Initial energy of unknown origin remaining at end",
        "Am Ende verbleibende Anfangsenergie unbekannter Herkunft",
    ),
    "not_specified": ("Not specified", "Nicht angegeben"),
    "manufacturer_requirement_matches_operating_context": (
        "The documented manufacturer requirement applies to the declared operating mode, topology and communication setup. Firmware, model combination and commissioning still require separate checks.",
        "Die dokumentierte Herstellervorgabe gilt für die angegebene Betriebsart, Topologie und Kommunikationsanbindung. Firmware, Modellkombination und Inbetriebnahme müssen weiterhin gesondert geprüft werden.",
    ),
    "parallel_count_uses_applicable_manufacturer_limit": (
        "Group size is checked only against manufacturer limits documented for the declared operating mode, topology and communication setup. If no applicable limit is documented, it remains unknown.",
        "Die Gerätezahl der Gruppe wird nur mit Herstellergrenzen abgeglichen, die für die angegebene Betriebsart, Topologie und Kommunikationsanbindung dokumentiert sind. Ist keine anwendbare Grenze dokumentiert, bleibt sie unbekannt.",
    ),
    "maximum_grid_output_is_necessary_bound_only": (
        "In grid-connected operation, the requested continuous active power from the battery cannot exceed the applicable documented maximum output of the whole inverter. Where the source gives a maximum apparent power S, |P| ≤ S is a necessary upper bound only; S is not an active-power rating. Passing this check does not establish continuous battery output.",
        "Im Netzparallelbetrieb darf die geforderte dauerhafte Wirkleistungsabgabe der Batterie die dokumentierte maximale Ausgangsleistung des gesamten Wechselrichters nicht überschreiten, sofern diese Angabe für die gewählten Bedingungen gilt. Gibt die Quelle eine maximale Scheinleistung S an, liefert |P| ≤ S lediglich eine notwendige Obergrenze; S darf nicht als Wirkleistungsangabe verwendet werden. Das Einhalten dieser Grenze weist keine Dauerentladeleistung der Batterie nach.",
    ),
    "sales_battery_system": ("Battery system", "Batteriesystem"),
    "sales_battery_module": ("Battery module", "Batteriemodul"),
    "sales_integrated_system": ("Integrated system", "Integriertes System"),
    "plant_scope": (
        "The report presents checks for each recorded system and its coordination group. Shared output, backup transfer and country-specific acceptance remain subject to the open checks.",
        "Der Bericht enthält die Prüfergebnisse für jedes erfasste System und seine Koordinationsgruppe. Die gemeinsame Leistungsabgabe, die Umschaltung auf Notstrombetrieb und die Erfüllung länderspezifischer Anforderungen sind aufgrund der offenen Prüfpunkte noch nicht bestätigt.",
    ),
    "plant_group": ("Coordination group", "Koordinationsgruppe"),
    "grid_connected": ("Grid-connected", "Netzparallelbetrieb"),
    "backup": ("Backup", "Notstrombetrieb"),
    "unit_must_match_plant_connection": (
        "Each system must match the project grid phases and operating mode.",
        "Jedes System muss die im Projekt geforderte Phasenanzahl und Betriebsart unterstützen.",
    ),
    "woo_parallel_count_requires_mode_scope": (
        "The group size is compared with the limit in the product data. Applicability to the declared operating mode and communication setup remains unconfirmed.",
        "Die Anzahl der Geräte in der Gruppe wird mit dem Grenzwert in den Produktdaten verglichen. Ob dieser Wert für die angegebene Betriebsart und Kommunikationsanbindung gilt, ist noch nicht bestätigt.",
    ),
    "mode_model_firmware_and_battery_association_require_scoped_evidence": (
        "Joint operation of this group remains unconfirmed for its operating mode, model combination, firmware versions and battery configuration.",
        "Der gemeinsame Betrieb dieser Gruppe ist hinsichtlich Betriebsart, Modellkombination, Firmwareversionen und Batteriekonfiguration noch nicht bestätigt.",
    ),
    "one_shared_controller_per_declared_group": (
        "The plan specifies one shared controller for the group. Its model and quantity must match the documented manufacturer requirements.",
        "Für die Gruppe ist ein gemeinsamer Controller vorgesehen. Modell und Stückzahl müssen den dokumentierten Herstellervorgaben entsprechen.",
    ),
    "declared_unit_demand_allocation_not_available_plant_output": (
        "These are declared project requirements allocated to individual systems. Available energy and power at the shared connection remain unconfirmed.",
        "Dies sind die den einzelnen Systemen zugewiesenen Projektanforderungen. Die verfügbare Energie und Leistung am gemeinsamen Anschlusspunkt sind noch nicht bestätigt.",
    ),
    "joint_delivery_requires_allocation_and_connection_assessment": (
        "Joint output requires assessment of the individual systems, their allocated requirements and the shared connection.",
        "Die gemeinsame Leistungsabgabe erfordert eine Prüfung der einzelnen Systeme mit ihren zugewiesenen Anforderungen sowie des gemeinsamen Anschlusspunkts.",
    ),
    "pv_fitting_method": ("Fitting method", "Anpassungsmethode"),
    "pv_refinement_method": ("Numerical refinement", "Numerische Verfeinerung"),
    "pv_translation_method": ("Temperature translation", "Temperaturumrechnung"),
    "pv_numerical_tolerance": (
        "Numerical fit tolerance",
        "Numerische Anpassungstoleranz",
    ),
    "pv_noct_irradiance": (
        "NOCT reference irradiance",
        "NOCT-Referenzbestrahlungsstärke",
    ),
    "pv_noct_cell_interval": (
        "NOCT cell-temperature interval",
        "NOCT-Zelltemperaturintervall",
    ),
    "pv_operating_title": (
        "Modeled electrical operating points",
        "Modellierte elektrische Arbeitspunkte",
    ),
    "pv_operating_scope": (
        "These estimates use a fitted single-diode model at the stated uniform module conditions. They do not include shading or establish manufacturer performance, design extremes, protection ratings or country approval.",
        "Diese Schätzwerte beruhen auf einem angepassten Eindiodenmodell bei den angegebenen einheitlichen Modulbedingungen. Sie berücksichtigen keine Verschattung und belegen weder die Leistungsangaben des Herstellers noch Auslegungsextreme, Schutzbemessungen oder eine Länderfreigabe.",
    ),
    "pv_operating_incomplete": (
        "Operating conditions and their source are incomplete.",
        "Betriebsbedingungen und deren Quelle sind noch unvollständig.",
    ),
    "pv_iv_unavailable": (
        "The maintained module data did not produce an admissible I–V model. The cold-Voc and STC checks remain available.",
        "Aus den gepflegten Moduldaten konnte kein zulässiges I–V-Modell ermittelt werden. Die Prüfungen der Leerlaufspannung bei Kälte und unter STC bleiben verfügbar.",
    ),
    "pv_effective_irradiance": ("Effective irradiance", "Effektive Bestrahlungsstärke"),
    "pv_hot_cell": (
        "Hot operating cell temperature",
        "Zelltemperatur bei heißem Betrieb",
    ),
    "pv_cold_cell": (
        "Cold operating cell temperature",
        "Zelltemperatur bei kaltem Betrieb",
    ),
    "pv_case": ("Case", "Betriebsfall"),
    "pv_hot_case": ("Hot operating case", "Heißer Betriebsfall"),
    "pv_cold_case": ("Cold operating case", "Kalter Betriebsfall"),
    "pv_model_details": (
        "Model, inputs and datasheet comparisons",
        "Modell, Eingaben und Datenblattvergleiche",
    ),
    "pv_model_scope": (
        "Batzelis initialization and De Soto fitting use the saved STC points and temperature coefficients. The fitted compound parameters do not identify the physical cell-series count. Numerical fit precision is separate from physical accuracy.",
        "Die Initialisierung nach Batzelis und die Anpassung nach De Soto verwenden die gespeicherten STC-Punkte und Temperaturkoeffizienten. Aus den angepassten zusammengesetzten Parametern lässt sich die physische Anzahl der in Reihe geschalteten Zellen nicht bestimmen. Die numerische Anpassungsgenauigkeit ist von der physikalischen Genauigkeit zu unterscheiden.",
    ),
    "pv_model_identity": ("Model reference", "Modellreferenz"),
    "pv_fitted_parameters": ("Fitted model parameters", "Angepasste Modellparameter"),
    "pv_value": ("Value", "Wert"),
    "pv_cell_technology": ("Cell technology", "Zelltechnologie"),
    "pv_eg_assumption": (
        "Silicon bandgap assumption",
        "Annahme zur Bandlücke von Silizium",
    ),
    "pv_deg_assumption": (
        "Bandgap temperature assumption",
        "Annahme zur Temperaturabhängigkeit der Bandlücke",
    ),
    "pv_numerical_residual": (
        "Relative numerical residual",
        "Relatives numerisches Residuum",
    ),
    "pv_gamma_declared": (
        "Declared power temperature coefficient",
        "Angegebener Temperaturkoeffizient der Leistung",
    ),
    "pv_gamma_model": (
        "Model power temperature coefficient",
        "Temperaturkoeffizient der Leistung im Modell",
    ),
    "pv_datasheet_comparisons": ("Datasheet comparisons", "Datenblattvergleiche"),
    "pv_diagnostics_scope": (
        "The power coefficient and NOCT values were not fitting targets. These comparisons show differences; they do not certify extrapolation accuracy.",
        "Der Leistungskoeffizient und die NOCT-Werte waren keine Zielgrößen der Anpassung. Die Vergleiche zeigen Abweichungen; sie bestätigen keine Extrapolationsgenauigkeit.",
    ),
    "pv_noct_cell": (
        "Declared NOCT cell temperature",
        "Angegebene NOCT-Zelltemperatur",
    ),
    "pv_noct_declared_power": ("Declared NOCT power", "Angegebene NOCT-Leistung"),
    "pv_noct_model_power": (
        "Model power at nominal NOCT",
        "Modellleistung bei nominaler NOCT",
    ),
    "pv_noct_model_limits": (
        "Model powers at the NOCT temperature limits",
        "Modellleistungen an den NOCT-Temperaturgrenzen",
    ),
    "derived_iv_model_with_numerical_readback": (
        "The fitted parameters reproduce the supplied STC points within the stated numerical tolerance. This is a numerical check, not a manufacturer performance validation.",
        "Die angepassten Parameter reproduzieren die vorgegebenen STC-Punkte innerhalb der angegebenen numerischen Toleranz. Dies ist eine numerische Prüfung und keine Validierung der Leistungsangaben des Herstellers.",
    ),
    "manufacturer_iv_performance_validation_required": (
        "The fit does not establish model accuracy for this exact module over its operating range. Validation against manufacturer performance data remains required.",
        "Die Anpassung belegt nicht, wie genau das Modell diesen Modultyp über seinen Betriebsbereich abbildet. Eine Validierung anhand von Leistungsdaten des Herstellers ist weiterhin erforderlich.",
    ),
    "operating_cell_conditions_required": (
        "Effective irradiance, hot and cold cell temperatures and their project basis are required for the operating-point calculation.",
        "Für die Arbeitspunktberechnung sind die effektive Bestrahlungsstärke, die heißen und kalten Zelltemperaturen und deren Projektgrundlage erforderlich.",
    ),
    "operating_cell_conditions_outside_domain": (
        "The cold cell temperature must not exceed the hot value, and both must lie within the cited module temperature range.",
        "Die kalte Zelltemperatur darf den heißen Wert nicht überschreiten. Beide Werte müssen im belegten Temperaturbereich des Moduls liegen.",
    ),
    "declared_uniform_irradiance_and_cell_conditions": (
        "The calculation applies the stated effective irradiance uniformly to the modules at each declared cell temperature.",
        "Die Berechnung verwendet die angegebene effektive Bestrahlungsstärke einheitlich für die Module bei der jeweils angegebenen Zelltemperatur.",
    ),
    "modeled_mpp_at_declared_cell_condition": (
        "This compares the modeled MPP voltage at the declared case with the documented MPPT window. Other irradiance, temperature and shading conditions require their own assessment.",
        "Verglichen wird die modellierte MPP-Spannung im angegebenen Betriebsfall mit dem dokumentierten MPPT-Bereich. Andere Bestrahlungs-, Temperatur- und Verschattungsbedingungen müssen gesondert geprüft werden.",
    ),
    "modeled_parallel_current_at_declared_conditions": (
        "Parallel currents are modeled at the declared uniform case. These points do not replace design-current or protection-rating checks.",
        "Die Parallelströme werden für den angegebenen einheitlichen Betriebsfall modelliert. Diese Arbeitspunkte ersetzen keine Prüfung des Auslegungsstroms oder der Schutzbemessung.",
    ),
    "parallel_operating_mpp_requires_matching_strings": (
        "Different parallel string lengths or orientations do not establish a common operating MPP. The operating-current sum is therefore unresolved.",
        "Unterschiedliche Längen oder Ausrichtungen paralleler Strings belegen keinen gemeinsamen MPP. Die Summe der Betriebsströme bleibt deshalb ungeklärt.",
    ),
    "module_operating_curve_not_admissible": (
        "The model did not produce a finite, physically admissible operating curve for these conditions.",
        "Das Modell lieferte für diese Bedingungen keine endliche, physikalisch zulässige Betriebskennlinie.",
    ),
    "module_iv_inputs_missing": (
        "The model requires STC Voc, Isc, Vmpp and Impp values, plus the Voc and Isc temperature coefficients, from the maintained module record with source references.",
        "Das Modell benötigt Voc, Isc, Vmpp und Impp unter STC sowie die Temperaturkoeffizienten von Voc und Isc aus dem gepflegten Moduldatensatz, jeweils mit Quellenbeleg.",
    ),
    "crystalline_module_basis_missing": (
        "The cited module record does not establish the crystalline-cell basis required by this model.",
        "Der belegte Moduldatensatz bestätigt nicht die für dieses Modell erforderliche kristalline Zellgrundlage.",
    ),
    "module_iv_points_inconsistent": (
        "The supplied STC current or voltage points are inconsistent with a physical single-diode curve.",
        "Die angegebenen STC-Strom- oder Spannungspunkte sind mit einer physikalischen Eindiodenkennlinie nicht vereinbar.",
    ),
    "module_iv_fit_not_admissible": (
        "The fitting result failed its physical or numerical checks. It is not used for operating estimates.",
        "Das Anpassungsergebnis hat die physikalischen oder numerischen Prüfungen nicht bestanden. Es wird nicht für Betriebsschätzungen verwendet.",
    ),
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
        "This list combines the selected equipment, saved roof modules and documented included components. Quantities are shown where established. Mounting, cabling, protection and other installation materials still require project-specific design.",
        "Diese Liste führt die ausgewählten Geräte, die Module der gespeicherten Dachbelegung und dokumentierte mitgelieferte Komponenten zusammen. Mengen erscheinen, soweit sie feststehen. Montagesystem, Leitungen, Schutzkomponenten und weitere Installationsmaterialien müssen noch projektspezifisch ausgelegt werden.",
    ),
    "material_handling": ("Supply scope", "Lieferumfang"),
    "material_source": ("Quantity basis and sources", "Mengengrundlage und Quellen"),
    "material_assessment": ("Planning status", "Planungsstand"),
    "material_unit": ("Unit", "Einheit"),
    "material_unit_piece": ("pc", "St."),
    "material_unit_pair": ("pair", "Paar"),
    "material_unit_m": ("m", "m"),
    "material_included_documented": (
        "Included with the equipment",
        "Mit dem Gerät mitgeliefert",
    ),
    "material_package_source": (
        "Manufacturer package contents",
        "Herstellerseitiger Lieferumfang",
    ),
    "material_installation_requirement": (
        "Installation requirement · specification pending",
        "Installationsbedarf · Spezifikation offen",
    ),
    "installation": ("Installation routing", "Leitungswege der Installation"),
    "installation_scope": (
        "Each listed cable or conductor is one physical run. Lengths use the saved three-dimensional path and explicitly declared extra length. Cable sizing, connector matching, protection, earthing, mounting and country requirements have not been assessed by this route calculation.",
        "Jede Zeile steht für eine einzelne Leitung oder einen separat geführten Leiter. Die Länge ergibt sich aus dem gespeicherten dreidimensionalen Leitungsweg zuzüglich der ausdrücklich angegebenen Zusatzlänge. Die Auslegung der Leitungen, die Kompatibilität der Steckverbinder, Schutzmaßnahmen, Erdung, Montage und länderspezifische Anforderungen werden durch diese Längenberechnung nicht geprüft.",
    ),
    "installation_instances": (
        "Physical devices and site connections",
        "Geräte und Anschlüsse am Standort",
    ),
    "installation_instance_scope": (
        "Connection point names and positions are project inputs. They do not establish manufacturer terminal ratings or approve the circuit design.",
        "Namen und Positionen der Anschlusspunkte sind Projektangaben. Die Bemessungswerte der Herstelleranschlüsse und die Auslegung des Stromkreises werden damit nicht geprüft.",
    ),
    "installation_instance": (
        "Device or site connection",
        "Gerät oder Anschluss am Standort",
    ),
    "installation_ports": ("Connection points", "Anschlusspunkte"),
    "installation_site_point": ("Site connection", "Anschluss am Standort"),
    "installation_circuit": ("Circuit / route", "Stromkreis / Leitungsweg"),
    "installation_pending": ("Quantity not confirmed", "Menge nicht bestätigt"),
    "installation_length": (
        "Route length + extra length",
        "Leitungsweglänge + Zusatzlänge",
    ),
    "installation_layout_confirmation_required": (
        "Confirm against the current layout",
        "Mit der aktuellen Planung abgleichen",
    ),
    "installation_source_missing": (
        "Measurement or drawing source missing",
        "Quelle für Messung oder Zeichnung fehlt",
    ),
    "installation_source_export_unconfirmed": (
        "Source export permission unconfirmed",
        "Berechtigung zum Export der Quelldaten nicht bestätigt",
    ),
    "installation_route_endpoints_differ": (
        "Route endpoints differ from the saved connection points",
        "Endpunkte des Leitungswegs weichen von den gespeicherten Anschlusspunkten ab",
    ),
    "installation_height_missing": ("Elevation missing", "Höhenangabe fehlt"),
    "installation_extra_length_unconfirmed": (
        "Extra length or its basis is missing",
        "Zusatzlänge oder deren Grundlage fehlt",
    ),
    "installation_route_length_not_positive": (
        "A positive route length is required",
        "Die Leitungsweglänge muss größer als null sein",
    ),
    "pv_components_roof_scope": (
        "Module counts come from the saved roof used by the selected equipment check. The modules are design references; electrical and mounting suitability require project-specific assessment.",
        "Die Stückzahlen stammen aus der gespeicherten Dachbelegung der ausgewählten Geräteprüfung. Die Module dienen als Auslegungsreferenz; ihre elektrische Eignung und ihre Eignung für die Montage müssen projektspezifisch geprüft werden.",
    ),
    "material_snapshot": ("Materials snapshot SHA-256", "SHA-256 des Materialstands"),
    "material_woo_product": ("Selected equipment", "Ausgewählte Geräte"),
    "material_pv_reference": (
        "PV reference module · project quotation",
        "PV-Referenzmodul · Projektangebot",
    ),
    "material_manufacturer_included": (
        "Included according to manufacturer · quantity unconfirmed",
        "Laut Hersteller mitgeliefert · Menge unbestätigt",
    ),
    "material_meter": ("Energy meter", "Energiezähler"),
    "material_backup": ("Backup components", "Notstromkomponenten"),
    "material_parallel_controller": ("Parallel controller", "Parallelsteuerung"),
    "material_installation_open": (
        "Installation materials require project-specific design",
        "Installationsmaterialien müssen projektspezifisch ausgelegt werden",
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
    "plant_grid_phase": (
        "Plant grid phases",
        "Phasenanzahl am Netzanschluss der Gesamtanlage",
    ),
    "plant_operating_mode": ("Plant operating mode", "Betriebsart der Gesamtanlage"),
    "plant_parallel_count": (
        "Converters in the group",
        "Anzahl der Umrichter in der Gruppe",
    ),
    "plant_joint_operation": ("Joint operation", "Gemeinsamer Betrieb"),
    "plant_operating_scope": (
        "Manufacturer requirement applicability",
        "Anwendbarkeit der Herstellervorgabe",
    ),
    "plant_controller": ("Shared controller", "Gemeinsamer Controller"),
    "plant_pv_allocation": (
        "Allocated PV nameplate rating",
        "Zugewiesene PV-Nennleistung",
    ),
    "plant_energy_allocation": (
        "Allocated usable energy target",
        "Zugewiesener Zielwert für die nutzbare Energie",
    ),
    "plant_discharge_allocation": (
        "Allocated continuous discharge power target",
        "Zugewiesener Zielwert für die Dauerentladeleistung",
    ),
    "plant_joint_energy": (
        "Usable energy at the shared connection",
        "Nutzbare Energie am gemeinsamen Anschlusspunkt",
    ),
    "plant_joint_discharge": (
        "Continuous discharge power at the shared connection",
        "Dauerentladeleistung am gemeinsamen Anschlusspunkt",
    ),
    "pv_iv_model": ("Single-diode model fit", "Anpassung des Eindiodenmodells"),
    "pv_model_applicability": (
        "Model applicability to this module",
        "Anwendbarkeit des Modells auf dieses Modul",
    ),
    "pv_operating_conditions": (
        "Operating-condition domain",
        "Bereich der Betriebsbedingungen",
    ),
    "pv_operating_curve": ("Operating curve", "Betriebskennlinie"),
    "pv_hot_mppt": (
        "Modeled MPP voltage: hot case",
        "Modellierte MPP-Spannung: heißer Betriebsfall",
    ),
    "pv_cold_mppt": (
        "Modeled MPP voltage: cold case",
        "Modellierte MPP-Spannung: kalter Betriebsfall",
    ),
    "pv_hot_current": (
        "Modeled MPPT current: hot case",
        "Modellierter MPPT-Strom: heißer Betriebsfall",
    ),
    "pv_cold_current": (
        "Modeled MPPT current: cold case",
        "Modellierter MPPT-Strom: kalter Betriebsfall",
    ),
    "pv_hot_isc": (
        "Modeled short-circuit current: hot case",
        "Modellierter Kurzschlussstrom: heißer Betriebsfall",
    ),
    "pv_cold_isc": (
        "Modeled short-circuit current: cold case",
        "Modellierter Kurzschlussstrom: kalter Betriebsfall",
    ),
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
    "grid_output_ceiling": (
        "Inverter output limit in grid-connected operation",
        "Leistungsgrenze des Wechselrichters im Netzparallelbetrieb",
    ),
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

<?php
/**
 * GW124.99K-ETR-G10 application notes and model-specific electrical data.
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\T5;

/**
 * Application sections used by the native product template.
 *
 * @param bool $de German edition.
 * @return list<array<string,mixed>>
 */
function etr_scenarios( bool $de ): array {
	$scenarios = $de ? array(
		array(
			'Ein Netzanschlusspunkt mit begrenzter Leistung',
			'Ein Gewerbebetrieb plant einen dreiphasigen Speicherwechselrichter an einem bestehenden Anschluss. Im Netzanschlussbegehren werden Wirkleistung, Scheinleistung und Strom getrennt ausgewiesen. Gerade bei diesem Modell lohnt ein Blick in die einzelne Datenblattspalte: Im Netzparallelbetrieb liegen Nenn- und Maximalwert jeweils bei 124,99 kW beziehungsweise 124,99 kVA.',
			'Bei 400 V erreicht das Gerät maximal 180,5 A. Beim GW125K-ETR-G10 beträgt der Nennstrom ebenfalls 180,5 A, der Höchstwert liegt jedoch bei 198,5 A. Die Leistungsreserve des größeren Modells gehört deshalb weder in die Schutzberechnung noch in die Leistungszusage für den GW124.99K. Für den Netzbetreiber sind außerdem die bereits vorhandenen Erzeugungseinheiten und die vereinbarte Einspeiseleistung relevant.',
			'Für die Einordnung an der deutschen 135-kW-Grenze wird die maximale Wirkleistung der Anlage betrachtet. Je nach Spannungsebene, installierter Gesamtleistung und vereinbarter Einspeisung gelten unterschiedliche Nachweise nach NELEV. Das Einheitenzertifikat und die Unterlagen für den konkreten Netzanschluss erfüllen dabei unterschiedliche Aufgaben.',
			array( 'Maximale Wirkleistung und Scheinleistung je Wechselrichter im Übersichtsschaltplan ausweisen.', 'Vorhandene Erzeugung und Erweiterungen am selben Netzanschluss erfassen.' ),
		),
		array(
			'PV-Strings über mehrere Dachflächen verteilen',
			'Ein Gewerbedach mit unterschiedlich ausgerichteten Teilflächen lässt sich auf zehn unabhängige MPP-Tracker verteilen. Jeder Tracker hat zwei Stringeingänge. Damit sind bis zu zwanzig Strings anschließbar, sofern die beiden Strings am selben Tracker elektrisch zusammenpassen. Die maximale PV-Eingangsleistung beträgt 250 kW bei 124,99 kW AC-Nennleistung.',
			'Für die Auslegung zählen die Ströme der parallelen Strings gemeinsam. Der zulässige Betriebsstrom beträgt 42 A je Tracker, der maximale Kurzschlussstrom 55 A. Für die Stringlänge sind die temperaturabhängigen Modulspannungen entscheidend. Das MPPT-Arbeitsfenster reicht von 160 bis 1000 V, die Startspannung liegt bei 200 V. Die absolute Eingangsspannungsgrenze von 1100 V bezeichnet keinen zusätzlichen Arbeitsbereich. Oberhalb von 1000 V wechselt das Gerät in Bereitschaft.',
			'Bei einem Projekt mit dem BAT-C-Schrank kommt eine weitere Bedingung hinzu: Die Leerlaufspannung der PV-Strings muss nach Fußnote 4 über 813 V liegen. Dieser Wert gehört zur Stringauslegung auf der PV-Seite. Das Arbeitsfenster des Batterieanschlusses ist separat angegeben.',
			array( 'Strom und Kurzschlussstrom für die tatsächliche Stringbelegung je Tracker berechnen.', 'Leerlaufspannung bei der tiefsten Auslegungstemperatur mit dem PV-Grenzwert abgleichen.' ),
		),
		array(
			'Den BAT-C-Schrank auf das Lastprofil abstimmen',
			'Für einen Betrieb mit hohen Lastspitzen sind die benötigte Leistung und die Dauer der Spitze zwei verschiedene Größen. Der Wechselrichter kann bis zu 124,99 kW laden oder entladen. Wie lange der Schrank diese Leistung für einen Verbraucher bereitstellen kann, hängt vom nutzbaren Energieinhalt, dem Ladezustand und den Betriebsgrenzen des Batteriesystems ab.',
			'GoodWe führt den GW261.2-BAT-LCD-G10 in der Batterie-Kompatibilitätsübersicht V029.1 auf Seite 6 für diese ETR-Leistungsklasse. Der Wechselrichter hat einen Batterieanschluss mit 750 V Nennspannung. Das Spannungsfenster reicht von 700 bis 1000 V. Für kontinuierliches Laden und Entladen gilt derselbe Höchststrom von 178,5 A. Der tatsächliche Betriebspunkt muss sowohl die Strom- als auch die Leistungsgrenze einhalten.',
			'Der maximale Wirkungsgrad von 98,2 % bezieht sich auf den Weg vom Batterieanschluss des Wechselrichters zum AC-Ausgang. Für eine Energiebilanz über einen vollständigen Lade- und Entladezyklus sind zusätzlich die Verluste der Batterie und die übrigen beteiligten Komponenten relevant.',
			array( 'Dauer und Höhe der Lastspitzen aus dem gemessenen Lastprofil übernehmen.', 'Freigegebenen Schrank, Firmwarestand und verfügbare Ladeleistung im Systementwurf festhalten.' ),
		),
		array(
			'Ersatzstrom und eine spätere Erweiterung planen',
			'Bei einem Netzausfall soll nur ein definierter Teil der Verbraucher weiterlaufen. Für diesen Strompfad sieht das ETR-Datenblatt eine externe STS-Box oder einen STS-Schrank vor. Bei einer einzelnen Einheit nennt GoodWe eine Umschaltzeit unter 10 ms. Die Nennscheinleistung im Ersatzstrombetrieb und die maximale Ersatzstrom-Scheinleistung betragen für dieses Modell jeweils 124,99 kVA.',
			'Bei Motoren oder Kälteanlagen zählt auch die Dauer des Anlaufs. Ohne Netz nennt die Modellspalte 120 % für 60 Sekunden und 150 % für zehn Sekunden. Diese kurzzeitigen Werte sind getrennt von der Dauerlast zu betrachten. Für die Aufstellung benötigt das wandmontierte Gerät mit Schutzart IP66 eine geeignete Montagefläche für 98 kg sowie die im Installationshandbuch angegebenen Abstände für Kühlung und Wartung.',
			'Für mehrere parallel betriebene ETR nennt das GoodWe-Handbuch einen SEC3000C mit Hauptprogramm ab V7.8.19. Bei einer späteren Erweiterung ändern sich die Gesamtleistung am Netzanschluss und die Anforderungen an Schutz, Messung und Betriebsführung. Für die Umschaltung einer Parallelanlage ist die vorgesehene Systemkonfiguration maßgeblich.',
			array( 'Dauerlast und Anlaufleistung der Ersatzstromverbraucher getrennt erfassen.', 'Umschalteinrichtung und Parallelsteuerung als eigene Positionen in der Systemplanung führen.' ),
		),
	) : array(
		array(
			'Working within an existing grid connection',
			'A business adding battery storage to an existing connection needs three separate figures for the grid application: active power, apparent power and line current. On the GW124.99K-ETR-G10 the rated and maximum grid outputs coincide. They are 124.99 kW of active power and 124.99 kVA of apparent power.',
			'At 400 V the maximum line current is 180.5 A. The GW125K-ETR-G10 has the same rated current, but its maximum reaches 198.5 A. That higher figure changes the design of the AC path. Use the column for the selected model when specifying switchgear or comparing the available capacity of an existing connection.',
			'For a German connection near the 135 kW boundary, the relevant quantity is active power. Count existing generation at the same connection and record the agreed export power. The applicable evidence under NELEV depends on the voltage level and the plant configuration. The unit certificates in the documents section identify the inverter, while the application describes the complete site.',
			array( 'Record the maximum active and apparent power of each unit on the single-line diagram.', 'Include existing equipment when checking the agreed export capacity.' ),
		),
		array(
			'Dividing a commercial rooftop between ten trackers',
			'Roof areas with different orientations can use separate trackers. The inverter accepts up to 250 kW of PV input across ten MPPTs. Each tracker has two string inputs, giving twenty inputs in total. The two strings on one tracker share its operating point and its current limit.',
			'Add the operating currents of the parallel strings before checking the 42 A limit per tracker. Check the combined short-circuit current against 55 A as a separate step. Voltage needs a temperature check too. The tracking window is 160 to 1000 V, with start-up at 200 V. The 1100 V maximum is an input limit. Above 1000 V the inverter enters standby and resumes normal operation when the voltage returns to 1000 V.',
			'Pairing the array with the released BAT-C cabinet introduces another string-design condition. Footnote 4 requires PV string open-circuit voltage above 813 V with that cabinet. Apply this to the PV design alongside the cold-weather upper limit. The battery port has its own voltage window.',
			array( 'Calculate the operating and short-circuit currents for the actual strings on each tracker.', 'Use the module temperature coefficients when checking the string voltage range.' ),
		),
		array(
			'Sizing battery power for a measured demand peak',
			'A demand peak has both a magnitude and a duration. The inverter can charge or discharge at up to 124.99 kW. How long the battery can sustain the required output depends on available energy, state of charge and the operating limits of the selected cabinet. Plotting the measured peak against time gives the starting point for choosing the usable capacity.',
			'GoodWe lists GW261.2-BAT-LCD-G10 for this ETR range in its Battery Compatibility Overview V029.1, page 6. The inverter has one battery port, with a nominal voltage of 750 V and a working range of 700 to 1000 V. Its continuous charge and discharge current limit is 178.5 A. A proposed operating point has to satisfy the voltage, current and power limits together.',
			'For an energy estimate, the 98.2% maximum battery-to-AC efficiency covers conversion from the inverter battery port to its AC output. A whole-cycle estimate also needs the losses during charging and inside the battery cabinet.',
			array( 'Read the required discharge power and duration from the site load trace.', 'Record the cabinet model and applicable firmware in the system design.' ),
		),
		array(
			'Backing up critical loads and adding parallel units',
			'Where only selected loads must stay online during an outage, define that circuit separately from the normal grid supply. The ETR datasheet specifies an external STS Box or STS Cabinet for backup. With one inverter it gives a transfer time below 10 ms. Rated and maximum backup apparent power on this model are both 124.99 kVA.',
			'Motor starts and refrigeration loads add a duration constraint. The off-grid peak ratings for this model are 120% for 60 seconds and 150% for ten seconds. Use the continuous rating for normal operation and compare the measured or specified starting demand with the appropriate time window. Allow mounting space for a 98 kg IP66 wall unit and the installation clearances specified for cooling and service.',
			'For parallel ETR systems, the GoodWe installation manual specifies one SEC3000C controller with main program V7.8.19 or later. Adding another inverter changes the power and current at the common connection. Revisit the protection and metering design and use the transfer specification for the actual parallel arrangement.',
			array( 'List the continuous demand and the starting demand of the critical circuits separately.', 'Include transfer equipment and the parallel controller as distinct components of the design.' ),
		),
	);
	$result    = array();
	foreach ( $scenarios as list( $title, $situation, $fit, $verdict, $checks ) ) {
		$result[] = array(
			'scenario_kind'      => 'application',
			'scenario_title'     => $title,
			'scenario_situation' => $situation,
			'scenario_fit'       => $fit,
			'scenario_verdict'   => $verdict,
			'scenario_checklist' => $checks,
		);
	}
	return $result;
}

/**
 * Edited values on the canonical English Woo product, including its German ACF.
 *
 * @param int                  $english_id GW124.99K-ETR-G10 canonical product ID.
 * @param array<string,string> $original Snapshotted post meta, as unslashed values.
 * @throws \RuntimeException When the source citation does not identify the verified ETR datasheet.
 * @return array<string,string>
 */
function batch_t5_etr_meta( int $english_id, array $original ): array {
	$meta = array();
	foreach ( array( '_tv_legacy_acf_json', '_linker_de_acf_json' ) as $key ) {
		$de                                      = '_linker_de_acf_json' === $key;
		$acf                                     = json_decode( $original[ $key ], true, 512, JSON_THROW_ON_ERROR );
		$acf['application_scenarios']            = etr_scenarios( $de );
		$peak                                    = $de ? '120 % für 60 s, 150 % für 10 s' : '120% for 60 s, 150% for 10 s';
		$acf['feature_cards'][2]['feature_body'] = $de
			? 'Mit STS-Box oder STS-Schrank liefert das Einzelgerät 124,99 kVA Ersatzstrom-Scheinleistung. Ohne Netz sind 120 % für 60 s und 150 % für 10 s möglich. Die Umschaltzeit für eine Einheit liegt unter 10 ms.'
			: 'With an STS Box or STS Cabinet, one unit supplies 124.99 kVA of backup apparent power. Off-grid peak ratings are 120% for 60 s and 150% for 10 s. Transfer takes less than 10 ms on a single unit.';
		$acf['spec_groups'][3]['spec_rows'][1]['spec_value'] = $peak;
		$rows = $de ? array(
			array( 'Max. Netzstrom bei 380 V', '190,0 A' ),
			array( 'Max. Netzstrom bei 415 V', '174,0 A' ),
			array( 'MPPT-Wirkungsgrad', '99,9 %' ),
			array( 'Netznachweise im Dokumentenbereich', 'VDE-AR-N 4105, EN 50549-1, EN 50549-2, IEC 61727 / IEC 62116, EU-Konformitätserklärung' ),
		) : array(
			array( 'Maximum grid current at 380 V', '190.0 A' ),
			array( 'Maximum grid current at 415 V', '174.0 A' ),
			array( 'MPPT efficiency', '99.9%' ),
			array( 'Grid documents on this page', 'VDE-AR-N 4105, EN 50549-1, EN 50549-2, IEC 61727 / IEC 62116, EU Declaration of Conformity' ),
		);
		foreach ( $rows as $index => list( $label, $value ) ) {
			$group = $index < 2 ? 0 : 4;
			$specs = $acf['spec_groups'][ $group ]['spec_rows'];
			if ( ! in_array( $label, array_column( $specs, 'spec_label' ), true ) ) {
				$acf['spec_groups'][ $group ]['spec_rows'][] = array(
					'spec_label' => $label,
					'spec_value' => $value,
				);
			}
		}
		$question = $de ? 'Welche PV-Stringspannung verlangt der freigegebene BAT-C-Schrank?' : 'What PV string voltage does the released BAT-C cabinet require?';
		if ( ! in_array( $question, array_column( $acf['faqs'], 'faq_question' ), true ) ) {
			$acf['faqs'][] = array(
				'faq_category' => $de ? 'PV-Auslegung' : 'PV string design',
				'faq_question' => $question,
				'faq_answer'   => $de
					? 'GoodWe nennt bei Anschluss des GW261.2-BAT-LCD-G10 eine PV-String-Leerlaufspannung über 813 V (ETR-Datenblatt V1.1, Fußnote 4). Das ist eine Vorgabe für den PV-Eingang. Für den Batterieanschluss gelten 700 bis 1000 V bei maximal 178,5 A Dauerstrom.'
					: 'GoodWe specifies PV string open-circuit voltage above 813 V with GW261.2-BAT-LCD-G10 (ETR datasheet V1.1, footnote 4). This condition applies to the PV input. The battery connection operates at 700 to 1000 V with a continuous current limit of 178.5 A.',
			);
		}
		$meta[ $key ] = (string) wp_json_encode( $acf, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
	}
	$figures = json_decode( $original['_tv_b2b_figures'], true, 512, JSON_THROW_ON_ERROR );
	foreach ( array(
		'max_current_a_380' => '190.0',
		'max_current_a_415' => '174.0',
	) as $key => $value ) {
		$figures[ $key ] = array(
			'value'         => $value,
			'unit'          => 'A',
			'evidence_refs' => array( 'GW_ETR_Datasheet_EMEA-EN_V1.1.pdf:p2' ),
		);
	}
	$sheet = $figures['ac_output_kw_nominal']['citation']['url'];
	if ( 'GW_ETR_Datasheet_EMEA-EN_V1.1.pdf' !== basename( (string) $sheet ) ) {
		throw new \RuntimeException( 'ETR datasheet citation is missing for product ' . esc_html( (string) $english_id ) );
	}
	$pages = array(
		2 => array( 'ac_output_kw_max', 'max_apparent_power_kva', 'nominal_apparent_power_kva', 'max_current_a_380', 'max_current_a_400', 'max_current_a_415', 'max_battery_charge_a', 'max_battery_charge_power_kw', 'ups_switchover_ms' ),
		3 => array( 'max_efficiency_pct', 'euro_efficiency_pct', 'battery_to_ac_efficiency_pct', 'mppt_efficiency_pct', 'dimensions_mm', 'weight_kg', 'ip_rating', 'operating_temp_c' ),
	);
	foreach ( $pages as $page => $keys ) {
		foreach ( $keys as $key ) {
			$figures[ $key ]['citation'] = array(
				'url'  => $sheet,
				'page' => $page,
			);
		}
	}
	$meta['_tv_b2b_figures'] = (string) wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
	return $meta;
}

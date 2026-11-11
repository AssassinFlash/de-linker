<?php
/**
 * The BAT-C product page's technical table gains the certification block and
 * the Australia-only rated current and power the user manual prints
 * (`GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf`, pdf p. 81-83).
 *
 * The page renders `_tv_legacy_acf_json` on English and `_linker_de_acf_json`
 * on German (Materials::acf(); ProductView::spec_groups() falls back to it
 * because no product carries `linker_specs`). Both tables are written here in
 * one pass so the two languages cannot drift: the English rows are the ones
 * tools/migrate/548-batc-pdp-spec-rows.json names, the German rows are their
 * reviewed twins (docs/acceptance/2026-11-11/548-batc-pdp-spec-rows/05-copy-review.md).
 *
 * The write is idempotent: a row whose label is already there is compared and
 * left alone or replaced, never duplicated. `_linker_de_source_acf_json` stays
 * untouched — it is the snapshot the German translation was made from, and
 * `spec_groups` is not one of the translated fields
 * (linker-i18n Translation\Fields::of_post()), so it is not what the pair means.
 *
 * WP-CLI evaluates this file: wp eval-file 548-batc-pdp-spec-rows.php -- --apply
 * Without --apply it reports what it would write and changes nothing.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

/**
 * The rows this batch adds, keyed by the English group they join.
 *
 * A row whose figure differs per product carries `per_product` keyed by
 * product ID (the manual prints one rated power per column, not a
 * charge/discharge pair; the rated current it does print as a pair).
 * `unit` and `note` are the table's own columns (ProductView::spec_groups()
 * passes both through; ProductShortcodes::pdp_specs() prints the unit beside
 * the value and the note as a muted line under it).
 *
 * @return array<string, array<string, array<int, array<string, mixed>>>>
 */
function batc_pdp_rows(): array { // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedFunctionFound -- This helper exists only inside this wp eval-file script; it is never part of the plugin namespace.
	return array(
		'en' => array(
			'Battery and electrical' => array(
				array(
					'after' => 'Max. charge / discharge power',
					'label' => 'Rated charge / discharge current',
					'value' => '100 / 100',
					'unit'  => 'A',
					'note'  => 'GoodWe rates these for Australia only; actual charge/discharge current and power derate with cell temperature and state of charge. The maximum ratings are listed above in this table.',
				),
				array(
					'after'       => 'Rated charge / discharge current',
					'label'       => 'Rated charge / discharge power',
					'per_product' => array(
						1954 => '30.7',
						1955 => '56.3',
					),
					'unit'        => 'kW',
					'note'        => 'GoodWe rates these for Australia only; actual charge/discharge current and power derate with cell temperature and state of charge. The maximum ratings are listed above in this table.',
				),
			),
			'Certification'          => array(
				array(
					'label' => 'Safety',
					'value' => 'IEC62619 / IEC63056 / IEC60730 / IEC62477 / VDE2510 / ISO13849; IEC62040 / N140 / EU 2023/1542 / UN38.3',
					'unit'  => '',
					'note'  => 'GoodWe states that not all certifications and standards are listed; the full set is on its website.',
				),
				array(
					'label' => 'EMC',
					'value' => 'IEC/EN 61000-6-1/2/3/4',
					'unit'  => '',
					'note'  => '',
				),
			),
		),
		'de' => array(
			'Batterie und elektrische Daten' => array(
				array(
					'after' => 'Max. Lade- / Entladeleistung',
					'label' => 'Nenn-Lade- / Entladestrom',
					'value' => '100 / 100',
					'unit'  => 'A',
					'note'  => 'GoodWe weist diese Werte nur für Australien aus; tatsächlicher Lade-/Entladestrom und tatsächliche Leistung werden abhängig von Zelltemperatur und Ladezustand reduziert. Die Maximalwerte stehen oben in dieser Tabelle.',
				),
				array(
					'after'       => 'Nenn-Lade- / Entladestrom',
					'label'       => 'Nenn-Lade- / Entladeleistung',
					'per_product' => array(
						1954 => '30,7',
						1955 => '56,3',
					),
					'unit'        => 'kW',
					'note'        => 'GoodWe weist diese Werte nur für Australien aus; tatsächlicher Lade-/Entladestrom und tatsächliche Leistung werden abhängig von Zelltemperatur und Ladezustand reduziert. Die Maximalwerte stehen oben in dieser Tabelle.',
				),
			),
			'Zertifizierung'                 => array(
				array(
					'label' => 'Sicherheit',
					'value' => 'IEC62619 / IEC63056 / IEC60730 / IEC62477 / VDE2510 / ISO13849; IEC62040 / N140 / EU 2023/1542 / UN38.3',
					'unit'  => '',
					'note'  => 'GoodWe weist darauf hin, dass nicht alle Zertifizierungen und Normen aufgeführt sind; die vollständige Liste steht auf der GoodWe-Website.',
				),
				array(
					'label' => 'EMV',
					'value' => 'IEC/EN 61000-6-1/2/3/4',
					'unit'  => '',
					'note'  => '',
				),
			),
		),
	);
}

/**
 * Writes the batch's rows into one legacy table.
 *
 * @param array<string, mixed>                            $decoded The table as stored.
 * @param array<string, array<int, array<string, mixed>>> $groups Group title => rows.
 * @param int                                             $product_id The product the rows are for.
 * @return array{decoded: array<string, mixed>, changed: list<string>}
 */
function batc_pdp_apply( array $decoded, array $groups, int $product_id ): array { // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedFunctionFound -- This helper exists only inside this wp eval-file script; it is never part of the plugin namespace.
	$changed = array();
	$titles  = array_map( static fn ( array $group ): string => (string) ( $group['spec_group_title'] ?? '' ), (array) ( $decoded['spec_groups'] ?? array() ) );

	foreach ( $groups as $title => $rows ) {
		$index = array_search( $title, $titles, true );
		if ( false === $index ) {
			$decoded['spec_groups'][] = array(
				'spec_group_title' => $title,
				'spec_rows'        => array(),
			);
			$titles[]                 = $title;
			$index                    = array_key_last( $decoded['spec_groups'] );
			$changed[]                = "group {$title}: created";
		}

		$current = array();
		foreach ( (array) ( $decoded['spec_groups'][ $index ]['spec_rows'] ?? array() ) as $position => $row ) {
			$current[ (string) ( $row['spec_label'] ?? '' ) ] = $position;
		}

		$insert_at = null;
		foreach ( $rows as $row ) {
			$label = $row['label'];
			$entry = array(
				'spec_label'        => $label,
				'spec_value'        => (string) ( $row['per_product'][ $product_id ] ?? $row['value'] ),
				'spec_unit'         => $row['unit'],
				'spec_note'         => $row['note'],
				'spec_is_highlight' => false,
			);
			if ( isset( $current[ $label ] ) ) {
				$existing = $decoded['spec_groups'][ $index ]['spec_rows'][ $current[ $label ] ];
				if ( $existing === $entry ) {
					$changed[] = "row {$label}: already as reviewed";
					continue;
				}
				$decoded['spec_groups'][ $index ]['spec_rows'][ $current[ $label ] ] = $entry;
				$changed[] = "row {$label}: replaced";
				continue;
			}
			$after = (string) ( $row['after'] ?? '' );
			if ( '' !== $after && isset( $current[ $after ] ) ) {
				$insert_at = $current[ $after ] + 1;
			}
			if ( null === $insert_at ) {
				$decoded['spec_groups'][ $index ]['spec_rows'][] = $entry;
			} elseif ( \is_int( $insert_at ) ) {
				array_splice( $decoded['spec_groups'][ $index ]['spec_rows'], $insert_at, 0, array( $entry ) );
				++$insert_at;
			}
			// Later rows in this batch anchor on the one just added.
			foreach ( $decoded['spec_groups'][ $index ]['spec_rows'] as $position => $stored ) {
				$current[ (string) ( $stored['spec_label'] ?? '' ) ] = $position;
			}
			$changed[] = "row {$label}: added";
		}
	}
	return array(
		'decoded' => $decoded,
		'changed' => $changed,
	);
}

( static function (): void {
	$apply  = '1' === getenv( 'BATC_PDP_APPLY' ) || in_array( '--apply', (array) ( $GLOBALS['argv'] ?? array() ), true );
	$rows   = batc_pdp_rows();
	$keys   = array(
		'en' => '_tv_legacy_acf_json',
		'de' => '_linker_de_acf_json',
	);
	$report = array();
	$failed = false;
	foreach ( array( 1954, 1955 ) as $product_id ) {
		foreach ( $keys as $side => $meta_key ) {
			$raw     = (string) get_post_meta( $product_id, $meta_key, true );
			$decoded = json_decode( $raw, true );
			if ( ! is_array( $decoded ) ) {
				$report[] = "{$product_id} {$meta_key}: unreadable, refused";
				$failed   = true;
				continue;
			}
			$result = batc_pdp_apply( $decoded, $rows[ $side ], $product_id );
			if ( $apply && array() !== $result['changed'] ) {
				update_post_meta(
					$product_id,
					$meta_key,
					wp_slash( (string) wp_json_encode( $result['decoded'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
				);
			}
			$report[] = "{$product_id} {$meta_key}: " . implode( '; ', $result['changed'] );
			foreach ( $result['changed'] as $line ) {
				if ( str_contains( $line, 'refused' ) ) {
					$failed = true;
				}
			}
		}
	}
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- WP-CLI report to a terminal, not a page.
	echo implode( "\n", $report ), "\n";
	echo $apply ? "APPLIED\n" : "DRY RUN (pass -- --apply to write)\n";
	exit( $failed ? 1 : 0 );
} )();

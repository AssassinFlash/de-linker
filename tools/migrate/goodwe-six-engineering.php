<?php
/**
 * Bind the GoodWe six-product packing lists and ET 50 manufacturer declarations.
 *
 * Run with wp eval-file goodwe-six-engineering.php plan|apply|verify /path/to/package
 *
 * @package Linker\Migrate
 */

use Linker\Commerce\Products\EngineeringFeed;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\CompatibilityClaims;
use Linker\Commerce\Products\Publication\PackageContents;

( static function ( array $args ): void {
	if ( count( $args ) !== 2 || ! in_array( $args[0], array( 'plan', 'apply', 'verify' ), true ) ) {
		WP_CLI::error( 'Usage: wp eval-file goodwe-six-engineering.php plan|apply|verify /path/to/package' );
	}
	list( $mode, $package ) = $args;
	$load                   = static function ( string $filename ) use ( $package ): array {
		$contents = file_get_contents( $package . '/data/' . $filename ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- The input is a local package manifest.
		if ( false === $contents ) {
			WP_CLI::error( 'Cannot read ' . $filename );
		}
		return json_decode( $contents, true, 512, JSON_THROW_ON_ERROR );
	};
	$inputs                 = $load( 'products_onboarding_manifest.json' );
	$pdfs                   = array_column( $load( 'pdf_manifest.json' ), null, 'filename' );
	$manifest               = Publication::catalog();
	$by_id                  = array_column( $manifest['products'], null, 'product_id' );
	$by_sha                 = array();
	foreach ( $manifest['documents'] as $doc ) {
		$by_sha[ $doc['blob_sha256'] ][] = $doc;
	}

	// The original staging filename may differ from a retained Woo upload. Only
	// the reviewed bytes in a currently related Woo document can support a row.
	$source = static function ( string $filename, int $page, array $related ) use ( $pdfs, $by_sha ): array {
		$pdf = $pdfs[ basename( $filename ) ] ?? null;
		if ( ! $pdf || $page < 1 || $page > $pdf['pages'] ) {
			WP_CLI::error( "Missing original or invalid PDF page: {$filename} p.{$page}" );
		}
		foreach ( $by_sha[ $pdf['sha256'] ] ?? array() as $doc ) {
			if ( array_intersect( $doc['product_ids'], $related ) ) {
				return array(
					'document_id' => $doc['document_id'],
					'page'        => $page,
				);
			}
		}
		WP_CLI::error( "No current related Woo document: {$filename} p.{$page} (products " . implode( ',', $related ) . ')' );
	};

	$expected = array(
		'LX C101-10'  => array( 'usable_kwh' => 101.38 ),
		'LX C138-10'  => array( 'usable_kwh' => 138.24 ),
		'LX C156-10'  => array( 'usable_kwh' => 156.67 ),
		'GW50K-ET-10' => array(
			'ac_power_kw' => 50,
			'pv_input_kw' => 75,
		),
		'GW100K-HT'   => array(
			'ac_power_kw' => 100,
			'pv_input_kw' => 150,
		),
		'GW120K-HT'   => array(
			'ac_power_kw' => 120,
			'pv_input_kw' => 180,
		),
	);
	$products = array_column( $inputs['products'], null, 'model' );
	if ( array_diff_key( $expected, $products ) || array_diff_key( $products, $expected ) ) {
		WP_CLI::error( 'The six-product input does not cover the requested GoodWe models.' );
	}
	$ids = array();
	foreach ( $products as $model => $product ) {
		$id = (int) ( $product['retained_woo_draft_id'] ?? wc_get_product_id_by_sku( $product['sku'] ) );
		if ( ( $by_id[ $id ]['model'] ?? '' ) !== $model || 0 !== strcasecmp( 'GoodWe', $by_id[ $id ]['brand'] ) ) {
			WP_CLI::error( "Expected current canonical GoodWe product for {$model}." );
		}
		$ids[ $model ] = $id;
	}

	$writes = array();
	foreach ( $products as $model => $product ) {
		$items = array();
		$id    = $ids[ $model ];
		foreach ( $product['_linker_package_contents']['items'] as $item ) {
			// HT manual PDF p.15 makes screw and bolt counts delivery-dependent.
			if ( str_ends_with( $model, '-HT' ) && in_array( $item['id'], array( 'screws', 'expansion_bolts' ), true ) ) {
				continue;
			}
			$item['source'] = $source( $item['source']['doc'], $item['source']['page'], array( $id ) );
			$items[]        = PackageContents::bind( $id, $item, $manifest, true );
		}
		$writes[ $id ][ PackageContents::META_KEY ] = array(
			'schema_version' => 1,
			'items'          => $items,
		);
	}

	$owner      = $ids['GW50K-ET-10'];
	$claims     = $products['GW50K-ET-10']['_linker_compatibility_claims'];
	$solutions  = 'GW_Commercial-Smart-Inverter-Solutions_User-Manual-ET25-50kW-EN.pdf';
	$lynx_sheet = 'GW_Lynx_C_Series_Datasheet_EMEA-EN.pdf';
	$existing   = get_post_meta( $owner, CompatibilityClaims::META_KEY, true );
	$next       = '' === $existing || array() === $existing ? array(
		'schema_version' => 1,
		'pairs'          => array(),
		'requirements'   => array(),
	) : $existing;
	if ( 1 !== ( $next['schema_version'] ?? null ) || ! is_array( $next['pairs'] ?? null ) || ! is_array( $next['requirements'] ?? null ) ) {
		WP_CLI::error( "Unexpected existing claims on {$owner}." );
	}
	$reference_models = array_flip( $inputs['live_reference_accessory_ids_on_delinker'] );
	foreach ( array( 'pairs', 'requirements' ) as $kind ) {
		foreach ( $claims[ $kind ] as $row ) {
			$related = array( $owner );
			if ( 'pairs' === $kind ) {
				$battery_id = $row['battery_product_id'];
				$related[]  = $battery_id;
				if ( isset( $reference_models[ $battery_id ] ) && ( $by_id[ $battery_id ]['model'] ?? '' ) !== $reference_models[ $battery_id ] ) {
					WP_CLI::error( "Unexpected referenced battery {$battery_id}." );
				}
				if ( in_array( $battery_id, array( $ids['LX C101-10'], $ids['LX C138-10'], $ids['LX C156-10'] ), true ) ) {
					$row['documents'][]  = array(
						'local_file' => $solutions,
						'page'       => 3,
					);
					$row['documents'][]  = array(
						'local_file' => $lynx_sheet,
						'page'       => 2,
					);
					$row['conditions'][] = array(
						'en' => 'For use with ET 40–50 kW, the Lynx C cabinet requires BMS version 25600 or later (date in the serial number: 1 June 2024 or later). The stated DC power is at nominal voltage. Available power varies with battery temperature and state of charge.',
						'de' => 'Für den Betrieb am ET 40–50 kW benötigt der Lynx-C-Schrank die BMS-Version 25600 oder höher (Datum in der Seriennummer ab 1. Juni 2024). Die angegebene DC-Leistung gilt bei Nennspannung. Die verfügbare Leistung hängt von Batterietemperatur und Ladezustand ab.',
					);
				}
			} elseif ( 'backup' === $row['kind'] ) {
				// ET solutions manual, applicable products and single-inverter backup diagram.
				$row['accessories'] = array();
				$row['documents']   = array(
					array(
						'local_file' => $solutions,
						'page'       => 3,
					),
					array(
						'local_file' => $solutions,
						'page'       => 31,
					),
					array(
						'local_file' => $solutions,
						'page'       => 112,
					),
					array(
						'local_file' => 'GW_ET40-50kW_Datasheet_EMEA-EN.pdf',
						'page'       => 2,
					),
				);
				$row['conditions']  = array(
					array(
						'en' => 'Single-inverter backup requires a separately supplied GoodWe STS200-80-10 with cabinet software version 4.400 or later. With this cabinet, transfer takes less than 10 ms when the backup load is below the inverter’s 50 kW rated power. Nominal backup apparent power is 50 kVA.',
						'de' => 'Für den Ersatzstrombetrieb eines einzelnen Wechselrichters ist ein separat bereitzustellender GoodWe STS200-80-10 mit Schranksoftware ab Version 4.400 erforderlich. Mit diesem Schrank dauert die Umschaltung weniger als 10 ms, wenn die Ersatzstromlast unter der Wechselrichter-Nennleistung von 50 kW liegt. Die Ersatzstrom-Nennscheinleistung beträgt 50 kVA.',
					),
				);
			} elseif ( 'parallel_controller' === $row['kind'] ) {
				$row['documents'][] = array(
					'local_file' => $solutions,
					'page'       => 4,
				);
				$row['documents'][] = array(
					'local_file' => $solutions,
					'page'       => 113,
				);
			}
			foreach ( $row['accessories'] as $accessory ) {
				$part = $accessory['product_id'];
				if ( ( $reference_models[ $part ] ?? null ) !== ( $by_id[ $part ]['model'] ?? '' ) ) {
					WP_CLI::error( "Unexpected accessory product {$part}." );
				}
				$related[] = $part;
			}
			foreach ( $row['documents'] as &$ref ) {
				$ref = $source( $ref['local_file'], $ref['page'], $related );
			}
			unset( $ref );
			$bound = CompatibilityClaims::bind_row( $owner, $row, $kind, $manifest, true );
			$key   = array_search( $row['id'], array_column( $next[ $kind ], 'id' ), true );
			if ( false === $key ) {
				$next[ $kind ][] = $bound;
			} else {
				$next[ $kind ][ $key ] = $bound;
			}
		}
	}
	$writes[ $owner ][ CompatibilityClaims::META_KEY ] = $next;

	$changes = 0;
	foreach ( $writes as $id => $fields ) {
		foreach ( $fields as $key => $value ) {
			if ( get_post_meta( $id, $key, true ) === $value ) {
				continue;
			}
			++$changes;
			if ( 'apply' === $mode ) {
				update_post_meta( $id, $key, wp_slash( $value ) );
				if ( get_post_meta( $id, $key, true ) !== $value ) {
					WP_CLI::error( "Could not persist {$key} for {$id}." );
				}
			} elseif ( 'verify' === $mode ) {
				WP_CLI::error( "Published {$key} differs for {$id}." );
			}
		}
	}
	$report = array(
		'mode'           => $mode,
		'changed_fields' => $changes,
		'canonical_ids'  => $ids,
	);
	if ( 'plan' !== $mode ) {
		$feed      = EngineeringFeed::feed();
		$published = array_column( $feed['products'], null, 'canonical_product_id' );
		foreach ( $ids as $model => $id ) {
			$item                  = $published[ $id ] ?? array();
			$facts                 = $expected[ $model ];
			$facts['phase']        = isset( $facts['usable_kwh'] ) ? 'unknown' : 3;
			$facts['device_class'] = isset( $facts['usable_kwh'] ) ? 'battery-systems' : 'inverters';
			$facts['application']  = 'commercial';
			foreach ( $facts as $key => $value ) {
				$actual = $item[ $key ] ?? null;
				if ( is_numeric( $value ) ? ( ! is_numeric( $actual ) || (float) $actual !== (float) $value ) : $actual !== $value ) {
					WP_CLI::error( "{$model}: expected {$key}=" . wp_json_encode( $value ) . ', got ' . wp_json_encode( $actual ) );
				}
			}
			$required = $products[ $model ]['_tv_b2b_figures'];
			if ( isset( $facts['usable_kwh'] ) ) {
				$required['usable_energy_test_c_rate']  = $required['c_rate'];
				$required['usable_energy_test_dod_pct'] = $required['dod_pct'];
				unset( $required['c_rate'], $required['dod_pct'] );
			}
			$missing = array_diff_key( $required, (array) $item['figures'] );
			if ( $missing || ! is_array( $item['package_contents']['items'] ?? null ) || 'documented' !== ( $item['package_contents']['status'] ?? null ) || ( $writes[ $id ][ PackageContents::META_KEY ]['items'] ?? null ) !== $item['package_contents']['items'] ) {
				WP_CLI::error( "{$model}: incomplete published packing list or missing figures: " . implode( ', ', array_keys( $missing ) ) );
			}
			$report['products'][ $model ] = array(
				'facts'         => $facts,
				'figure_count'  => count( (array) $item['figures'] ),
				'package_items' => count( $item['package_contents']['items'] ),
			);
		}
		$contract = $feed['compatibility'] ?? array();
		if ( empty( $contract['version'] ) || $contract['version'] !== $feed['compatibility_version'] ) {
			WP_CLI::error( 'The engineering feed has no current Woo compatibility projection.' );
		}
		$owned        = static fn( array $row ): bool => $row['inverter_product_id'] === $owner;
		$pairs        = array_filter( $contract['pairs'], $owned );
		$requirements = array_filter( $contract['requirements'], $owned );
		foreach ( $claims['pairs'] as $row ) {
			$matches = array_filter( $pairs, static fn( array $p ): bool => $p['battery_product_id'] === $row['battery_product_id'] && 'released' === $p['verdict'] );
			if ( ! $matches ) {
				WP_CLI::error( 'Missing released battery pair: ' . $row['battery_product_id'] );
			}
		}
		foreach ( $claims['requirements'] as $row ) {
			if ( ! in_array( $row['kind'], array_column( $requirements, 'kind' ), true ) ) {
				WP_CLI::error( 'Missing requirement: ' . $row['kind'] );
			}
		}
		foreach ( $requirements as $row ) {
			if ( 'backup' === $row['kind'] && in_array( 6530, array_column( $row['accessories'], 'product_id' ), true ) ) {
				WP_CLI::error( 'A backup requirement still links the wrong transfer cabinet.' );
			}
		}
		$report['battery_product_ids']   = array_column( $pairs, 'battery_product_id' );
		$report['requirements']          = array_column( $requirements, 'kind' );
		$report['source_revision']       = $feed['source_revision'];
		$report['compatibility_version'] = $contract['version'];
	}
	$receipt = wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR );
	if ( false === $receipt ) {
		WP_CLI::error( 'Could not encode the GoodWe engineering receipt.' );
	}
	WP_CLI::log( $receipt );
} )( $args ?? array() );

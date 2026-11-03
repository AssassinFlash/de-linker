<?php
/**
 * Guarded, one-time import of reviewed sales-unit figures from their already associated PDFs.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI, never a runtime source.
		$request         = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		$key             = \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY;
		$site            = home_url();
		$written         = 0;
		$protect         = static function ( int $id ): string {
			$product = wc_get_product( $id );
			if ( ! $product instanceof WC_Product ) {
				throw new RuntimeException( esc_html( "Missing product {$id}." ) );
			}
			// Include paired product identity/status, all ordinary properties and terms.
			$ids  = function_exists( 'pll_get_post_translations' ) ? array_values( pll_get_post_translations( $id ) ) : array( $id );
			$data = array();
			foreach ( $ids as $paired ) {
				$p = wc_get_product( (int) $paired );
				if ( ! $p instanceof WC_Product ) {
					throw new RuntimeException( 'Missing paired Woo product.' );
				}
				$data[ $paired ] = $p->get_data();
				unset( $data[ $paired ]['meta_data'] );
			}
			return \Linker\Commerce\Products\Publication::revision( $data );
		};
		$documents_match = static function ( int $id, array $expected ): void {
			$actual = array();
			foreach ( \Linker\Commerce\Products\Publication::manifest()['documents'] as $row ) {
				if ( in_array( $id, $row['product_ids'], true ) ) {
					$actual[ $row['document_id'] ] = $row['blob_sha256'];
				}
			}
			foreach ( $expected as $doc => $sha ) {
				if ( ( $actual[ $doc ] ?? null ) !== $sha ) {
					throw new RuntimeException( esc_html( "Associated source bytes changed for {$id}/{$doc}." ) );
				}
			}
		};
		if ( 'preview' === $request['action'] ) {
			$plan = $request['plan'];
			if ( ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || 'battery_sales_unit_v1' !== ( $plan['kind'] ?? null ) || ! is_array( $plan['products'] ?? null ) || array() === $plan['products'] ) {
				throw new RuntimeException( 'A reviewed battery sales-unit plan is required.' );
			}
			$receipt = array(
				'site'     => $site,
				'products' => array(),
			);
			foreach ( $plan['products'] as $id => $patch ) {
				$id = (int) $id;
				if ( \Linker\Commerce\Products\Publication::canonical_id( $id ) !== $id || ! \Linker\Commerce\Products\Publication::is_published( $id ) ) {
					throw new RuntimeException( 'Only current canonical published Woo products may be prepared.' );
				}
				$product = wc_get_product( $id );
				if ( ! $product instanceof WC_Product || $product->get_attribute( 'pa_model' ) !== $patch['model'] || $product->get_sku() !== $patch['sku'] ) {
					throw new RuntimeException( esc_html( "Model or SKU identity changed for {$id}." ) );
				}
				$documents_match( $id, $patch['documents'] );
				$before = get_post_meta( $id, $key, true );
				// CB2 systems carry no maintained figures yet; their first figure is created here.
				$raw = '' === $before ? array() : ( is_string( $before ) ? json_decode( $before, true, 512, JSON_THROW_ON_ERROR ) : $before );
				if ( ! is_array( $raw ) ) {
					throw new RuntimeException( 'Unreadable existing Woo figures.' );
				}
				foreach ( $patch['figures'] as $field => $change ) {
					$existing = $raw[ $field ] ?? null;
					$matches  = is_array( $existing );
					foreach ( $change['set'] as $name => $value ) {
						$matches = $matches && ( $existing[ $name ] ?? null ) === $value;
					}
					if ( $matches ) {
						continue;
					}
					if ( null === $change['expect'] ) {
						if ( null !== $existing ) {
							throw new RuntimeException( esc_html( "Unexpected existing {$id}/{$field}." ) );
						}
					} else {
						foreach ( $change['expect'] as $name => $value ) {
							if ( ! is_array( $existing ) || ( $existing[ $name ] ?? null ) !== $value ) {
								throw new RuntimeException( esc_html( "Review required for changed {$id}/{$field}/{$name}." ) );
							}
						}
					}
					$raw[ $field ] = array_replace( is_array( $existing ) ? $existing : array(), $change['set'] );
				}
				$after = wp_json_encode( $raw, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
				if ( ! is_string( $after ) ) {
					throw new RuntimeException( 'Cannot encode Woo facts.' );
				}
				$receipt['products'][ $id ] = array(
					'before'    => $before,
					'after'     => $after,
					'protected' => $protect( $id ),
					'documents' => $patch['documents'],
				);
			}
		} else {
			$receipt = $request['receipt'];
			if ( $receipt['site'] !== $site || ! in_array( $request['action'], array( 'apply', 'rollback' ), true ) ) {
				throw new RuntimeException( 'Receipt belongs to another site or action.' );
			}
			$from = 'rollback' === $request['action'] ? 'after' : 'before';
			$to   = 'rollback' === $request['action'] ? 'before' : 'after';
			// Check every preimage before the first write. No partial stale-plan application.
			foreach ( $receipt['products'] as $id => $entry ) {
				$current = get_post_meta( (int) $id, $key, true );
				if ( ( $current !== $entry[ $from ] && $current !== $entry[ $to ] ) || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id}; receipt cannot overwrite it." ) );
				}
				$documents_match( (int) $id, $entry['documents'] );
			}
			foreach ( $receipt['products'] as $id => $entry ) {
				$current = get_post_meta( (int) $id, $key, true );
				if ( $current === $entry[ $to ] ) {
					continue;
				}
				if ( $current !== $entry[ $from ] || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id} before write." ) );
				}
				// Native metadata events bind the edited facts and enqueue shared preparation.
				update_post_meta( (int) $id, $key, is_string( $entry[ $to ] ) ? wp_slash( $entry[ $to ] ) : $entry[ $to ], $entry[ $from ] );
				wc_delete_product_transients( (int) $id );
				if ( get_post_meta( (int) $id, $key, true ) !== $entry[ $to ] || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Readback failed for {$id}; retain receipt for recovery." ) );
				}
				++$written;
			}
			if ( 'apply' === $request['action'] && $written > 0 ) {
				// The engine admits a battery only when the feed publishes a resolvable
				// sales_unit_kind citation, so prove both the value and the association.
				$fresh = \Linker\Commerce\Products\Publication::manifest();
				foreach ( $receipt['products'] as $id => $entry ) {
					$figures = json_decode( (string) $entry['after'], true, 512, JSON_THROW_ON_ERROR );
					$figure  = $figures['sales_unit_kind'] ?? null;
					$item    = \Linker\Commerce\Products\EngineeringFeed::item( (int) $id, $fresh );
					$urls    = array();
					foreach ( is_array( $item ) ? (array) ( $item['documents'] ?? array() ) : array() as $doc ) {
						$urls[] = $doc['url'] ?? null;
					}
					if ( ! is_array( $figure ) || ! is_array( $item ) || ( $item['figures']['sales_unit_kind']['value'] ?? null ) !== $figure['value'] || ! in_array( $figure['citation']['url'] ?? null, $urls, true ) ) {
						throw new RuntimeException( esc_html( "The engineering feed did not publish the reviewed sales unit for {$id}." ) );
					}
				}
			}
		}
		$receipt['changes']         = 'preview' === $request['action'] ? count( array_filter( $receipt['products'], static fn ( array $entry ): bool => $entry['before'] !== $entry['after'] ) ) : $written;
		$receipt['source_revision'] = \Linker\Commerce\Products\Publication::manifest()['source_revision'];
		echo '@@548-battery-sales-units@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '548-battery-sales-units-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

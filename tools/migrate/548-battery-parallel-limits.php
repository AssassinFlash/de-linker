<?php
/**
 * Guarded, one-time import of reviewed battery parallel-cluster limits.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI, never a runtime source.
		$request           = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		$key               = \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY;
		$site              = home_url();
		$written           = 0;
		$protect           = static function ( int $id ): string {
			$product = wc_get_product( $id );
			if ( ! $product instanceof WC_Product ) {
				throw new RuntimeException( esc_html( "Missing product {$id}." ) );
			}
			$ids  = function_exists( 'pll_get_post_translations' ) ? array_values( pll_get_post_translations( $id ) ) : array( $id );
			$data = array();
			foreach ( $ids as $paired ) {
				$item = wc_get_product( (int) $paired );
				if ( ! $item instanceof WC_Product ) {
					throw new RuntimeException( 'Missing paired Woo product.' );
				}
				$data[ $paired ] = $item->get_data();
				unset( $data[ $paired ]['meta_data'] );
			}
			return \Linker\Commerce\Products\Publication::revision( $data );
		};
		$current_documents = static function ( int $id ): array {
			$actual = array();
			foreach ( \Linker\Commerce\Products\Publication::manifest()['documents'] as $row ) {
				if ( in_array( $id, $row['product_ids'], true ) ) {
					$actual[ $row['document_id'] ] = array(
						'blob_sha256'       => $row['blob_sha256'],
						'document_revision' => $row['document_revision'],
						'url'               => $row['url'],
					);
				}
			}
			return $actual;
		};
		$documents_match   = static function ( int $id, array $expected, array $actual ): void {
			foreach ( $expected as $document_id => $identity ) {
				$current = $actual[ $document_id ] ?? null;
				if ( ! is_array( $current ) || $current['blob_sha256'] !== $identity['blob_sha256'] || $current['document_revision'] !== $identity['document_revision'] || $current['url'] !== $identity['url'] ) {
					throw new RuntimeException( esc_html( "Associated source changed for {$id}/{$document_id}." ) );
				}
			}
		};
		if ( 'preview' === $request['action'] ) {
			$plan = $request['plan'];
			if ( ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || 'battery_parallel_limits_v1' !== ( $plan['kind'] ?? null ) || ! is_array( $plan['products'] ?? null ) || array() === $plan['products'] ) {
				throw new RuntimeException( 'A reviewed battery parallel-limits plan is required.' );
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
				$documents = array();
				foreach ( $patch['figures'] as $field => $change ) {
					$source = $change['source'] ?? null;
					if ( ! is_array( $source ) || ! isset( $source['document_id'], $source['page'] ) || ! is_int( $source['page'] ) ) {
						throw new RuntimeException( esc_html( "A reviewed source is required for {$id}/{$field}." ) );
					}
					$documents[ $source['document_id'] ] = array(
						'blob_sha256'       => $source['blob_sha256'],
						'document_revision' => $source['document_revision'],
						'url'               => $change['set']['citation']['url'],
					);
				}
				// The reviewed citation must name this exact associated document page.
				$actual = $current_documents( $id );
				$documents_match( $id, $documents, $actual );
				foreach ( $patch['figures'] as $field => $change ) {
					$source   = $change['source'];
					$citation = $change['set']['citation'];
					$document = $actual[ $source['document_id'] ];
					if ( $citation['url'] !== $document['url'] || $citation['page'] !== $source['page'] ) {
						throw new RuntimeException( esc_html( "The citation of {$id}/{$field} does not point at the reviewed source page." ) );
					}
				}
				$before = get_post_meta( $id, $key, true );
				// A product without maintained figures starts from an empty object.
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
					'model'     => $patch['model'],
					'before'    => $before,
					'after'     => $after,
					'protected' => $protect( $id ),
					'documents' => $documents,
				);
			}
		} else {
			$receipt = $request['receipt'];
			if ( ! is_array( $receipt ) || ( $receipt['site'] ?? null ) !== $site || ! in_array( $request['action'], array( 'apply', 'rollback' ), true ) ) {
				throw new RuntimeException( 'Receipt belongs to another site or action.' );
			}
			$from = 'rollback' === $request['action'] ? 'after' : 'before';
			$to   = 'rollback' === $request['action'] ? 'before' : 'after';
			foreach ( $receipt['products'] as $id => $entry ) {
				$current = get_post_meta( (int) $id, $key, true );
				if ( ( $current !== $entry[ $from ] && $current !== $entry[ $to ] ) || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id}; receipt cannot overwrite it." ) );
				}
				$documents_match( (int) $id, $entry['documents'], $current_documents( (int) $id ) );
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
			if ( 'apply' === $request['action'] ) {
				// The engine admits a limit only when the feed publishes a resolvable citation.
				$fresh = \Linker\Commerce\Products\Publication::manifest();
				foreach ( $receipt['products'] as $id => $entry ) {
					$figures = json_decode( (string) $entry['after'], true, 512, JSON_THROW_ON_ERROR );
					$figure  = $figures['stacks_parallel_max'] ?? null;
					$item    = \Linker\Commerce\Products\EngineeringFeed::item( (int) $id, $fresh );
					$feed    = is_array( $item ) ? (array) ( $item['figures'] ?? null ) : array();
					$urls    = array();
					foreach ( is_array( $item ) ? (array) ( $item['documents'] ?? array() ) : array() as $doc ) {
						$urls[] = $doc['url'] ?? null;
					}
					if ( ! is_array( $figure ) || ! is_array( $item ) || ( $feed['stacks_parallel_max']['value'] ?? null ) !== $figure['value'] || ! in_array( $figure['citation']['url'] ?? null, $urls, true ) ) {
						throw new RuntimeException( esc_html( "The engineering feed did not publish the reviewed parallel limit for {$id}." ) );
					}
				}
			}
		}
		$receipt['changes']         = 'preview' === $request['action'] ? count( array_filter( $receipt['products'], static fn( array $entry ): bool => $entry['before'] !== $entry['after'] ) ) : $written;
		$receipt['source_revision'] = \Linker\Commerce\Products\Publication::manifest()['source_revision'];
		echo '@@548-battery-parallel-limits@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '548-battery-parallel-limits-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

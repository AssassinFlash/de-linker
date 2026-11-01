<?php
/**
 * Add only the reviewed Nexans current rows to existing Woo references.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI.
		$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		$action  = $request['action'] ?? '';
		$plan    = $request['plan'] ?? null;
		$digest  = $request['plan_sha256'] ?? null;
		if ( ! in_array( $action, array( 'preview', 'apply', 'verify', 'rollback' ), true ) || ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || ! is_array( $plan['references'] ?? null ) || ! is_string( $digest ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $digest ) ) {
			throw new RuntimeException( 'Invalid cable-current request.' );
		}
		$expected = array(
			'nexans-038021106' => 8467,
			'nexans-038023102' => 8468,
		);
		$planned  = array();
		foreach ( $plan['references'] as $entry ) {
			if ( ! is_array( $entry ) || ! isset( $expected[ $entry['id'] ?? '' ] ) || isset( $planned[ $entry['id'] ] ) || 'cable' !== ( $entry['kind'] ?? null ) || ! is_string( $entry['model'] ?? null ) || ! is_array( $entry['cable_facts']['reference_current_ratings'] ?? null ) || 3 !== count( $entry['cable_facts']['reference_current_ratings'] ) ) {
				throw new RuntimeException( 'Only the two reviewed cable references are supported.' );
			}
			$planned[ $entry['id'] ] = $entry;
		}
		if ( count( $planned ) !== count( $expected ) ) {
			throw new RuntimeException( 'Both reviewed cable references are required.' );
		}
		$reference_for = static function ( string $id ) use ( $planned ): array {
			$reference = $planned[ $id ] ?? null;
			if ( ! is_array( $reference ) ) {
				throw new RuntimeException( 'A reviewed cable reference is missing.' );
			}
			return $reference;
		};
		$site          = home_url();
		$host          = wp_parse_url( $site, PHP_URL_HOST );
		$local         = in_array( $host, array( 'localhost', '127.0.0.1', '::1' ), true );
		$manifest      = \Linker\Commerce\Products\Publication::manifest();
		$rows          = array_column( $manifest['products'], null, 'product_id' );
		$key           = \Linker\Commerce\Products\Publication\CableFacts::META_KEY;
		$products      = array();
		$documents_for = static function ( int $id, array $current ): array {
			$documents = array();
			foreach ( $current['documents'] as $document ) {
				if ( in_array( $id, $document['product_ids'], true ) ) {
					$documents[ $document['document_id'] ] = array(
						'document_id'       => $document['document_id'],
						'document_revision' => $document['document_revision'],
						'blob_sha256'       => $document['blob_sha256'],
						'url'               => $document['url'],
					);
				}
			}
			ksort( $documents );
			return $documents;
		};
		foreach ( $expected as $engineering_id => $production_id ) {
			$reference = $planned[ $engineering_id ] ?? null;
			if ( ! is_array( $reference ) ) {
				throw new RuntimeException( 'A reviewed cable reference is missing.' );
			}
			$found = get_posts(
				array(
					'post_type'                   => 'product',
					'post_status'                 => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ),
					'fields'                      => 'ids',
					'posts_per_page'              => -1,
					'suppress_filters'            => true,
					'lang'                        => '',
					'linker_publication_internal' => true,
					'cache_results'               => false,
					'meta_key'                    => \Linker\Commerce\Products\EngineeringReference::ID_META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Two explicit migration identities.
					'meta_value'                  => $engineering_id, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Two explicit migration identities.
				)
			);
			$ids   = array_values( array_unique( array_map( static fn ( int|string $id ): int => \Linker\Commerce\Products\Publication::canonical_id( (int) $id ), $found ) ) );
			if ( 1 !== count( $ids ) || ( ! $local && $ids[0] !== $production_id ) ) {
				throw new RuntimeException( 'Cable reference identity or production ID differs.' );
			}
			$id      = $ids[0];
			$product = wc_get_product( $id );
			if ( ! $product instanceof WC_Product || ! \Linker\Commerce\Products\Publication::is_published( $id ) || \Linker\Commerce\Products\Publication::canonical_id( $id ) !== $id || \Linker\Commerce\Products\EngineeringReference::CABLE !== \Linker\Commerce\Products\EngineeringReference::role( $id ) || get_post_meta( $id, \Linker\Commerce\Products\EngineeringReference::ID_META_KEY, true ) !== $engineering_id || $product->get_attribute( 'pa_model' ) !== $reference['model'] || ! is_array( $rows[ $id ] ?? null ) ) {
				throw new RuntimeException( 'Cable reference product, role or model changed.' );
			}
			$products[ $id ] = array(
				'engineering_id'   => $engineering_id,
				'model'            => $reference['model'],
				'product_revision' => $rows[ $id ]['product_revision'],
				'documents'        => $documents_for( $id, $manifest ),
			);
		}
		$protected = static function ( int $id ): string {
			$ids  = function_exists( 'pll_get_post_translations' ) ? array_values( pll_get_post_translations( $id ) ) : array( $id );
			$data = array();
			foreach ( $ids as $paired ) {
				$product = wc_get_product( (int) $paired );
				if ( ! $product instanceof WC_Product ) {
					throw new RuntimeException( 'A paired Woo product is missing.' );
				}
				$data[ $paired ] = $product->get_data();
				unset( $data[ $paired ]['meta_data'] );
			}
			return \Linker\Commerce\Products\Publication::revision( $data );
		};
		$patch     = static function ( int $id, array $before, array $reference, array $publication, array &$changes ): array {
			if ( null === \Linker\Commerce\Products\Publication\CableFacts::project( $id, $before, $publication ) ) {
				throw new RuntimeException( 'Existing cable facts are missing, changed or unbound.' );
			}
			$after = $before;
			if ( ! array_key_exists( 'reference_current_ratings', $after ) ) {
				$after['reference_current_ratings'] = array();
			}
			$seen = array();
			foreach ( $after['reference_current_ratings'] as $current ) {
				$seen[ $current['id'] ] = $current;
			}
			foreach ( $reference['cable_facts']['reference_current_ratings'] as $rating ) {
				$source = is_array( $rating ) ? ( $rating['source'] ?? null ) : null;
				if ( ! is_array( $rating ) || ! is_string( $rating['id'] ?? null ) || ! is_array( $source ) || ! is_string( $source['document_url'] ?? null ) || ! is_string( $source['blob_sha256'] ?? null ) || ! is_int( $source['page'] ?? null ) || ! is_string( $source['quote'] ?? null ) ) {
					throw new RuntimeException( 'A reviewed current needs its original document.' );
				}
				$document_id = \Linker\Commerce\Products\Publication\DocumentFiles::id( $source['document_url'] );
				$document    = null;
				foreach ( $publication['documents'] as $candidate ) {
					if ( $document_id === $candidate['document_id'] && $source['blob_sha256'] === $candidate['blob_sha256'] && in_array( $id, $candidate['product_ids'], true ) ) {
						$document = $candidate;
						break;
					}
				}
				if ( null === $document ) {
					throw new RuntimeException( 'The current source PDF or product association differs.' );
				}
				$rating['source'] = array(
					'document_id'       => $document_id,
					'document_revision' => $document['document_revision'],
					'blob_sha256'       => $document['blob_sha256'],
					'product_id'        => $id,
					'page'              => $source['page'],
					'quote'             => $source['quote'],
				);
				if ( isset( $seen[ $rating['id'] ] ) && \Linker\Commerce\Products\Publication::revision( $seen[ $rating['id'] ] ) !== \Linker\Commerce\Products\Publication::revision( $rating ) ) {
					throw new RuntimeException( 'A reviewed current conflicts with existing Woo data.' );
				}
				if ( ! isset( $seen[ $rating['id'] ] ) ) {
					$after['reference_current_ratings'][] = $rating;
					$seen[ $rating['id'] ]                = $rating;
					$changes[]                            = array(
						'product_id' => $id,
						'id'         => $rating['id'],
						'before'     => null,
						'after'      => $rating,
					);
				}
			}
			if ( null === \Linker\Commerce\Products\Publication\CableFacts::project( $id, $after, $publication ) ) {
				throw new RuntimeException( 'The reviewed currents fail the cable publication contract.' );
			}
			return $after;
		};
		if ( 'preview' === $action ) {
			$receipt = array(
				'schema_version'  => 1,
				'scope'           => 'nexans-reference-currents-v1',
				'action'          => $action,
				'site'            => $site,
				'plan_sha256'     => $digest,
				'source_revision' => $manifest['source_revision'],
				'products'        => array(),
				'changes'         => array(),
			);
			foreach ( $products as $id => $product ) {
				$before = get_post_meta( $id, $key, true );
				if ( ! metadata_exists( 'post', $id, $key ) || ! is_array( $before ) ) {
					throw new RuntimeException( 'Existing cable facts are required.' );
				}
				$after                      = $patch( $id, $before, $reference_for( $product['engineering_id'] ), $manifest, $receipt['changes'] );
				$receipt['products'][ $id ] = $product + array(
					'before'     => $before,
					'after'      => $after,
					'after_hash' => \Linker\Commerce\Products\Publication::revision( $after ),
					'protected'  => $protected( $id ),
				);
			}
			$result = $receipt;
		} else {
			$receipt = $request['receipt'] ?? null;
			if ( ! is_array( $receipt ) || 1 !== ( $receipt['schema_version'] ?? null ) || 'nexans-reference-currents-v1' !== ( $receipt['scope'] ?? null ) || ( $receipt['site'] ?? null ) !== $site || ( $receipt['plan_sha256'] ?? null ) !== $digest || ! is_array( $receipt['products'] ?? null ) || array_keys( $receipt['products'] ) !== array_keys( $products ) ) {
				throw new RuntimeException( 'Receipt identity or product scope differs.' );
			}
			$changes = array();
			foreach ( $products as $id => $product ) {
				$entry = $receipt['products'][ $id ];
				if ( ! is_array( $entry ) || $entry['engineering_id'] !== $product['engineering_id'] || $entry['model'] !== $product['model'] || $entry['documents'] !== $product['documents'] || $entry['protected'] !== $protected( $id ) || ! is_array( $entry['before'] ) ) {
					throw new RuntimeException( 'Cable product or document changed after preview.' );
				}
				$after = $patch( $id, $entry['before'], $reference_for( $product['engineering_id'] ), $manifest, $changes );
				if ( $after !== $entry['after'] || \Linker\Commerce\Products\Publication::revision( $after ) !== $entry['after_hash'] ) {
					throw new RuntimeException( 'Receipt changes unrelated cable data.' );
				}
				$current = get_post_meta( $id, $key, true );
				if ( ! metadata_exists( 'post', $id, $key ) || ( $current !== $entry['before'] && $current !== $entry['after'] ) ) {
					throw new RuntimeException( 'Cable facts changed after preview.' );
				}
				if ( 'apply' === $action && $current === $entry['before'] && $current !== $entry['after'] && $entry['product_revision'] !== $product['product_revision'] ) {
					throw new RuntimeException( 'Cable product revision changed after preview.' );
				}
			}
			if ( $changes !== $receipt['changes'] ) {
				throw new RuntimeException( 'Receipt change list differs from the reviewed input.' );
			}
			$written = 0;
			$states  = array();
			foreach ( $products as $id => $product ) {
				$entry   = $receipt['products'][ $id ];
				$current = get_post_meta( $id, $key, true );
				$target  = 'rollback' === $action ? $entry['before'] : $entry['after'];
				$fresh   = \Linker\Commerce\Products\Publication::manifest();
				$latest  = array_column( $fresh['products'], null, 'product_id' );
				if ( ! metadata_exists( 'post', $id, $key ) || ( $current !== $entry['before'] && $current !== $entry['after'] ) || $protected( $id ) !== $entry['protected'] || $documents_for( $id, $fresh ) !== $entry['documents'] || \Linker\Commerce\Products\EngineeringReference::CABLE !== \Linker\Commerce\Products\EngineeringReference::role( $id ) || get_post_meta( $id, \Linker\Commerce\Products\EngineeringReference::ID_META_KEY, true ) !== $entry['engineering_id'] || ! is_array( $latest[ $id ] ?? null ) ) {
					throw new RuntimeException( 'Cable identity or facts changed during the migration.' );
				}
				if ( 'apply' === $action && $current === $entry['before'] && $current !== $entry['after'] && $latest[ $id ]['product_revision'] !== $entry['product_revision'] ) {
					throw new RuntimeException( 'Cable product revision changed during the migration.' );
				}
				if ( 'verify' !== $action && $current !== $target ) {
					update_post_meta( $id, $key, wp_slash( $target ), $current );
					wc_delete_product_transients( $id );
					if ( get_post_meta( $id, $key, true ) !== $target || $protected( $id ) !== $entry['protected'] ) {
						throw new RuntimeException( 'Cable readback failed; retain this receipt.' );
					}
					++$written;
					$current = $target;
				}
				$state = $entry['before'] === $entry['after'] ? 'unchanged' : ( $current === $entry['after'] ? 'verified' : 'restored' );
				if ( 'restored' !== $state && null === \Linker\Commerce\Products\Publication\CableFacts::projection( $id, \Linker\Commerce\Products\Publication::manifest() ) ) {
					throw new RuntimeException( 'Current cable projection failed verification.' );
				}
				$states[] = array(
					'product_id'     => $id,
					'engineering_id' => $product['engineering_id'],
					'status'         => $state,
				);
			}
			$changed_states = array_diff( array_column( $states, 'status' ), array( 'unchanged' ) );
			if ( 'verify' === $action && count( array_unique( $changed_states ) ) > 1 ) {
				throw new RuntimeException( 'Cable references are in mixed receipt states.' );
			}
			$fresh = \Linker\Commerce\Products\Publication::manifest();
			if ( 'verify' === $action ) {
				$feed = \Linker\Commerce\Products\EngineeringFeed::feed();
				if ( ( $feed['source_revision'] ?? null ) !== $fresh['source_revision'] || ! is_array( $feed['overlay'] ?? null ) ) {
					throw new RuntimeException( 'Engineering feed and current publication differ.' );
				}
				foreach ( $products as $id => $product ) {
					$matches    = array_values( array_filter( $feed['overlay'], static fn ( array $row ): bool => ( $row['canonical_product_id'] ?? null ) === $id && ( $row['id'] ?? null ) === $product['engineering_id'] ) );
					$projection = \Linker\Commerce\Products\Publication\CableFacts::projection( $id, $fresh );
					if ( 1 !== count( $matches ) || null === $projection || \Linker\Commerce\Products\Publication::revision( $matches[0]['cable_facts'] ?? null ) !== \Linker\Commerce\Products\Publication::revision( $projection ) ) {
						throw new RuntimeException( 'Engineering feed cable facts do not match the current projection.' );
					}
				}
			}
			$result = array(
				'action'          => $action,
				'source_revision' => $fresh['source_revision'],
				'changes'         => $written,
				'products'        => $states,
			);
		}
		echo '@@548-cable-reference-currents@@' . wp_json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '548-cable-reference-currents-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

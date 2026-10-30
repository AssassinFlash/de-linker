<?php
/**
 * Guarded one-time projection of reviewed installation facts into Woo metadata.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI, never a runtime source.
		$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		if ( ! is_array( $request ) || ! in_array( $request['action'] ?? null, array( 'preview', 'apply', 'rollback', 'verify', 'refresh' ), true ) ) {
			throw new RuntimeException( 'Unknown installation-facts action.' );
		}

		$key             = \Linker\Commerce\Products\Publication\InstallationFacts::META_KEY;
		$site            = home_url();
		$manifest        = \Linker\Commerce\Products\Publication::manifest();
		$documents       = static function ( int $id, array $publication ): array {
			$result = array();
			foreach ( $publication['documents'] as $row ) {
				if ( ! in_array( $id, $row['product_ids'], true ) ) {
					continue;
				}
				$result[ $row['document_id'] ] = array(
					'document_id'       => $row['document_id'],
					'document_revision' => $row['document_revision'],
					'blob_sha256'       => $row['blob_sha256'],
					'url'               => $row['url'],
				);
			}
			ksort( $result );
			return $result;
		};
		$protected       = static function ( int $id ): string {
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
		$current_meta    = static function ( int $id ) use ( $key ): array {
			return array(
				'exists' => metadata_exists( 'post', $id, $key ),
				'value'  => get_post_meta( $id, $key, true ),
			);
		};
		$same_meta       = static fn( array $current, bool $exists, mixed $value ): bool => $current['exists'] === $exists && ( ! $exists || $current['value'] === $value );
		$assert_product  = static function ( int $id, array $entry, array $publication, bool $check_revision, ?array $expected_source_documents = null, ?array $expected_product_documents = null ) use ( $documents ): array {
			if ( \Linker\Commerce\Products\Publication::canonical_id( $id ) !== $id || ! \Linker\Commerce\Products\Publication::is_published( $id ) ) {
				throw new RuntimeException( 'Only current canonical published Woo products may be migrated.' );
			}
			$product = wc_get_product( $id );
			if ( ! $product instanceof WC_Product || $product->get_attribute( 'pa_model' ) !== $entry['model'] ) {
				throw new RuntimeException( esc_html( "Model identity changed for {$id}." ) );
			}
			$rows = array_column( $publication['products'], null, 'product_id' );
			$row  = $rows[ $id ] ?? null;
			if ( ! is_array( $row ) || ! isset( $entry['product_revision'] ) ) {
				throw new RuntimeException( esc_html( "Current publication is missing {$id}." ) );
			}
			if ( $check_revision && $row['product_revision'] !== $entry['product_revision'] ) {
				throw new RuntimeException( esc_html( "Product revision changed for {$id}." ) );
			}
			$current_documents = $documents( $id, $publication );
			if ( null !== $expected_product_documents && $current_documents !== $expected_product_documents ) {
				throw new RuntimeException( esc_html( "Associated source documents changed for {$id}." ) );
			}
			if ( null !== $expected_source_documents ) {
				foreach ( $expected_source_documents as $document_id => $identity ) {
					if ( ( $current_documents[ $document_id ] ?? null ) !== $identity ) {
						throw new RuntimeException( esc_html( "Installation source document changed for {$id}/{$document_id}." ) );
					}
				}
			}
			return $row;
		};
		$source_identity = static function ( array $items ): array {
			$result = array();
			foreach ( $items as $item ) {
				$source   = $item['source'];
				$result[] = array(
					'item_id'           => $item['id'],
					'document_id'       => $source['document_id'],
					'document_revision' => $source['document_revision'],
					'blob_sha256'       => $source['blob_sha256'],
					'page'              => $source['page'],
					'quote'             => $source['quote'],
				);
			}
			return $result;
		};
		$json_value      = static function ( mixed $value ): mixed {
			$encoded = wp_json_encode( $value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
			if ( ! is_string( $encoded ) ) {
				throw new RuntimeException( 'Cannot canonicalize installation-facts JSON.' );
			}
			return json_decode( $encoded, true, 512, JSON_THROW_ON_ERROR );
		};

		$action = $request['action'];
		if ( 'refresh' === $action ) {
			// Read-only: report what the current publication would pin, so the
			// plan can be re-frozen with the same guard the preview applies.
			$plan = $request['plan'] ?? null;
			if ( ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || ! is_array( $plan['products'] ?? null ) ) {
				throw new RuntimeException( 'Unsupported installation-facts plan.' );
			}
			$pinned = array();
			foreach ( $plan['products'] as $id => $entry ) {
				$id = (int) $id;
				if ( $id < 1 || ! is_array( $entry ) || ! is_string( $entry['model'] ?? null ) ) {
					throw new RuntimeException( 'Each planned product needs its model.' );
				}
				if ( \Linker\Commerce\Products\Publication::canonical_id( $id ) !== $id || ! \Linker\Commerce\Products\Publication::is_published( $id ) ) {
					throw new RuntimeException( 'Only current canonical published Woo products may be refreshed.' );
				}
				$product = wc_get_product( $id );
				if ( ! $product instanceof WC_Product || $product->get_attribute( 'pa_model' ) !== $entry['model'] ) {
					throw new RuntimeException( esc_html( "Model identity changed for {$id}." ) );
				}
				$rows = array_column( $manifest['products'], null, 'product_id' );
				$row  = $rows[ $id ] ?? null;
				if ( ! is_array( $row ) ) {
					throw new RuntimeException( esc_html( "Current publication is missing {$id}." ) );
				}
				$documents = array();
				foreach ( $manifest['documents'] as $document ) {
					if ( in_array( $id, $document['product_ids'], true ) ) {
						$documents[ $document['document_id'] ] = array(
							'document_revision' => $document['document_revision'],
							'blob_sha256'       => $document['blob_sha256'],
						);
					}
				}
				$pinned[ $id ] = array(
					'product_revision' => $row['product_revision'],
					'documents'        => $documents,
				);
			}
			$result = array(
				'schema_version'   => 1,
				'site'             => $site,
				'source_revision'  => $manifest['source_revision'],
				'products'         => $pinned,
			);
			echo '@@548-installation-facts@@' . wp_json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
			return;
		} elseif ( 'preview' === $action ) {
			$plan = $request['plan'] ?? null;
			if ( ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || ! is_array( $plan['products'] ?? null ) ) {
				throw new RuntimeException( 'Unsupported installation-facts plan.' );
			}
			$receipt = array(
				'schema_version' => 1,
				'site'           => $site,
				'products'       => array(),
			);
			foreach ( $plan['products'] as $id => $entry ) {
				$id = (int) $id;
				if ( $id < 1 || ! is_array( $entry ) || ! is_string( $entry['model'] ?? null ) || ! is_string( $entry['product_revision'] ?? null ) || ! is_array( $entry['items'] ?? null ) || array() === $entry['items'] ) {
					throw new RuntimeException( 'Each planned product needs its model, revision and at least one installation fact.' );
				}
				$row   = $assert_product( $id, $entry, $manifest, true );
				$items = array();
				foreach ( $entry['items'] as $installation ) {
					if ( ! is_array( $installation ) ) {
						throw new RuntimeException( esc_html( "Invalid installation fact for {$id}." ) );
					}
					$items[] = \Linker\Commerce\Products\Publication\InstallationFacts::bind( $id, $installation, $manifest );
				}
				$stored_items = $json_value( $items );
				if ( ! is_array( $stored_items ) ) {
					throw new RuntimeException( 'Installation facts did not project as an item list.' );
				}
				$after           = array(
					'schema_version' => 1,
					'items'          => $stored_items,
				);
				$before          = $current_meta( $id );
				$product_docs    = $documents( $id, $manifest );
					$source_docs = array();
				foreach ( $items as $item ) {
					if ( ! isset( $product_docs[ $item['source']['document_id'] ] ) ) {
						throw new RuntimeException( esc_html( "Installation source is not one of the current documents for {$id}." ) );
					}
						$source_docs[ $item['source']['document_id'] ] = $product_docs[ $item['source']['document_id'] ];
				}
					ksort( $source_docs );
				$receipt['products'][ $id ] = array(
					'model'             => $entry['model'],
					'product_revision'  => $row['product_revision'],
					'before_exists'     => $before['exists'],
					'before'            => $before['value'],
					'after'             => $after,
					'after_hash'        => \Linker\Commerce\Products\Publication::revision( $after ),
					'protected'         => $protected( $id ),
					'documents'         => $source_docs,
					'product_documents' => $product_docs,
					'sources'           => $source_identity( $items ),
				);
			}
			$receipt['changes']         = count( array_filter( $receipt['products'], static fn( array $entry ): bool => ! $entry['before_exists'] || $entry['before'] !== $entry['after'] ) );
			$receipt['source_revision'] = $manifest['source_revision'];
		} else {
			$receipt = $request['receipt'] ?? null;
			if ( ! is_array( $receipt ) || 1 !== ( $receipt['schema_version'] ?? null ) || ! is_array( $receipt['products'] ?? null ) || $receipt['site'] !== $site ) {
				throw new RuntimeException( 'Receipt belongs to another site or has an unsupported shape.' );
			}
			$original_source_revision = $receipt['source_revision'] ?? null;
			if ( ! is_string( $original_source_revision ) ) {
				throw new RuntimeException( 'Receipt has no original source revision.' );
			}
			// Every guarded action starts from a fresh current authority read.
			$manifest = \Linker\Commerce\Products\Publication::manifest();

			if ( 'verify' === $action ) {
				$verified = array();
				$failed   = false;
				$states   = array();
				foreach ( $receipt['products'] as $id => $entry ) {
					$id = (int) $id;
					try {
						$assert_product( $id, $entry, $manifest, false, $entry['documents'], $entry['product_documents'] );
						if ( $protected( $id ) !== $entry['protected'] ) {
							throw new RuntimeException( 'Protected Woo state changed.' );
						}
						$current = $current_meta( $id );
						if ( $same_meta( $current, true, $entry['after'] ) ) {
							if ( \Linker\Commerce\Products\Publication::revision( $entry['after'] ) !== $entry['after_hash'] ) {
								throw new RuntimeException( 'After metadata differs from its receipt hash.' );
							}
							$projection = \Linker\Commerce\Products\Publication\InstallationFacts::projection( $id, $manifest );
							if (
								! is_array( $projection )
								|| 'documented' !== $projection['status']
								|| \Linker\Commerce\Products\Publication::revision( $json_value( $projection['items'] ) ) !== \Linker\Commerce\Products\Publication::revision( $entry['after']['items'] )
							) {
								throw new RuntimeException( 'Canonical installation projection is unresolved or differs.' );
							}
							$item       = \Linker\Commerce\Products\EngineeringFeed::item( $id, $manifest );
							$feed_facts = is_array( $item ) ? ( $item['installation_facts'] ?? null ) : null;
							if (
								! is_array( $item )
								|| ! is_array( $feed_facts )
								|| \Linker\Commerce\Products\Publication::revision( $json_value( $feed_facts ) ) !== \Linker\Commerce\Products\Publication::revision( $json_value( $projection ) )
							) {
								throw new RuntimeException( 'Engineering feed installation facts differ.' );
							}
							$states[]   = 'applied';
							$verified[] = array(
								'status'          => 'verified',
								'item_count'      => count( $projection['items'] ),
								'source_identity' => $source_identity( $projection['items'] ),
							);
						} elseif ( $same_meta( $current, $entry['before_exists'], $entry['before'] ) ) {
							$states[]   = 'restored';
							$verified[] = array(
								'status'          => 'restored',
								'item_count'      => 0,
								'source_identity' => array(),
							);
						} else {
							throw new RuntimeException( 'Raw installation metadata matches neither receipt state.' );
						}
					} catch ( Throwable $error ) {
						$failed     = true;
						$verified[] = array(
							'status'          => 'failed',
							'item_count'      => 0,
							'source_identity' => array(),
							'error'           => $error->getMessage(),
						);
					}
				}
				if ( array() !== $states && count( array_unique( $states ) ) !== 1 ) {
					$failed = true;
					foreach ( $verified as &$entry ) {
						$entry['status'] = 'failed';
						$entry['error']  = 'Receipt products are in mixed applied/restored states.';
					}
					unset( $entry );
				}
				$fresh = \Linker\Commerce\Products\Publication::manifest();
				if ( ! $failed && 'restored' === ( $states[0] ?? null ) && $fresh['source_revision'] !== $original_source_revision ) {
					$failed = true;
					foreach ( $verified as &$entry ) {
						$entry['status'] = 'failed';
						$entry['error']  = 'Restored source revision differs from the receipt.';
					}
					unset( $entry );
				}
				$receipt['products']        = $verified;
				$receipt['changes']         = 0;
				$receipt['source_revision'] = $fresh['source_revision'];
				echo '@@548-installation-facts@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
				if ( $failed ) {
					throw new RuntimeException( 'Installation-facts verification failed.' );
				}
				return;
			}

			// Every receipt preimage is checked before any write.
			foreach ( $receipt['products'] as $id => $entry ) {
				$id = (int) $id;
				$assert_product( $id, $entry, $manifest, 'apply' === $action, $entry['documents'], $entry['product_documents'] );
				if ( $protected( $id ) !== $entry['protected'] || \Linker\Commerce\Products\Publication::revision( $entry['after'] ) !== $entry['after_hash'] ) {
					throw new RuntimeException( esc_html( "Concurrent or corrupt receipt state for {$id}." ) );
				}
				$current = $current_meta( $id );
				if ( ! $same_meta( $current, $entry['before_exists'], $entry['before'] ) && ! $same_meta( $current, true, $entry['after'] ) ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id}; receipt cannot overwrite it." ) );
				}
			}

			$written = 0;
			foreach ( $receipt['products'] as $id => $entry ) {
				$id      = (int) $id;
				$current = $current_meta( $id );
				if ( 'apply' === $action && $same_meta( $current, true, $entry['after'] ) ) {
					continue;
				}
				if ( 'rollback' === $action && $same_meta( $current, $entry['before_exists'], $entry['before'] ) ) {
					continue;
				}
				if ( $protected( $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Protected Woo state changed before writing {$id}." ) );
				}
				if ( 'apply' === $action ) {
					if ( ! $same_meta( $current, $entry['before_exists'], $entry['before'] ) ) {
						throw new RuntimeException( esc_html( "Meta changed before writing {$id}." ) );
					}
					if ( $entry['before_exists'] ) {
						update_post_meta( $id, $key, wp_slash( $entry['after'] ), $entry['before'] );
					} else {
						add_post_meta( $id, $key, wp_slash( $entry['after'] ), true );
					}
				} else {
					if ( ! $same_meta( $current, true, $entry['after'] ) ) {
						throw new RuntimeException( esc_html( "Applied metadata changed before rollback of {$id}." ) );
					}
					if ( $entry['before_exists'] ) {
						update_post_meta( $id, $key, wp_slash( $entry['before'] ), $entry['after'] );
					} else {
						delete_post_meta( $id, $key, $entry['after'] );
					}
				}
				wc_delete_product_transients( $id );
				$readback = $current_meta( $id );
				$expected = 'apply' === $action ? $entry['after'] : $entry['before'];
				$exists   = 'apply' === $action ? true : (bool) $entry['before_exists'];
				if ( $protected( $id ) !== $entry['protected'] || ! $same_meta( $readback, $exists, $expected ) ) {
					throw new RuntimeException( esc_html( "Readback failed for {$id}; retain receipt for recovery." ) );
				}
				++$written;
			}
			$fresh = \Linker\Commerce\Products\Publication::manifest();
			if ( 'rollback' === $action && $fresh['source_revision'] !== $original_source_revision ) {
				throw new RuntimeException( 'Rollback did not restore the receipt source revision.' );
			}
			$receipt['changes']         = $written;
			$receipt['source_revision'] = $fresh['source_revision'];
		}

		echo '@@548-installation-facts@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '548-installation-facts-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

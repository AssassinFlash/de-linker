<?php
/**
 * Guarded, one-time repair of Woo figures from their already associated PDFs.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI, never a runtime source.
		$request       = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		$key           = \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY;
		$site          = home_url();
		$written       = 0;
		$protect       = static function ( int $id ): string {
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
		$document_urls = static function ( int $id, array $expected ): array {
			$actual = array();
			$urls   = array();
			foreach ( \Linker\Commerce\Products\Publication::manifest()['documents'] as $row ) {
				if ( in_array( $id, $row['product_ids'], true ) ) {
					$actual[ $row['document_id'] ] = $row;
				}
			}
			foreach ( $expected as $doc => $sha ) {
				if ( ( $actual[ $doc ]['blob_sha256'] ?? null ) !== $sha ) {
					throw new RuntimeException( esc_html( "Associated source bytes changed for {$id}/{$doc}." ) );
				}
				$urls[ $doc ] = $actual[ $doc ]['url'];
			}
			return $urls;
		};
		if ( 'preview' === $request['action'] ) {
			$receipt = array(
				'site'     => $site,
				'products' => array(),
			);
			foreach ( $request['plan']['products'] as $id => $patch ) {
				$id = (int) $id;
				if ( \Linker\Commerce\Products\Publication::canonical_id( $id ) !== $id || ! \Linker\Commerce\Products\Publication::is_published( $id ) ) {
					throw new RuntimeException( 'Only current canonical published Woo products may be prepared.' );
				}
				$product = wc_get_product( $id );
				if ( ! $product instanceof WC_Product || $product->get_attribute( 'pa_model' ) !== $patch['model'] ) {
					throw new RuntimeException( esc_html( "Model identity changed for {$id}." ) );
				}
				$urls = $document_urls( $id, $patch['documents'] );
				if ( isset( $patch['package'] ) ) {
					$items    = $request['plan']['package_contents'][ $patch['package'] ];
					$manifest = \Linker\Commerce\Products\Publication::manifest();
					$contents = array();
					foreach ( $items as $item ) {
						if ( ! isset( $urls[ $item['source']['document_id'] ] ) ) {
							throw new RuntimeException( esc_html( "Missing reviewed package document for {$id}." ) );
						}
						$contents[] = \Linker\Commerce\Products\Publication\PackageContents::bind( $id, $item, $manifest, true );
					}
					$after  = array(
						'schema_version' => 1,
						'items'          => $contents,
					);
					$before = get_post_meta( $id, \Linker\Commerce\Products\Publication\PackageContents::META_KEY, true );
					if ( '' !== $before && $before !== $after ) {
						throw new RuntimeException( esc_html( "Review existing package contents for {$id}." ) );
					}
					$receipt['products'][ $id ] = array(
						'package'   => true,
						'before'    => $before,
						'after'     => $after,
						'protected' => $protect( $id ),
						'documents' => $patch['documents'],
					);
					continue;
				}
				$before = get_post_meta( $id, $key, true );
				$raw    = is_string( $before ) ? json_decode( $before, true, 512, JSON_THROW_ON_ERROR ) : $before;
				if ( ! is_array( $raw ) ) {
					throw new RuntimeException( 'Unreadable existing Woo figures.' );
				}
				foreach ( $patch['figures'] as $field => $change ) {
					if ( isset( $change['set']['citation']['document_id'] ) ) {
						$doc = $change['set']['citation']['document_id'];
						if ( ! isset( $urls[ $doc ] ) ) {
							throw new RuntimeException( esc_html( "Unverified citation for {$id}/{$field}." ) );
						}
						$change['set']['citation'] = array(
							'url'  => $urls[ $doc ],
							'page' => $change['set']['citation']['page'],
						);
					}
					$existing = $raw[ $field ] ?? null;
					$matches  = is_array( $existing );
					foreach ( $change['set'] + ( $change['expect'] ?? array() ) as $name => $value ) {
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
				$meta_key = empty( $entry['package'] ) ? $key : \Linker\Commerce\Products\Publication\PackageContents::META_KEY;
				$current  = get_post_meta( (int) $id, $meta_key, true );
				if ( ( $current !== $entry[ $from ] && $current !== $entry[ $to ] ) || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id}; receipt cannot overwrite it." ) );
				}
				$document_urls( (int) $id, $entry['documents'] );
			}
			foreach ( $receipt['products'] as $id => $entry ) {
				$meta_key = empty( $entry['package'] ) ? $key : \Linker\Commerce\Products\Publication\PackageContents::META_KEY;
				$current  = get_post_meta( (int) $id, $meta_key, true );
				if ( $current === $entry[ $to ] ) {
					continue;
				}
				if ( $current !== $entry[ $from ] || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Concurrent edit to {$id} before write." ) );
				}
				// Native metadata events bind the edited facts and enqueue shared preparation.
				if ( ! empty( $entry['package'] ) && '' === $entry[ $to ] ) {
					delete_post_meta( (int) $id, $meta_key, $entry[ $from ] );
				} else {
					update_post_meta( (int) $id, $meta_key, wp_slash( $entry[ $to ] ), $entry[ $from ] );
				}
				wc_delete_product_transients( (int) $id );
				if ( get_post_meta( (int) $id, $meta_key, true ) !== $entry[ $to ] || $protect( (int) $id ) !== $entry['protected'] ) {
					throw new RuntimeException( esc_html( "Readback failed for {$id}; retain receipt for recovery." ) );
				}
				++$written;
			}
		}
		$receipt['changes']         = 'preview' === $request['action'] ? count( array_filter( $receipt['products'], static fn( array $entry ): bool => $entry['before'] !== $entry['after'] ) ) : $written;
		$receipt['source_revision'] = \Linker\Commerce\Products\Publication::manifest()['source_revision'];
		echo '@@615-dc-figures@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '615-dc-figures-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

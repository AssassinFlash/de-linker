<?php
/**
 * Preview and atomically maintain the selected ET / SEC LAN scheme in Woo.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringFeed;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\CompatibilityClaims;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\Publication\InstallationFacts;
use Linker\Commerce\Products\Publication\PackageContents;
use Linker\Commerce\Products\SelectionFacts;

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		global $wpdb, $wp_filter;
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Private JSON transport from the companion native CLI.
		$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
		$action  = $request['action'] ?? '';
		if ( ! in_array( $action, array( 'preview', 'apply', 'rollback', 'verify' ), true ) ) {
			throw new RuntimeException( 'Unknown controller-facts action.' );
		}
		$manifest  = Publication::manifest();
		$keys      = array(
			2409 => array( SelectionFacts::FIGURES_META_KEY, EvidenceBindings::META_KEY, PackageContents::META_KEY, InstallationFacts::META_KEY ),
			1946 => array( CompatibilityClaims::META_KEY ),
			1947 => array( CompatibilityClaims::META_KEY ),
			1948 => array( CompatibilityClaims::META_KEY ),
		);
		$state     = static fn( int $id, string $key ): array => array(
			'exists' => metadata_exists( 'post', $id, $key ),
			'value'  => get_post_meta( $id, $key, true ),
		);
		$same      = static fn( array $current, bool $exists, mixed $value ): bool => $current['exists'] === $exists && ( ! $exists || $current['value'] === $value );
		$json      = static fn( mixed $value ): mixed => json_decode( (string) wp_json_encode( $value ), true );
		$documents = static function ( int $id, array $publication ): array {
			$rows = array();
			foreach ( $publication['documents'] as $doc ) {
				if ( in_array( $id, $doc['product_ids'], true ) ) {
					$rows[ $doc['document_id'] ] = array_intersect_key( $doc, array_flip( array( 'document_id', 'document_revision', 'blob_sha256', 'url' ) ) );
				}
			}
			ksort( $rows );
			return $rows;
		};
		$protected = static function ( int $id ) use ( $keys ): string {
			$product = wc_get_product( $id );
			if ( ! $product instanceof WC_Product ) {
				throw new RuntimeException( 'Current Woo product is missing.' );
			}
			$data = $product->get_data();
			unset( $data['meta_data'] );
			$meta = get_post_meta( $id );
			foreach ( $keys[ $id ] as $key ) {
				unset( $meta[ $key ] );
			}
			return Publication::revision(
				array(
					'product' => $data,
					'meta'    => $meta,
				)
			);
		};
		$record    = static function ( int $id, string $key, mixed $after, array &$receipt ) use ( $state ): void {
			$before                                     = $state( $id, $key );
			$receipt['products'][ $id ]['meta'][ $key ] = array(
				'before_exists' => $before['exists'],
				'before'        => $before['value'],
				'after'         => $after,
				'after_sha256'  => Publication::revision( $after ),
			);
		};
		$input     = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		if ( ! is_array( $input ) ) {
			throw new RuntimeException( 'Reviewed compatibility input is missing.' );
		}
		if ( 'preview' === $action ) {
			$plan = $request['plan'] ?? null;
			if ( ! is_array( $plan ) || 1 !== ( $plan['schema_version'] ?? null ) || ! is_array( $plan['controller'] ?? null ) || ! is_array( $plan['requirement'] ?? null ) ) {
				throw new RuntimeException( 'A reviewed controller plan is required.' );
			}
			$controller  = $plan['controller'];
			$requirement = $plan['requirement'];
			if ( 2409 !== ( $controller['product_id'] ?? null ) || 'SEC3000C' !== ( $controller['model'] ?? null ) || array( 1946, 1947, 1948 ) !== ( $requirement['owners'] ?? null ) || 'max_lan_inverters' !== ( $controller['figure_key'] ?? null ) ) {
				throw new RuntimeException( 'The plan differs from the reviewed ET / SEC scope.' );
			}
			$docs = array_column( $manifest['documents'], null, 'document_id' );
			foreach ( $requirement['source_documents'] as $id => $sha ) {
				if ( ! isset( $docs[ $id ] ) || $docs[ $id ]['blob_sha256'] !== $sha ) {
					throw new RuntimeException( 'A reviewed manufacturer original is unavailable or changed.' );
				}
			}
			$doc    = $docs[ $controller['document_id'] ] ?? null;
			$figure = $controller['figure'];
			if ( ! is_array( $doc ) || $doc['blob_sha256'] !== $controller['blob_sha256'] || ! in_array( 2409, $doc['product_ids'], true ) || ! is_array( $figure ) || ! is_int( $figure['value'] ?? null ) || $figure['value'] < 1 || 'units' !== ( $figure['unit'] ?? null ) || ( $figure['citation']['page'] ?? null ) !== $controller['page'] || (string) wp_parse_url( $figure['citation']['url'], PHP_URL_PATH ) !== (string) wp_parse_url( $doc['url'], PHP_URL_PATH ) ) {
				throw new RuntimeException( 'The maintained LAN count needs the reviewed controller original and page.' );
			}
			$matched = array_values( array_filter( $input['requirements'], static fn( array $row ): bool => $row['inverter'] === $requirement['selector'] && $row['kind'] === $requirement['kind'] ) );
			if ( 1 !== count( $matched ) || ( $matched[0]['applicability'] ?? null ) !== array(
				'operating_mode'        => 'grid_connected',
				'topology'              => 'parallel_group',
				'control_network'       => 'lan',
				'controller_product_id' => 2409,
			) || isset( $matched[0]['max_units'] ) ) {
				throw new RuntimeException( 'Exactly one optional, selected-controller LAN declaration is required.' );
			}
			$receipt  = array(
				'schema_version'             => 1,
				'site'                       => home_url(),
				'plan_sha256'                => Publication::revision( $plan ),
				'compatibility_input_sha256' => Publication::revision( $input ),
				'source_revision'            => $manifest['source_revision'],
				'products'                   => array(),
				'changes'                    => array(),
			);
			$products = array_column( $manifest['products'], null, 'product_id' );
			foreach ( $keys as $id => $unused ) {
				if ( ! isset( $products[ $id ] ) || Publication::canonical_id( $id ) !== $id || ! Publication::is_published( $id ) ) {
					throw new RuntimeException( 'A reviewed canonical Woo identity is unavailable.' );
				}
				$receipt['products'][ $id ] = array(
					'model'            => $products[ $id ]['model'],
					'product_revision' => $products[ $id ]['product_revision'],
					'protected_sha256' => $protected( $id ),
					'documents'        => $documents( $id, $manifest ),
					'meta'             => array(),
				);
			}
			if ( $products[2409]['model'] !== $controller['model'] ) {
				throw new RuntimeException( 'The selected controller model changed.' );
			}
			$raw      = get_post_meta( 2409, SelectionFacts::FIGURES_META_KEY, true );
			$figures  = is_string( $raw ) ? json_decode( $raw, true, 512, JSON_THROW_ON_ERROR ) : $raw;
			$bindings = get_post_meta( 2409, EvidenceBindings::META_KEY, true );
			if ( ! is_array( $figures ) || ! is_array( $bindings ) ) {
				throw new RuntimeException( 'Existing controller figure maintenance or bindings are malformed.' );
			}
			foreach ( $figures as $key => $entry ) {
				if ( is_array( $entry ) && isset( $entry['citation'] ) && ( $bindings[ $key ]['figure_revision'] ?? null ) !== Publication::revision( $entry ) ) {
					throw new RuntimeException( 'An unrelated figure needs its own evidence review before this update.' );
				}
			}
			if ( array_diff_key( $bindings, $figures ) ) {
				throw new RuntimeException( 'Unrelated obsolete bindings require separate maintenance.' );
			}
			if ( array_key_exists( $controller['figure_key'], $figures ) && $figures[ $controller['figure_key'] ] !== $figure ) {
				throw new RuntimeException( 'An existing LAN figure differs; this additive plan cannot overwrite it.' );
			}
			$expected_binding = array(
				'document_id'     => $doc['document_id'],
				'blob_sha256'     => $doc['blob_sha256'],
				'figure_revision' => Publication::revision( $figure ),
			);
			if ( array_key_exists( $controller['figure_key'], $figures ) && ( $bindings[ $controller['figure_key'] ] ?? null ) !== $expected_binding ) {
				throw new RuntimeException( 'The existing LAN figure requires an explicit evidence renewal.' );
			}
			$figures[ $controller['figure_key'] ]  = $figure;
			$bindings[ $controller['figure_key'] ] = array(
				'document_id'     => $doc['document_id'],
				'blob_sha256'     => $doc['blob_sha256'],
				'figure_revision' => Publication::revision( $figure ),
			);
			$record( 2409, SelectionFacts::FIGURES_META_KEY, is_string( $raw ) ? wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) : $figures, $receipt );
			$record( 2409, EvidenceBindings::META_KEY, $bindings, $receipt );
			$package      = get_post_meta( 2409, PackageContents::META_KEY, true );
			$package      = '' === $package ? array(
				'schema_version' => 1,
				'items'          => array(),
			) : $package;
			$installation = get_post_meta( 2409, InstallationFacts::META_KEY, true );
			$installation = '' === $installation ? array(
				'schema_version' => 1,
				'items'          => array(),
			) : $installation;
			$append       = static function ( array $existing, array $item ): array {
				if ( 1 !== ( $existing['schema_version'] ?? null ) || ! is_array( $existing['items'] ?? null ) ) {
					throw new RuntimeException( 'Existing maintained items are malformed.' );
				}
				foreach ( $existing['items'] as $old ) {
					if ( $old['id'] === $item['id'] ) {
						if ( $old !== $item ) {
							throw new RuntimeException( 'A maintained item with this identity already differs.' );
						}
						return $existing;
					}
				}
				$existing['items'][] = $item;
				return $existing;
			};
			$record( 2409, PackageContents::META_KEY, $append( $package, PackageContents::bind( 2409, $controller['package_item'], $manifest, true ) ), $receipt );
			$record( 2409, InstallationFacts::META_KEY, $append( $installation, $json( InstallationFacts::bind( 2409, $controller['installation_item'], $manifest ) ) ), $receipt );
			foreach ( $requirement['owners'] as $id ) {
				if ( 1 !== preg_match( '~' . $requirement['selector'] . '~', $products[ $id ]['model'] ) ) {
					throw new RuntimeException( 'An ET model differs from the reviewed selector.' );
				}
				$row = $matched[0];
				unset( $row['inverter'] );
				$row['id'] = hash( 'sha256', '548:selected-et-lan-sec3000c:' . $id );
				$row       = CompatibilityClaims::bind_row( $id, $row, 'requirements', $manifest, true );
				foreach ( $row['documents'] as $source ) {
					if ( ( $requirement['source_documents'][ $source['document_id'] ] ?? null ) !== $source['blob_sha256'] ) {
						throw new RuntimeException( 'The optional scheme cites an unreviewed original.' );
					}
				}
				$claims = get_post_meta( $id, CompatibilityClaims::META_KEY, true );
				if ( ! is_array( $claims ) || 1 !== ( $claims['schema_version'] ?? null ) || ! is_array( $claims['pairs'] ?? null ) || ! is_array( $claims['requirements'] ?? null ) ) {
					throw new RuntimeException( 'The existing Woo declarations must be preserved as a complete object.' );
				}
				$rows                   = $append(
					array(
						'schema_version' => 1,
						'items'          => $claims['requirements'],
					),
					$row
				);
				$claims['requirements'] = $rows['items'];
				$record( $id, CompatibilityClaims::META_KEY, $claims, $receipt );
			}
		} else {
			$receipt = $request['receipt'] ?? null;
			if ( ! is_array( $receipt ) || 1 !== ( $receipt['schema_version'] ?? null ) || home_url() !== ( $receipt['site'] ?? null ) || ! is_array( $receipt['products'] ?? null ) || Publication::revision( $input ) !== ( $receipt['compatibility_input_sha256'] ?? null ) ) {
				throw new RuntimeException( 'The reviewed receipt or compatibility input changed.' );
			}
		}
		$inspect  = static function ( array $publication ) use ( &$receipt, $keys, $documents, $protected, $state, $same ): string {
			if ( array_diff_key( $receipt['products'], $keys ) || array_diff_key( $keys, $receipt['products'] ) ) {
				throw new RuntimeException( 'Receipt product scope changed.' );
			}
			$before = true;
			$after  = true;
			foreach ( $receipt['products'] as $id => $entry ) {
				if ( $documents( $id, $publication ) !== $entry['documents'] || $protected( $id ) !== $entry['protected_sha256'] || array_keys( $entry['meta'] ) !== $keys[ $id ] ) {
					throw new RuntimeException( 'Associated originals, protected Woo state or metadata scope changed.' );
				}
				foreach ( $entry['meta'] as $key => $meta ) {
					if ( Publication::revision( $meta['after'] ) !== $meta['after_sha256'] ) {
						throw new RuntimeException( 'Receipt after-image is corrupt.' );
					}
					$current = $state( $id, $key );
					$before  = $before && $same( $current, $meta['before_exists'], $meta['before'] );
					$after   = $after && $same( $current, true, $meta['after'] );
				}
			}
			return $after ? 'applied' : ( $before ? 'restored' : 'conflict' );
		};
		$observed = $inspect( $manifest );
		if ( 'preview' === $action ) {
			foreach ( $receipt['products'] as $id => $entry ) {
				foreach ( $entry['meta'] as $key => $meta ) {
					if ( ! $meta['before_exists'] || $meta['before'] !== $meta['after'] ) {
						// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Planned receipt fields, not a query.
						$receipt['changes'][] = array(
							'product_id' => $id,
							'meta_key'   => $key, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Planned receipt field only.
						);
					}
				}
			}
		}
		if ( 'conflict' === $observed ) {
			throw new RuntimeException( 'Concurrent metadata changes or a partial state require explicit recovery.' );
		}
		if ( 'apply' === $action || 'rollback' === $action ) {
			$expected_revision = 'apply' === $action ? $receipt['source_revision'] : ( $receipt['applied_source_revision'] ?? null );
			if ( $manifest['source_revision'] !== $expected_revision || ( 'apply' === $action ? 'restored' : 'applied' ) !== $observed ) {
				throw new RuntimeException( 'Review the current source and receipt state before writing; no replay was performed.' );
			}
			// Atomicity is a database capability, not implied by successful setters.
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact table-engine metadata before this bounded transaction.
			$engines = $wpdb->get_col( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (%s, %s, %s)', $wpdb->posts, $wpdb->postmeta, $wpdb->options ) );
			if ( 3 !== count( $engines ) || array( 'INNODB' ) !== array_values( array_unique( array_map( 'strtoupper', $engines ) ) ) ) {
				throw new RuntimeException( 'The native metadata transaction requires InnoDB source tables.' );
			}
			if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
				throw new RuntimeException( 'Could not begin the native metadata transaction.' );
			}
			$deferred = array();
			try {
				foreach ( array( 'added_post_meta', 'updated_post_meta', 'deleted_post_meta' ) as $hook ) {
					foreach ( ( $wp_filter[ $hook ]->callbacks ?? array() ) as $priority => $callbacks ) {
						foreach ( $callbacks as $callback ) {
							$callable = $callback['function'];
							if ( is_array( $callable ) && $callable[0] instanceof \Linker\Commerce\Products\Publication\Module && 'metadata_changed' === $callable[1] ) {
								$deferred[] = array( $hook, $callable, $priority, $callback['accepted_args'] );
								remove_action( $hook, $callable, $priority );
							}
						}
					}
				}
				foreach ( array_keys( $keys ) as $id ) {
					// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Lock the matching product row as well as its metadata.
					$wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE ID = %d FOR UPDATE", $id ) );
					// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Lock only the four reviewed metadata owners before their native setters.
					$wpdb->get_col( $wpdb->prepare( "SELECT meta_id FROM {$wpdb->postmeta} WHERE post_id = %d FOR UPDATE", $id ) );
					wp_cache_delete( $id, 'post_meta' );
				}
				$fresh = Publication::manifest();
				if ( $fresh['source_revision'] !== $expected_revision || $inspect( $fresh ) !== $observed ) {
					throw new RuntimeException( 'The reviewed preimage changed before the transaction acquired its locks.' );
				}
				$receipt['changes'] = array();
				foreach ( $receipt['products'] as $id => $entry ) {
					foreach ( $entry['meta'] as $key => $meta ) {
						$value   = 'apply' === $action ? $meta['after'] : $meta['before'];
						$exists  = 'apply' === $action || $meta['before_exists'];
						$current = $state( $id, $key );
						if ( ! $same( $current, $exists, $value ) ) {
							if ( 'apply' === $action && EvidenceBindings::META_KEY === $key ) {
								throw new RuntimeException( 'The normal figure setter did not produce the reviewed evidence binding.' );
							}
							if ( $exists ) {
								update_post_meta( $id, $key, wp_slash( $value ) );
							} else {
								delete_post_meta( $id, $key );
							}
						}
						if ( ! $same( $state( $id, $key ), $exists, $value ) ) {
							throw new RuntimeException( 'Native setter readback differs from its reviewed image.' );
						}
						if ( ! $meta['before_exists'] || $meta['before'] !== $meta['after'] ) {
							$receipt['changes'][] = array(
								'product_id' => $id,
								'meta_key'   => $key, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Includes a derived binding produced by the native setter.
							);
						}
					}
				}
				$fresh = Publication::manifest();
				if ( $inspect( $fresh ) !== ( 'apply' === $action ? 'applied' : 'restored' ) ) {
					throw new RuntimeException( 'Final protected-state verification failed.' );
				}
				if ( 'apply' === $action ) {
					$item              = EngineeringFeed::item( 2409, $fresh );
					$published_figures = is_array( $item ) ? (array) $item['figures'] : array();
					if ( ! is_array( $item ) || ! isset( $published_figures['max_lan_inverters'] ) || 'documented' !== ( $item['package_contents']['status'] ?? null ) || 'documented' !== ( $item['installation_facts']['status'] ?? null ) ) {
						throw new RuntimeException( 'The actual engineering feed did not publish the maintained facts.' );
					}
					foreach ( array( 1946, 1947, 1948 ) as $id ) {
						$active          = \Linker\Commerce\Products\Compatibility::requirements(
							$receipt['products'][ $id ]['model'],
							'parallel_controller',
							$id,
							$fresh,
							array(
								'operating_mode'        => 'grid_connected',
								'topology'              => 'parallel_group',
								'control_network'       => 'lan',
								'controller_product_id' => 2409,
							)
						);
						$selected_scheme = array_values( array_filter( $active, static fn( array $row ): bool => ( $row['applicability']['controller_product_id'] ?? null ) === 2409 ) );
						if ( 1 !== count( $selected_scheme ) || isset( $selected_scheme[0]['max_units'] ) ) {
							throw new RuntimeException( 'The native compatibility consumer did not expose exactly the optional control scheme.' );
						}
					}
					$receipt['applied_source_revision'] = $fresh['source_revision'];
				} elseif ( $fresh['source_revision'] !== $receipt['source_revision'] ) {
					throw new RuntimeException( 'Rollback did not restore the original publication revision.' );
				}
				// Durable invalidation commits with the facts; scheduling can then be
				// recovered naturally even if the caller exits immediately afterwards.
				update_option( 'linker_publication_pending', true, false );
				if ( false === $wpdb->query( 'COMMIT' ) ) {
					throw new RuntimeException( 'Native transaction commit failed.' );
				}
				$observed = 'apply' === $action ? 'applied' : 'restored';
			} catch ( Throwable $error ) {
				$wpdb->query( 'ROLLBACK' );
				foreach ( array_keys( $keys ) as $id ) {
					wp_cache_delete( $id, 'post_meta' );
				}
				wp_cache_delete( 'linker_publication_pending', 'options' );
				wp_cache_delete( 'notoptions', 'options' );
				throw $error;
			} finally {
				foreach ( $deferred as $callback ) {
					if ( is_callable( $callback[1] ) ) {
						add_action( $callback[0], $callback[1], $callback[2], $callback[3] );
					}
				}
			}
			( new \Linker\Commerce\Products\Publication\PreparationJobs() )->changed();
		}
		if ( 'verify' === $action && 'applied' === $observed ) {
			if ( ( $receipt['applied_source_revision'] ?? null ) !== $manifest['source_revision'] ) {
				throw new RuntimeException( 'Verification cannot adopt a later source revision as the applied revision.' );
			}
		}
		$receipt['observed_source_revision'] = ( 'apply' === $action || 'rollback' === $action ) ? $fresh['source_revision'] : $manifest['source_revision'];
		$receipt['state']                    = $observed;
		echo '@@548-controller-facts@@' . wp_json_encode( $receipt, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} )( '548-controller-facts-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}

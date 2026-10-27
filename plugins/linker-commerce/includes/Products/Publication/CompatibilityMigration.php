<?php
/**
 * One-time pattern expansion into native Woo product declarations.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;

/** Source files are migration inputs only; no runtime caller invokes this class. */
final class CompatibilityMigration {

	public const META_KEY = '_linker_compatibility_migration';

	/**
	 * Make a complete, reviewable before/after plan without writing anything.
	 *
	 * @param array<string,mixed>      $input Retained schema-one compatibility input.
	 * @param string                   $source_sha256 Exact input-file hash.
	 * @param array<string,mixed>|null $manifest Existing current authority read.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When the migration envelope is invalid.
	 */
	public static function plan( array $input, string $source_sha256, ?array $manifest = null ): array {
		if ( 1 !== ( $input['schema_version'] ?? null ) || ! is_array( $input['pairs'] ?? null ) || ! is_array( $input['requirements'] ?? null ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $source_sha256 ) ) {
			throw new \RuntimeException( 'A schema-one migration input and its exact SHA-256 are required.' );
		}
		$manifest ??= Publication::manifest();
		$products   = $manifest['products'];
		$sets       = array();
		$unresolved = array();
		foreach ( array( 'pairs', 'requirements' ) as $kind ) {
			foreach ( $input[ $kind ] as $position => $original ) {
				$owners  = self::matches( $products, (string) ( $original['inverter'] ?? '' ) );
				$targets = 'pairs' === $kind ? self::matches( $products, (string) ( $original['battery'] ?? '' ) ) : array( null );
				if ( array() === $owners || array() === $targets ) {
					$unresolved[] = array(
						'kind'   => $kind,
						'index'  => $position,
						'reason' => 'No current published Woo identity matches this source scope.',
						'source' => $original,
					);
				}
				foreach ( $owners as $owner ) {
					$id            = $owner['product_id'];
					$sets[ $id ] ??= array(
						'schema_version' => 1,
						'pairs'          => array(),
						'requirements'   => array(),
					);
					foreach ( $targets as $target ) {
						$row       = $original;
						$row['id'] = hash( 'sha256', $source_sha256 . ':' . $kind . ':' . $position . ':' . $id . ':' . ( $target['product_id'] ?? '' ) );
						unset( $row['inverter'], $row['battery'] );
						if ( 'pairs' === $kind && null !== $target ) {
							$row['battery_product_id'] = $target['product_id'];
						}
						$row['accessories'] = array();
						$issues             = array();
						foreach ( (array) ( $original['accessories'] ?? array() ) as $accessory ) {
							$matches = self::matches( $products, (string) ( $accessory['model'] ?? '' ) );
							if ( 1 !== count( $matches ) ) {
								$issues[] = 'Accessory identity is absent or ambiguous: ' . (string) ( $accessory['model'] ?? '' );
								continue;
							}
							$row['accessories'][] = array(
								'product_id' => $matches[0]['product_id'],
								'quantity'   => $accessory['quantity'],
								'per'        => $accessory['per'],
							);
						}
						try {
							$bound = CompatibilityClaims::bind_row( $id, $row, $kind, $manifest, true );
							if ( array() === $issues ) {
								$row = $bound;
							}
						} catch ( \RuntimeException $error ) {
							$issues[] = $error->getMessage();
						}
						if ( array() !== $issues ) {
							$row['unresolved']       = $issues;
							$row['migration_source'] = $original;
							$unresolved[]            = array(
								'product_id'     => $id,
								'declaration_id' => $row['id'],
								'reason'         => $issues,
								'source'         => $original,
							);
						}
						$sets[ $id ][ $kind ][] = $row;
					}
				}
			}
		}
		ksort( $sets );
		$changes   = array();
		$preserved = array();
		foreach ( $sets as $id => $after ) {
			$before = self::state( (int) $id );
			if ( $before['exists'] && '' !== $before['value'] && array() !== $before['value'] ) {
				$preserved[] = array(
					'product_id' => $id,
					'reason'     => Publication::revision( $before['value'] ) === Publication::revision( $after ) ? 'already_migrated' : 'existing_woo_declarations_preserved',
				);
				continue;
			}
			$recovery_before = self::state( (int) $id, self::META_KEY );
			if ( $recovery_before['exists'] ) {
				$preserved[] = array(
					'product_id' => $id,
					'reason'     => 'existing_migration_recovery_preserved',
				);
				continue;
			}
			$changes[] = array(
				'product_id'    => $id,
				'meta_key'      => CompatibilityClaims::META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- A review-plan field, not a query.
				'before'        => $before,
				'after'         => $after,
				'recovery_meta' => array(
					'meta_key' => self::META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- A review-plan field.
					'before'   => $recovery_before,
					'after'    => array(
			'schema_version' => 1,
			'source_sha256'  => $source_sha256,
			'before'         => $before,
			'after_sha256'   => Publication::revision( $after ),
				),
				),
			);
		}
		return array(
			'schema_version'       => 1,
			'source_sha256'        => $source_sha256,
			'publication_revision' => $manifest['source_revision'],
			'changes'              => $changes,
			'preserved'            => $preserved,
			'unresolved'           => $unresolved,
		);
	}

	/**
	 * Apply an inspected plan through Woo CRUD, without changing any SKU/status.
	 *
	 * @param array<string,mixed> $plan Complete before/after migration plan.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When the source changed or a native product is absent.
	 */
	public static function apply( array $plan ): array {
		if ( 1 !== ( $plan['schema_version'] ?? null ) || ! is_array( $plan['changes'] ?? null ) || ( $plan['publication_revision'] ?? '' ) !== Publication::manifest()['source_revision'] ) {
			throw new \RuntimeException( 'Current Woo source differs from the reviewed migration plan.' );
		}
		$targets = array();
		foreach ( $plan['changes'] as $change ) {
			$product = wc_get_product( $change['product_id'] );
			if ( self::state( $change['product_id'] ) !== $change['before'] || self::state( $change['product_id'], self::META_KEY ) !== $change['recovery_meta']['before'] || ! $product ) {
				throw new \RuntimeException( 'A migration target changed; no new write started.' );
			}
			$targets[ $change['product_id'] ] = $product;
		}
		$changed = array();
		foreach ( $plan['changes'] as $change ) {
			$product = $targets[ $change['product_id'] ];
			$product->update_meta_data( CompatibilityClaims::META_KEY, $change['after'] );
			$product->update_meta_data( self::META_KEY, $change['recovery_meta']['after'] );
			$product->save();
			$changed[] = $change['product_id'];
		}
		return array(
			'changed_product_ids'    => $changed,
			'source_sha256'          => $plan['source_sha256'],
			'compatibility_revision' => Publication::manifest()['compatibility_revision'],
			'unresolved'             => $plan['unresolved'],
		);
	}

	/**
	 * Restore only still-unedited migration writes. Never overwrite later Woo edits.
	 *
	 * @param bool $dry_run Preview by default.
	 * @return array<string,mixed>
	 */
	public static function rollback( bool $dry_run = true ): array {
		$result = array(
			'changes'   => array(),
			'preserved' => array(),
		);
		$ids    = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ),
				'posts_per_page'              => -1,
				'fields'                      => 'ids',
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'meta_key'                    => self::META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Explicit native migration recovery.
			)
		); // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Explicit bounded migration recovery.
		foreach ( $ids as $id ) {
			$marker = get_post_meta( (int) $id, self::META_KEY, true );
			if ( ! is_array( $marker ) || 1 !== ( $marker['schema_version'] ?? null ) || ! is_array( $marker['before'] ?? null ) || Publication::revision( get_post_meta( (int) $id, CompatibilityClaims::META_KEY, true ) ) !== ( $marker['after_sha256'] ?? '' ) ) {
				$result['preserved'][] = (int) $id;
				continue;
			}
			$result['changes'][] = array(
				'product_id'    => (int) $id,
				'before'        => self::state( (int) $id ),
				'after'         => $marker['before'],
				'recovery_meta' => array(
					'before' => self::state( (int) $id, self::META_KEY ),
					'after'  => array(
						'exists' => false,
						'value'  => '',
					),
				),
			);
			if ( ! $dry_run ) {
				$product = wc_get_product( (int) $id );
				if ( ! $product ) {
					continue;
				}
				if ( $marker['before']['exists'] ) {
					$product->update_meta_data( CompatibilityClaims::META_KEY, $marker['before']['value'] );
				} else {
					$product->delete_meta_data( CompatibilityClaims::META_KEY );
				}
				$product->delete_meta_data( self::META_KEY );
				$product->save();
			}
		}
		return $result;
	}

	/**
	 * Native declaration data.
	 *
	 * @param int    $id Canonical product ID.
	 * @param string $key Native declaration or operational recovery meta.
	 * @return array{exists:bool,value:mixed}
	 */
	private static function state( int $id, string $key = CompatibilityClaims::META_KEY ): array {
		return array(
			'exists' => metadata_exists( 'post', $id, $key ),
			'value'  => get_post_meta( $id, $key, true ),
		);
	}

	/**
	 * Expand a migration pattern only against current canonical Woo identities.
	 *
	 * @param list<array<string,mixed>> $products Current products.
	 * @param string                    $pattern One-time input pattern, never stored as runtime identity.
	 * @return list<array<string,mixed>>
	 */
	private static function matches( array $products, string $pattern ): array {
		return array_values( array_filter( $products, static fn( array $p ): bool => '' !== $pattern && 1 === preg_match( '{' . $pattern . '}', (string) $p['model'] ) ) );
	}
}

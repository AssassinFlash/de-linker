<?php
/**
 * Woo-maintained manufacturer declarations and their current document proof.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;

/** Canonical product IDs are the maintenance identity; model patterns are derived. */
final class CompatibilityClaims {

	public const META_KEY = '_linker_compatibility_claims';

	/**
	 * Project this same authority assembly without recursively reading a manifest.
	 *
	 * @param list<array<string,mixed>> $products Current canonical products.
	 * @param list<array<string,mixed>> $documents Current allowed documents.
	 * @return array<string,mixed>|null Null means malformed Woo maintenance data.
	 * @throws \RuntimeException Handled per scope to withdraw invalid claims.
	 */
	public static function projection( array $products, array $documents ): ?array {
		$manifest = array(
			'products'  => $products,
			'documents' => $documents,
		);
		$index    = array_column( $products, null, 'product_id' );
		$rows     = array(
			'pairs'        => array(),
			'requirements' => array(),
		);
		$blocked  = array();
		foreach ( $index as $owner => $product ) {
			$claims = get_post_meta( (int) $owner, self::META_KEY, true );
			if ( '' === $claims || array() === $claims ) {
				continue;
			}
			if ( ! self::shape( $claims ) ) {
				return null;
			}
			foreach ( array( 'pairs', 'requirements' ) as $kind ) {
				foreach ( $claims[ $kind ] as $row ) {
					$target = 'pairs' === $kind && is_array( $row ) ? ( $row['battery_product_id'] ?? 0 ) : 0;
					$key    = $owner . ':' . (int) $target;
					try {
						if ( ! is_array( $row ) || ! empty( $row['unresolved'] ) ) {
							throw new \RuntimeException( 'Declaration identity or migration evidence is unresolved.' );
						}
						$valid                            = self::bind_row( (int) $owner, $row, $kind, $manifest, false );
						$projected                        = $valid;
						$projected['inverter']            = self::pattern( (string) $product['model'] );
						$projected['inverter_product_id'] = (int) $owner;
						if ( 'pairs' === $kind ) {
							$projected['battery'] = self::pattern( (string) $index[ $target ]['model'] );
						}
						$projected['documents']   = array_map(
							static fn( array $doc ): array => array_filter(
								array(
									'url'  => $doc['url'],
									'page' => $doc['page'] ?? null,
								),
								static fn( mixed $value ): bool => null !== $value
							),
							$valid['documents']
						);
						$projected['accessories'] = array_map(
							static fn( array $part ): array => array(
								'product_id' => $part['product_id'],
								'model'      => self::pattern( (string) $index[ $part['product_id'] ]['model'] ),
								'quantity'   => $part['quantity'],
								'per'        => $part['per'],
							),
							$valid['accessories']
						);
						unset( $projected['id'] );
						$rows[ $kind ][] = array(
							'scope' => $key,
							'owner' => $owner,
							'row'   => $projected,
						);
					} catch ( \RuntimeException $error ) {
						// An invalid restrictive claim must not disappear and leave a
						// less restrictive overlapping claim as a new release.
						$blocked[ 'requirements' === $kind || ! is_int( $target ) || $target < 1 ? $owner . ':*' : $key ] = true;
					}
				}
			}
		}
		$result = array(
			'schema_version' => 1,
			'pairs'          => array(),
			'requirements'   => array(),
		);
		foreach ( $rows as $kind => $entries ) {
			foreach ( $entries as $entry ) {
				if ( 'not_released' === ( $entry['row']['verdict'] ?? null ) || ( ! isset( $blocked[ $entry['scope'] ] ) && ! isset( $blocked[ $entry['owner'] . ':*' ] ) ) ) {
					$result[ $kind ][ Publication::revision( $entry['row'] ) ] = $entry['row'];
				}
			}
			ksort( $result[ $kind ] );
			$result[ $kind ] = array_values( $result[ $kind ] );
		}
		$result['version'] = Publication::revision( $result );
		return $result;
	}

	/**
	 * Validate a claim, binding bytes only on an explicit editor/migration action.
	 *
	 * @param int                 $owner Canonical inverter product.
	 * @param array<string,mixed> $row Maintained declaration.
	 * @param string              $kind pairs or requirements.
	 * @param array<string,mixed> $manifest Current Woo authority.
	 * @param bool                $bind Explicitly confirm the currently displayed source bytes.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When identity, evidence or declaration shape is unresolved.
	 */
	public static function bind_row( int $owner, array $row, string $kind, array $manifest, bool $bind ): array {
		$products = array_column( $manifest['products'], null, 'product_id' );
		$docs     = array_column( $manifest['documents'], null, 'document_id' );
		if ( ! isset( $products[ $owner ] ) || '' === ( $products[ $owner ]['model'] ?? '' ) || ! is_string( $row['id'] ?? null ) || '' === $row['id'] ) {
			throw new \RuntimeException( 'A published canonical product and declaration identity are required.' );
		}
		$result  = array( 'id' => $row['id'] );
		$related = array( $owner );
		if ( 'pairs' === $kind ) {
			$target = $row['battery_product_id'] ?? null;
			if ( ! is_int( $target ) || ! isset( $products[ $target ] ) || '' === ( $products[ $target ]['model'] ?? '' ) || ! in_array( $row['verdict'] ?? null, array( 'released', 'released_with_accessory', 'not_released' ), true ) ) {
				throw new \RuntimeException( 'The battery must be a current canonical Woo product with an explicit verdict.' );
			}
			$result['battery_product_id'] = $target;
			$result['verdict']            = $row['verdict'];
			$related[]                    = $target;
			if ( isset( $row['modules'] ) ) {
				$range = $row['modules'];
				if ( ! is_array( $range ) || ! self::positive( $range['min'] ?? null ) || ! self::positive( $range['max'] ?? null ) || $range['min'] > $range['max'] ) {
					throw new \RuntimeException( 'An explicit positive module-count interval is required.' );
				}
				$result['modules'] = array(
					'min' => $range['min'],
					'max' => $range['max'],
				);
			}
		} else {
			if ( ! in_array( $row['kind'] ?? null, array( 'meter', 'backup', 'parallel_controller' ), true ) || ! is_bool( $row['included'] ?? null ) ) {
				throw new \RuntimeException( 'A requirement kind and explicit included status are required.' );
			}
			$result['kind']     = $row['kind'];
			$result['included'] = $row['included'];
			foreach ( array( 'phase', 'max_units' ) as $field ) {
				if ( isset( $row[ $field ] ) ) {
					if ( ! self::positive( $row[ $field ] ) || ( 'phase' === $field && ! in_array( $row[ $field ], array( 1, 3 ), true ) ) ) {
						throw new \RuntimeException( 'Requirement phase/count is invalid.' );
					}
					$result[ $field ] = $row[ $field ];
				}
			}
		}
		$result['conditions'] = array();
		if ( ! is_array( $row['conditions'] ?? null ) ) {
			throw new \RuntimeException( 'Conditions must retain their English and German wording.' );
		}
		foreach ( $row['conditions'] as $condition ) {
			if ( ! is_array( $condition ) || ! is_string( $condition['en'] ?? null ) || ! is_string( $condition['de'] ?? null ) || '' === trim( $condition['en'] ) || '' === trim( $condition['de'] ) ) {
				throw new \RuntimeException( 'Each condition needs English and German text.' );
			}
			$result['conditions'][] = array(
				'en' => $condition['en'],
				'de' => $condition['de'],
			);
		}
		$result['accessories'] = array();
		if ( ! is_array( $row['accessories'] ?? null ) ) {
			throw new \RuntimeException( 'Accessory identities and quantity bases are required.' );
		}
		foreach ( $row['accessories'] as $part ) {
			if ( ! is_array( $part ) || ! is_int( $part['product_id'] ?? null ) || ! isset( $products[ $part['product_id'] ] ) || '' === ( $products[ $part['product_id'] ]['model'] ?? '' ) || ! self::positive( $part['quantity'] ?? null ) || ! in_array( $part['per'] ?? null, array( 'system', 'stack', 'unit' ), true ) ) {
				throw new \RuntimeException( 'An accessory needs a current canonical Woo identity, quantity and per basis.' );
			}
			$related[]               = $part['product_id'];
			$result['accessories'][] = array(
				'product_id' => $part['product_id'],
				'quantity'   => $part['quantity'],
				'per'        => $part['per'],
			);
		}
		if ( 'released_with_accessory' === ( $row['verdict'] ?? null ) && array() === $result['accessories'] ) {
			throw new \RuntimeException( 'An accessory-dependent release cannot omit its accessory.' );
		}
		$result['documents'] = array();
		if ( ! is_array( $row['documents'] ?? null ) || array() === $row['documents'] ) {
			throw new \RuntimeException( 'A manufacturer declaration requires associated hosted evidence.' );
		}
		foreach ( $row['documents'] as $reference ) {
			if ( ! is_array( $reference ) ) {
				throw new \RuntimeException( 'A document reference must be structured.' );
			}
			$id       = $reference['document_id'] ?? DocumentFiles::id( (string) ( $reference['url'] ?? '' ) );
			$document = $docs[ $id ] ?? null;
			$owners   = is_array( $document ) ? array_values( array_intersect( $related, $document['product_ids'] ) ) : array();
			if ( ! is_array( $document ) || array() === $owners || ( isset( $reference['page'] ) && ! self::positive( $reference['page'] ) ) ) {
				throw new \RuntimeException( 'Evidence must be currently public and associated with this declaration\'s products.' );
			}
			$association = $bind ? $owners[0] : ( $reference['product_id'] ?? null );
			if ( ! in_array( $association, $owners, true ) || ( ! $bind && ( ( $reference['blob_sha256'] ?? null ) !== $document['blob_sha256'] || ( $reference['document_revision'] ?? null ) !== $document['document_revision'] ) ) ) {
				throw new \RuntimeException( 'The declaration has not been confirmed against these document bytes and version.' );
			}
			$bound = array(
				'document_id'       => $id,
				'document_revision' => $document['document_revision'],
				'blob_sha256'       => $document['blob_sha256'],
				'product_id'        => $association,
				'url'               => self::url( (string) $document['url'] ),
			);
			if ( isset( $reference['page'] ) ) {
				$bound['page'] = $reference['page'];
			}
			$result['documents'][] = $bound;
		}
		return $result;
	}

	/**
	 * Candidate stored structure.
	 *
	 * @param mixed $value Candidate stored structure.
	 */
	public static function shape( mixed $value ): bool {
		return is_array( $value ) && 1 === ( $value['schema_version'] ?? null ) && is_array( $value['pairs'] ?? null ) && is_array( $value['requirements'] ?? null );
	}

	/**
	 * Native interoperable positive integer.
	 *
	 * @param mixed $value Native interoperable positive integer.
	 */
	private static function positive( mixed $value ): bool {
		return is_int( $value ) && $value > 0 && $value <= 9007199254740991;
	}

	/**
	 * Current Woo model name.
	 *
	 * @param string $model Current Woo model name.
	 */
	private static function pattern( string $model ): string {
		return '^' . preg_quote( $model, '~' ) . '$';
	}

	/**
	 * An already allowed managed technical document.
	 *
	 * @param string $url An already allowed managed technical document.
	 */
	private static function url( string $url ): string {
		return 'https://de-linker.com' . (string) wp_parse_url( $url, PHP_URL_PATH );
	}
}

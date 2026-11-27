<?php
/**
 * Published engineering relationships for the storefront and equipment references.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/** Project the live Woo declarations onto products in the visitor's language. */
final class CompatibilityIndex {

	/** One authority read shared by all renderers in a page request.
	 *
	 * @return array<string,mixed> Publication manifest.
	 */
	public static function manifest(): array {
		static $cache = array();

		return $cache[ Materials::cache_revision() ] ??= Publication::manifest();
	}

	/** Published declarations for the full reference and matrix.
	 *
	 * @param array<string,mixed>|null $manifest Current Woo authority read.
	 * @return array<string,mixed> Pairs and requirements.
	 */
	public static function declarations( ?array $manifest = null ): array {
		static $cache = array();
		$manifest   ??= self::manifest();
		$key          = $manifest['source_revision'];
		if ( ! isset( $cache[ $key ] ) ) {
			$source = EngineeringData::compatibility( $manifest ) ?? array(
				'pairs'        => array(),
				'requirements' => array(),
			);
			$public = array();
			foreach ( $manifest['products'] as $record ) {
				if ( empty( $record['engineering_role'] ) ) {
					$public[ $record['product_id'] ] = true;
				}
			}
			$public_ids = array_keys( $public );
			$pairs    = array();
			$verdicts = array();
			foreach ( $source['pairs'] as $row ) {
				if ( ! isset( $public[ $row['inverter_product_id'] ], $public[ $row['battery_product_id'] ] ) || array_diff( array_column( $row['accessories'], 'product_id' ), $public_ids ) ) {
					continue;
				}
				$pair = $row['inverter_product_id'] . ':' . $row['battery_product_id'];
				$rank = array_search( $row['verdict'], Compatibility::VERDICTS, true );
				if ( false === $rank ) {
					continue;
				}
				$pairs[ $pair ][]  = $row;
				$verdicts[ $pair ] = min( $verdicts[ $pair ] ?? $rank, $rank );
			}
			$source['pairs'] = array();
			foreach ( $pairs as $key_pair => $rows ) {
				foreach ( $rows as $row ) {
					if ( Compatibility::VERDICTS[ $verdicts[ $key_pair ] ] === $row['verdict'] ) {
						$source['pairs'][] = $row;
					}
				}
			}
			$source['requirements'] = array_values( array_filter( $source['requirements'], static fn( array $row ): bool => isset( $public[ $row['inverter_product_id'] ] ) && ! array_diff( array_column( $row['accessories'], 'product_id' ), $public_ids ) ) );
			$cache[ $key ]          = $source;
		}
		return $cache[ $key ];
	}

	/** The labeled standards of a publication-approved certificate.
	 *
	 * @param array<string,mixed> $document Hosted download.
	 * @return list<string> Canonical names.
	 */
	public static function document_standards( array $document ): array {
		if ( 'certificate' !== Materials::document_kind( (string) ( $document['role'] ?? '' ), (string) ( $document['type'] ?? '' ) ) ) {
			return array();
		}
		return self::standards( $document['title'] . ' ' . rawurldecode( basename( $document['url'] ) ) );
	}

	/** Read the canonical grid standards explicitly named in the evidence.
	 *
	 * @param string $text Certificate label or cited figure.
	 * @return list<string> Canonical names.
	 */
	private static function standards( string $text ): array {
		$tokens = array(
			'EN 50549'      => '/\b(?:EN[\s-]*)?50549\b/i',
			'TOR Erzeuger'  => '/\bTOR\b/i',
			'VDE-AR-N 4105' => '/(?:\bVDE[\s-]*(?:AR[\s-]*N[\s-]*)?|\b)4105\b/i',
			'VDE-AR-N 4110' => '/(?:\bVDE[\s-]*(?:AR[\s-]*N[\s-]*)?|\b)4110\b/i',
		);
		$text   = str_replace( '_', ' ', $text );
		return array_keys( array_filter( $tokens, static fn( string $pattern ): bool => 1 === preg_match( $pattern, $text ) ) );
	}

	/** Project grid standards from current downloads and the product's cited certification row.
	 *
	 * @param int                            $product_id Product or language twin.
	 * @param array<int,array<string,mixed>> $downloads Authorized documents of this product.
	 * @param array<string,array<string,mixed>>|null $figures Authorized figures from the same manifest.
	 * @return list<string> Verified standards.
	 */
	public static function grid_standards( int $product_id, array $downloads, ?array $figures = null ): array {
		$standards = array();
		foreach ( $downloads as $document ) {
			$standards = array_merge( $standards, self::document_standards( $document ) );
		}
		$raw = null === $figures ? get_post_meta( Publication::canonical_id( $product_id ), SelectionFacts::FIGURES_META_KEY, true ) : null;
		$raw = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		if ( null === $figures && isset( $raw['certification'] ) ) {
			$figures = Publication::figures_in_manifest( $product_id, self::manifest() );
		}
		$row = $figures['certification'] ?? array();
		if ( is_string( $row['value'] ?? null ) && in_array( $row['citation']['url'] ?? null, array_column( $downloads, 'url' ), true ) ) {
			$standards = array_merge( $standards, self::standards( $row['value'] ) );
		}
		$standards = array_values( array_unique( $standards ) );
		sort( $standards );
		return $standards;
	}

	/** Related equipment and accessories, only within a published manufacturer release.
	 *
	 * @param int                      $product_id Requested locale ID.
	 * @param array<string,mixed>|null $manifest Existing publication read.
	 * @return array{compatible:list<array<string,mixed>>,accessory_for:list<array<string,mixed>>,requirements:list<array<string,mixed>>}
	 */
	public static function for_product( int $product_id, ?array $manifest = null ): array {
		static $cache = array();
		$manifest   ??= self::manifest();
		$locale       = Materials::locale();
		$key          = $manifest['source_revision'] . ':' . $product_id . ':' . $locale;
		if ( isset( $cache[ $key ] ) ) {
			return $cache[ $key ];
		}
		$rows     = array(
			'compatible'    => array(),
			'accessory_for' => array(),
			'requirements'  => array(),
		);
		$source   = Publication::canonical_id( $product_id );
		$products = array_column( $manifest['products'], null, 'product_id' );
		if ( ! isset( $products[ $source ] ) || ! empty( $products[ $source ]['engineering_role'] ) || ! in_array( $product_id, $products[ $source ]['published_locale_ids'], true ) ) {
			return $rows;
		}
		$declarations = self::declarations( $manifest );
		foreach ( $declarations['pairs'] as $pair ) {
			if ( 'not_released' === $pair['verdict'] ) {
				continue;
			}
			$inverter = $pair['inverter_product_id'];
			$battery  = $pair['battery_product_id'];
			if ( in_array( $source, array_column( $pair['accessories'], 'product_id' ), true ) ) {
				foreach ( array(
					'inverter' => $inverter,
					'battery'  => $battery,
				) as $kind => $id ) {
					$target = self::item( $products[ $id ], $locale );
					if ( $target ) {
						$rows['accessory_for'][ $id ] = $target + array( 'kind' => $kind );
					}
				}
			}
			if ( $source !== $inverter && $source !== $battery ) {
				continue;
			}
			$id     = $source === $inverter ? $battery : $inverter;
			$target = self::item( $products[ $id ], $locale );
			if ( ! $target ) {
				continue;
			}
			$target['role']              = $source === $inverter ? 'battery' : 'inverter';
			$target['verdict']           = $pair['verdict'];
			$rows['compatible'][ $id ] ??= $target + array(
				'accessories' => array(),
				'conditions'  => array(),
				'documents'   => array(),
			);
			$item                        = &$rows['compatible'][ $id ];
			foreach ( $pair['accessories'] as $part ) {
				$accessory = self::item( $products[ $part['product_id'] ], $locale );
				if ( $accessory ) {
					$item['accessories'][ $part['product_id'] . ':' . $part['per'] ] = $accessory + $part;
				}
			}
			foreach ( $pair['conditions'] as $condition ) {
				$text                        = Materials::apply_terms( $condition[ $locale ], 'de' === $locale );
				$item['conditions'][ $text ] = $text;
			}
			foreach ( $pair['documents'] as $doc ) {
				$item['documents'][ $doc['url'] . ':' . ( $doc['page'] ?? '' ) ] = $doc;
			}
			unset( $item );
		}
		foreach ( Materials::relationships( $source ) as $relationship ) {
			$id = (int) ( $relationship['target_product_id'] ?? 0 );
			if ( isset( $rows['compatible'][ $id ] ) && in_array( $relationship['status'] ?? '', array( 'listed', 'one_way' ), true ) ) {
				$constraint = Materials::apply_terms( Materials::localized_text( $relationship, 'constraint', $locale ), 'de' === $locale );
				if ( '' !== $constraint ) {
					$rows['compatible'][ $id ]['conditions'][ $constraint ] = $constraint;
				}
			}
		}
		foreach ( $declarations['requirements'] as $rule ) {
			$owner = $rule['inverter_product_id'];
			if ( $owner === $source ) {
				$rows['requirements'][] = $rule;
			}
			if ( in_array( $source, array_column( $rule['accessories'], 'product_id' ), true ) ) {
				$target = self::item( $products[ $owner ], $locale );
				if ( $target ) {
					$rows['accessory_for'][ $owner ] = $target + array( 'kind' => 'inverter' );
				}
			}
		}
		foreach ( $rows['compatible'] as &$item ) {
			foreach ( array( 'conditions', 'documents', 'accessories' ) as $field ) {
				$item[ $field ] = array_values( $item[ $field ] );
			}
		}
		unset( $item );
		foreach ( array( 'compatible', 'accessory_for' ) as $field ) {
			usort( $rows[ $field ], static fn( array $left, array $right ): int => strnatcasecmp( $left['name'], $right['name'] ) );
		}
		$cache[ $key ] = $rows;
		return $rows;
	}

	/** Localized identity and rating of a released model.
	 *
	 * @param array<string,mixed> $record Published manifest row.
	 * @param string              $locale Storefront locale.
	 * @return array<string,mixed> Empty when the target has no published twin.
	 */
	private static function item( array $record, string $locale ): array {
		$id = $record['locale_product_ids'][ $locale ] ?? 0;
		if ( ! $id ) {
			return array();
		}
		$source = $record['product_id'];
		$facts  = SelectionFacts::for_product( $source );
		$rating = array();
		foreach ( array(
			'kW'  => $facts->ac_power_kw,
			'kWh' => $facts->nominal_kwh,
		) as $unit => $value ) {
			if ( is_float( $value ) ) {
				$rating[] = wc_format_localized_decimal( (string) $value ) . ' ' . $unit;
			}
		}
		if ( is_int( $facts->phase ) ) {
			$rating[] = 1 === $facts->phase ? __( 'single-phase', 'linker-commerce' ) : __( 'three-phase', 'linker-commerce' );
		}
		$terms = get_the_terms( $id, 'product_cat' );
		return array(
			'canonical_id' => $source,
			'product_id'   => $id,
			'name'         => html_entity_decode( get_the_title( $id ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
			'url'          => (string) get_permalink( $id ),
			'sku'          => (string) get_post_meta( $source, '_sku', true ),
			'category'     => is_array( $terms ) ? implode( ', ', wp_list_pluck( $terms, 'name' ) ) : '',
			'rating'       => implode( ' · ', $rating ),
		);
	}
}

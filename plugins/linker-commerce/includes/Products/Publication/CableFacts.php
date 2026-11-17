<?php
/**
 * Cited cable identity and condition-specific impedance maintained only in Woo.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/** Invalid or stale typed facts withdraw the cable reference from the feed. */
final class CableFacts {

	public const META_KEY = '_linker_cable_facts';

	/**
	 * Project current metadata only when all fields and original bytes match.
	 *
	 * @param int                 $owner Canonical Woo record.
	 * @param array<string,mixed> $manifest Current publication assembly.
	 * @return array<string,mixed>|null
	 */
	public static function projection( int $owner, array $manifest ): ?array {
		$raw = get_post_meta( $owner, self::META_KEY, true );
		return self::project( $owner, $raw, $manifest );
	}

	/**
	 * Renew versions after a host rewrite without adopting changed source bytes.
	 *
	 * @param int                 $owner Canonical Woo record.
	 * @param array<string,mixed> $manifest Current authority manifest.
	 * @param bool                $dry_run Preview without changing stored facts.
	 * @return int Cable records renewed, not individual citations.
	 */
	public static function renew_unchanged( int $owner, array $manifest, bool $dry_run = false ): int {
		$raw = get_post_meta( $owner, self::META_KEY, true );
		if ( ! is_array( $raw ) ) {
			return 0;
		}
		$documents      = array_column( $manifest['documents'], null, 'document_id' );
		$renew          = static function ( mixed $source ) use ( $owner, $documents ): mixed {
			if ( ! is_array( $source ) || ! is_string( $source['document_id'] ?? null ) ) {
				return $source;
			}
			$document = $documents[ $source['document_id'] ] ?? null;
			if ( is_array( $document ) && ( $source['product_id'] ?? null ) === $owner && ( $source['blob_sha256'] ?? null ) === $document['blob_sha256'] && in_array( $owner, $document['product_ids'], true ) ) {
				$source['document_revision'] = $document['document_revision'];
			}
			return $source;
		};
		$next           = $raw;
		$next['source'] = $renew( $raw['source'] ?? null );
		foreach ( array( 'parameter_sets', 'reference_current_ratings' ) as $group ) {
			if ( ! is_array( $raw[ $group ] ?? null ) ) {
				continue;
			}
			foreach ( $raw[ $group ] as $index => $row ) {
				if ( is_array( $row ) ) {
					$next[ $group ][ $index ]['source'] = $renew( $row['source'] ?? null );
				}
			}
		}
		if ( $next === $raw || null === self::project( $owner, $next, $manifest ) ) {
			return 0;
		}
		if ( ! $dry_run ) {
			update_post_meta( $owner, self::META_KEY, $next );
		}
		return 1;
	}

	/**
	 * Validate a candidate without changing Woo metadata.
	 *
	 * @param int                 $owner Canonical Woo record.
	 * @param mixed               $raw Stored or previewed facts.
	 * @param array<string,mixed> $manifest Current publication assembly.
	 * @return array<string,mixed>|null
	 */
	public static function project( int $owner, mixed $raw, array $manifest ): ?array {
		$keys = array( 'schema_version', 'construction', 'core_count', 'cross_section_mm2', 'conductor_material', 'insulation', 'source', 'parameter_sets' );
		if ( is_array( $raw ) && array_key_exists( 'reference_current_ratings', $raw ) ) {
			$keys[] = 'reference_current_ratings';
		}
		if ( ! is_array( $raw ) || ! self::keys( $raw, $keys ) || 1 !== $raw['schema_version'] || ! in_array( $raw['construction'], array( 'single_conductor', 'multicore_cable' ), true ) || ! is_int( $raw['core_count'] ) || $raw['core_count'] < 1 || $raw['core_count'] > 9007199254740991 || ( 'single_conductor' === $raw['construction'] && 1 !== $raw['core_count'] ) || ! self::number( $raw['cross_section_mm2'], true ) || ! self::text( $raw['conductor_material'] ) || ! self::text( $raw['insulation'] ) || ! is_array( $raw['parameter_sets'] ) || ! array_is_list( $raw['parameter_sets'] ) ) {
			return null;
		}
		$source = self::source( $owner, $raw['source'], $manifest );
		if ( null === $source ) {
			return null;
		}
		$raw['source'] = $source;
		$seen          = array();
		foreach ( $raw['parameter_sets'] as $index => $set ) {
			if ( ! is_array( $set ) || ! self::keys( $set, array( 'id', 'current_kind', 'temperature_c', 'frequency_hz', 'arrangement', 'resistance_ohm_per_km', 'reactance_ohm_per_km', 'resistance_basis', 'source' ) ) || ! is_string( $set['id'] ) || 1 !== preg_match( '/^[A-Za-z][A-Za-z0-9_-]{0,63}$/D', $set['id'] ) || isset( $seen[ $set['id'] ] ) || ! in_array( $set['current_kind'], array( 'dc', 'ac' ), true ) || ! self::number( $set['temperature_c'] ) || ! self::number( $set['resistance_ohm_per_km'], true ) || ! in_array( $set['resistance_basis'], array( 'nominal', 'maximum' ), true ) ) {
				return null;
			}
			if ( 'dc' === $set['current_kind'] && ( null !== $set['frequency_hz'] || null !== $set['reactance_ohm_per_km'] ) ) {
				return null;
			}
			if ( null !== $set['arrangement'] && ! self::text( $set['arrangement'] ) ) {
				return null;
			}
			if ( 'ac' === $set['current_kind'] && ( ! self::number( $set['frequency_hz'], true ) || ! self::number( $set['reactance_ohm_per_km'] ) || $set['reactance_ohm_per_km'] < 0 || ! self::text( $set['arrangement'] ) ) ) {
				return null;
			}
			$evidence = self::source( $owner, $set['source'], $manifest );
			if ( null === $evidence ) {
				return null;
			}
			$seen[ $set['id'] ]                        = true;
			$raw['parameter_sets'][ $index ]['source'] = $evidence;
		}
		if ( array_key_exists( 'reference_current_ratings', $raw ) ) {
			if ( ! is_array( $raw['reference_current_ratings'] ) || ! array_is_list( $raw['reference_current_ratings'] ) ) {
				return null;
			}
			$seen = array();
			foreach ( $raw['reference_current_ratings'] as $index => $rating ) {
				if ( ! is_array( $rating ) || ! self::keys( $rating, array( 'id', 'laying', 'ambient_temperature_c', 'rated_conductor_temperature_c', 'current_a', 'source' ) ) || ! is_string( $rating['id'] ) || 1 !== preg_match( '/^[A-Za-z][A-Za-z0-9_-]{0,63}$/D', $rating['id'] ) || isset( $seen[ $rating['id'] ] ) || ! in_array( $rating['laying'], array( 'single_in_air', 'single_on_surface', 'two_touching_on_surface' ), true ) || ! self::number( $rating['ambient_temperature_c'] ) || ! self::number( $rating['rated_conductor_temperature_c'] ) || ! self::number( $rating['current_a'], true ) ) {
					return null;
				}
				$evidence = self::source( $owner, $rating['source'], $manifest );
				if ( null === $evidence ) {
					return null;
				}
				$seen[ $rating['id'] ]                                = true;
				$raw['reference_current_ratings'][ $index ]['source'] = $evidence;
			}
		}
		return $raw;
	}

	/**
	 * Bind the cited row to the published product and exact retained document.
	 *
	 * @param int                 $owner Canonical record.
	 * @param mixed               $source Stored evidence.
	 * @param array<string,mixed> $manifest Current assembly.
	 * @return array<string,mixed>|null
	 */
	private static function source( int $owner, mixed $source, array $manifest ): ?array {
		if ( ! is_array( $source ) || ! self::keys( $source, array( 'document_id', 'document_revision', 'blob_sha256', 'product_id', 'page', 'quote' ) ) || ! self::text( $source['document_id'] ) || ! is_int( $source['page'] ) || $source['page'] < 1 || $source['page'] > 9007199254740991 || ! self::text( $source['quote'] ) || ( function_exists( 'mb_strlen' ) ? mb_strlen( $source['quote'], 'UTF-8' ) : strlen( $source['quote'] ) ) > 2000 || $owner !== $source['product_id'] ) {
			return null;
		}
		foreach ( $manifest['documents'] as $doc ) {
			if ( $doc['document_id'] === $source['document_id'] && $doc['document_revision'] === $source['document_revision'] && $doc['blob_sha256'] === $source['blob_sha256'] && in_array( $owner, $doc['product_ids'], true ) ) {
				return $source + array( 'url' => 'https://de-linker.com' . (string) wp_parse_url( $doc['url'], PHP_URL_PATH ) );
			}
		}
		return null;
	}

	/**
	 * Exact typed keys; no silently ignored manufacturer conditions.
	 *
	 * @param array<string,mixed> $value Stored object.
	 * @param array<int,string>   $keys Required keys.
	 */
	private static function keys( array $value, array $keys ): bool {
		return count( $value ) === count( $keys ) && array() === array_diff( $keys, array_keys( $value ) );
	}

	/**
	 * Nonempty stored text.
	 *
	 * @param mixed $value Stored text.
	 */
	private static function text( mixed $value ): bool {
		return is_string( $value ) && '' !== trim( $value ) && ( function_exists( 'mb_strlen' ) ? mb_strlen( $value, 'UTF-8' ) : strlen( $value ) ) <= 4096;
	}

	/**
	 * Finite JSON numbers; boolean/string coercion is prohibited.
	 *
	 * @param mixed $value Stored number.
	 * @param bool  $positive Whether strictly positive.
	 */
	private static function number( mixed $value, bool $positive = false ): bool {
		return ( is_int( $value ) || is_float( $value ) ) && is_finite( (float) $value ) && ( ! $positive || $value > 0 );
	}
}

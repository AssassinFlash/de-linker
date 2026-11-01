<?php
/**
 * Pairing an inverter with a battery against the compatibility contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * Join current Woo declarations for exact canonical product identities.
 * Every applicable declaration contributes; the most restrictive verdict wins.
 * Model-only callers must resolve to exactly one current canonical product.
 */
final class Compatibility {

	/**
	 * The three verdicts the contract states, from the most restrictive to
	 * the least.
	 */
	public const VERDICTS = array( 'not_released', 'released_with_accessory', 'released' );

	/**
	 * The verdict of an inverter and a battery model, joined from every pair
	 * that matches them.
	 *
	 * @param string                   $inverter The inverter model (pa_model).
	 * @param string                   $battery  The battery model (pa_model).
	 * @param array<string,mixed>|null $manifest Same current Woo authority read.
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>, accessories: list<array{product_id: int, model: string, quantity: int, per: string}>}|null Null when no pair matches.
	 */
	public static function for_models( string $inverter, string $battery, ?array $manifest = null ): ?array {
		$manifest  ??= Publication::manifest();
		$inverter_id = self::identity( $inverter, $manifest );
		$battery_id  = self::identity( $battery, $manifest );
		return null === $inverter_id || null === $battery_id ? null : self::for_products( $inverter_id, $battery_id, $manifest );
	}

	/**
	 * Join every declaration attached to these exact canonical Woo identities.
	 *
	 * @param int                 $inverter_id Canonical inverter.
	 * @param int                 $battery_id Canonical battery.
	 * @param array<string,mixed> $manifest Current shared authority.
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>, accessories: list<array{product_id: int, model: string, quantity: int, per: string}>}|null
	 */
	private static function answer( int $inverter_id, int $battery_id, array $manifest ): ?array {
		$conditions  = array();
		$documents   = array();
		$accessories = array();
		$verdict     = null;
		foreach ( self::pairs( $manifest ) as $pair ) {
			if ( ( $pair['inverter_product_id'] ?? null ) !== $inverter_id || ( $pair['battery_product_id'] ?? null ) !== $battery_id ) {
				continue;
			}
			$verdict = self::most_restrictive( $verdict, (string) ( $pair['verdict'] ?? '' ) );
			foreach ( (array) ( $pair['conditions'] ?? array() ) as $condition ) {
				if ( is_array( $condition ) && is_string( $condition['en'] ?? null ) ) {
					$conditions[ $condition['en'] ] = array(
						'en' => $condition['en'],
						'de' => is_string( $condition['de'] ?? null ) ? $condition['de'] : $condition['en'],
					);
				}
			}
			foreach ( (array) ( $pair['documents'] ?? array() ) as $document ) {
				if ( is_array( $document ) && is_string( $document['url'] ?? null ) ) {
					$page = $document['page'] ?? null;
					$documents[ $document['url'] . ':' . (string) $page ] = array_filter(
						array(
							'url'  => $document['url'],
							'page' => is_int( $page ) ? $page : null,
						),
						static fn( $value ): bool => null !== $value
					);
				}
			}
			foreach ( (array) ( $pair['accessories'] ?? array() ) as $accessory ) {
				if ( is_array( $accessory ) && is_string( $accessory['model'] ?? null ) ) {
					$accessories[ (string) $accessory['product_id'] . ':' . (string) ( $accessory['per'] ?? '' ) ] = array(
						'product_id' => $accessory['product_id'],
						'model'      => $accessory['model'],
						'quantity'   => (int) ( $accessory['quantity'] ?? 1 ),
						'per'        => (string) ( $accessory['per'] ?? 'system' ),
					);
				}
			}
		}
		if ( null === $verdict ) {
			return null;
		}

		return array(
			'verdict'     => $verdict,
			'conditions'  => array_values( $conditions ),
			'documents'   => array_values( $documents ),
			'accessories' => array_values( $accessories ),
		);
	}

	/**
	 * The verdict for two current canonical Woo products.
	 *
	 * @param int                      $inverter_id Inverter product ID.
	 * @param int                      $battery_id  Battery product ID.
	 * @param array<string,mixed>|null $manifest Same current Woo authority read.
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>, accessories: list<array{product_id: int, model: string, quantity: int, per: string}>}|null
	 */
	public static function for_products( int $inverter_id, int $battery_id, ?array $manifest = null ): ?array {
		$manifest ??= Publication::manifest();
		return self::answer( Publication::canonical_id( $inverter_id ), Publication::canonical_id( $battery_id ), $manifest );
	}

	/**
	 * Current Woo pairs with a known verdict.
	 *
	 * @param array<string,mixed>|null $manifest Same current Woo authority read.
	 * @return list<array<string, mixed>>
	 */
	public static function pairs( ?array $manifest = null ): array {
		$data   = EngineeringData::compatibility( $manifest );
		$pairs  = is_array( $data['pairs'] ?? null ) ? $data['pairs'] : array();
		$usable = array();
		foreach ( $pairs as $pair ) {
			if ( is_array( $pair ) && in_array( $pair['verdict'] ?? '', self::VERDICTS, true ) ) {
				$usable[] = $pair;
			}
		}

		return $usable;
	}

	/**
	 * Requirements for the same canonical Woo inverter identity and kind.
	 *
	 * @param string                   $inverter The inverter model (pa_model).
	 * @param string                   $kind     The requirement kind (meter, parallel_controller).
	 * @param int|null                 $inverter_id Exact Woo identity when the caller has it.
	 * @param array<string,mixed>|null $manifest Same current Woo authority read.
	 * @param array<string,string|int> $context Explicit mode/topology/network/selected controller; absent context never grants a conditional claim.
	 * @return list<array<string, mixed>> The matching entries.
	 */
	public static function requirements( string $inverter, string $kind, ?int $inverter_id = null, ?array $manifest = null, array $context = array() ): array {
		$manifest    ??= Publication::manifest();
		$inverter_id ??= self::identity( $inverter, $manifest );
		$data          = EngineeringData::compatibility( $manifest );
		$entries       = is_array( $data['requirements'] ?? null ) ? $data['requirements'] : array();
		$requirements  = array();
		foreach ( $entries as $entry ) {
			if ( is_array( $entry )
				&& ( $entry['kind'] ?? '' ) === $kind
				&& null !== $inverter_id && ( $entry['inverter_product_id'] ?? null ) === Publication::canonical_id( $inverter_id )
				&& ( ! isset( $entry['applicability'] ) || array() === array_diff_assoc( $entry['applicability'], $context ) )
			) {
				$requirements[] = $entry;
			}
		}

		return $requirements;
	}

	/**
	 * Native declaration data.
	 *
	 * @param string              $model A model-only caller.
	 * @param array<string,mixed> $manifest Current Woo authority.
	 */
	private static function identity( string $model, array $manifest ): ?int {
		$matches = array_values( array_filter( $manifest['products'], static fn( array $product ): bool => ( $product['model'] ?? null ) === $model ) );
		return 1 === count( $matches ) ? $matches[0]['product_id'] : null;
	}

	/**
	 * The more restrictive of two verdicts; a verdict that is not in the
	 * vocabulary loses to the one held.
	 *
	 * @param string|null $held   The verdict held so far, null before the first.
	 * @param string      $joined The verdict that joined it.
	 */
	private static function most_restrictive( ?string $held, string $joined ): string {
		$held_at   = null === $held ? PHP_INT_MAX : array_search( $held, self::VERDICTS, true );
		$joined_at = array_search( $joined, self::VERDICTS, true );
		if ( false === $joined_at ) {
			return (string) $held;
		}

		return self::VERDICTS[ min( (int) $held_at, (int) $joined_at ) ];
	}
}

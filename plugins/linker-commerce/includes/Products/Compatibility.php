<?php
/**
 * Pairing an inverter with a battery against the compatibility contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * Pairing an inverter with a battery against data/compatibility.json
 * (docs/specs/8-engineering-data.md): pairs of model patterns with a verdict,
 * bilingual conditions, documents and accessories. A pattern matches the
 * product model (pa_model) with search semantics, carrying its own anchors.
 *
 * Every pair that matches a combination applies, the way the #14 engine
 * reads the same file: the verdict is the most restrictive one
 * (not_released < released_with_accessory < released), conditions, documents
 * and accessories are joined; a combination no pair matches has no
 * documented release (null).
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
	 * @param string $inverter The inverter model (pa_model).
	 * @param string $battery  The battery model (pa_model).
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>, accessories: list<array{model: string, quantity: int, per: string}>}|null Null when no pair matches.
	 */
	public static function for_models( string $inverter, string $battery ): ?array {
		$conditions  = array();
		$documents   = array();
		$accessories = array();
		$verdict     = null;
		foreach ( self::pairs() as $pair ) {
			if ( ! self::matches( $pair['inverter'] ?? '', $inverter )
				|| ! self::matches( $pair['battery'] ?? '', $battery )
			) {
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
					$accessories[ $accessory['model'] . ':' . (string) ( $accessory['per'] ?? '' ) ] = array(
						'model'    => $accessory['model'],
						'quantity' => (int) ( $accessory['quantity'] ?? 1 ),
						'per'      => (string) ( $accessory['per'] ?? 'system' ),
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
	 * The verdict for two products: their pa_model terms, the way the feed
	 * names them.
	 *
	 * @param int $inverter_id Inverter product ID.
	 * @param int $battery_id  Battery product ID.
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>, accessories: list<array{model: string, quantity: int, per: string}>}|null
	 */
	public static function for_products( int $inverter_id, int $battery_id ): ?array {
		$inverter = self::model( $inverter_id );
		$battery  = self::model( $battery_id );
		if ( null === $inverter || null === $battery ) {
			return null;
		}

		return self::for_models( $inverter, $battery );
	}

	/**
	 * The pairs of the contract, usable ones only: a known verdict.
	 *
	 * @return list<array<string, mixed>>
	 */
	public static function pairs(): array {
		$data   = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
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
	 * The requirements an inverter of one kind carries, the way the #14
	 * engine reads the same file: every requirement entry whose kind equals
	 * and whose inverter pattern matches the model (search semantics, own
	 * anchors).
	 *
	 * @param string $inverter The inverter model (pa_model).
	 * @param string $kind     The requirement kind (meter, parallel_controller).
	 * @return list<array<string, mixed>> The matching entries, in file order.
	 */
	public static function requirements( string $inverter, string $kind ): array {
		$data         = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		$entries      = is_array( $data['requirements'] ?? null ) ? $data['requirements'] : array();
		$requirements = array();
		foreach ( $entries as $entry ) {
			if ( is_array( $entry )
				&& ( $entry['kind'] ?? '' ) === $kind
				&& self::matches( (string) ( $entry['inverter'] ?? '' ), $inverter )
			) {
				$requirements[] = $entry;
			}
		}

		return $requirements;
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

	/**
	 * The product's model (its pa_model term name), null without one.
	 *
	 * @param int $product_id Product ID.
	 */
	private static function model( int $product_id ): ?string {
		$terms = get_the_terms( $product_id, 'pa_model' );
		if ( ! is_array( $terms ) || 1 !== count( $terms ) ) {
			return null;
		}
		$name = reset( $terms )->name;

		return '' === $name ? null : $name;
	}

	/**
	 * Whether a pattern of the contract matches a model. The patterns carry
	 * their own anchors and are tested with search semantics, the way the
	 * engine tests them; a malformed one is loud (PHP warns) and matches
	 * nothing, so a broken data file is seen, not silently ignored.
	 *
	 * @param string $pattern The pattern of a pair entry.
	 * @param string $model   The product model.
	 */
	private static function matches( string $pattern, string $model ): bool {
		if ( '' === $pattern || '' === $model ) {
			return false;
		}

		return 1 === preg_match( '{' . $pattern . '}', $model );
	}
}

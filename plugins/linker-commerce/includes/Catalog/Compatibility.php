<?php
/**
 * Pairing an inverter with a battery against the compatibility contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

/**
 * Pairing an inverter with a battery against data/compatibility.json
 * (docs/specs/8-engineering-data.md): pairs of model patterns with a verdict,
 * conditions and documents. A pair matches when both patterns match the
 * "<brand> <model>" of the products asked about; the first matching entry
 * decides, so the model-level entries sit before their family entry in the
 * file.
 */
final class Compatibility {

	/**
	 * The three verdicts the contract states.
	 */
	public const VERDICTS = array( 'released', 'released_with_accessory', 'not_released' );

	/**
	 * The verdict of an inverter and a battery, as the contract states it.
	 *
	 * @param string $inverter "<brand> <model>" of the inverter.
	 * @param string $battery "<brand> <model>" of the battery.
	 * @return array{verdict: string, conditions: list<string>, conditions_de: list<string>, documents: list<array<string, mixed>>}|null The first matching pair, null when the contract has none.
	 */
	public static function for_models( string $inverter, string $battery ): ?array {
		foreach ( self::pairs() as $pair ) {
			if ( self::matches( $pair['inverter'] ?? '', $inverter ) && self::matches( $pair['battery'] ?? '', $battery ) ) {
				return array(
					'verdict'       => (string) ( $pair['verdict'] ?? '' ),
					'conditions'    => array_values( array_filter( array_map( 'strval', $pair['conditions'] ?? array() ) ) ),
					'conditions_de' => array_values( array_filter( array_map( 'strval', $pair['conditions_de'] ?? array() ) ) ),
					'documents'     => array_values( array_filter( is_array( $pair['documents'] ?? null ) ? $pair['documents'] : array(), 'is_array' ) ),
				);
			}
		}

		return null;
	}

	/**
	 * The verdict for two products: their "<brand> <model>" strings read the
	 * way the feed names them.
	 *
	 * @param int $inverter_id Inverter product ID.
	 * @param int $battery_id  Battery product ID.
	 * @return array{verdict: string, conditions: list<string>, conditions_de: list<string>, documents: list<array<string, mixed>>}|null
	 */
	public static function for_products( int $inverter_id, int $battery_id ): ?array {
		$inverter = self::brand_model( $inverter_id );
		$battery  = self::brand_model( $battery_id );
		if ( null === $inverter || null === $battery ) {
			return null;
		}

		return self::for_models( $inverter, $battery );
	}

	/**
	 * The pairs of the contract, in file order.
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
	 * The date the contract states it was verified on, or "".
	 */
	public static function verified_on(): string {
		$data = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );

		return is_string( $data['verified_on'] ?? null ) ? $data['verified_on'] : '';
	}

	/**
	 * The subject the patterns are written against: "<brand> <model>", or
	 * null when the product states neither.
	 *
	 * @param int $product_id Product ID.
	 */
	private static function brand_model( int $product_id ): ?string {
		$terms = get_the_terms( $product_id, 'pa_model' );
		if ( ! is_array( $terms ) || 1 !== count( $terms ) ) {
			return null;
		}
		$model = reset( $terms )->name;
		$brand = '';
		$terms = get_the_terms( $product_id, 'pa_brand' );
		if ( is_array( $terms ) && 1 === count( $terms ) ) {
			$brand = (string) reset( $terms )->name;
		}

		return trim( "{$brand} {$model}" );
	}

	/**
	 * Whether a pattern of the contract matches a subject. The patterns are
	 * anchored regular expressions; a malformed one is loud (PHP warns) and
	 * matches nothing, so a broken data file is seen, not silently ignored.
	 *
	 * @param string $pattern The pattern of a pair entry.
	 * @param string $subject "<brand> <model>".
	 */
	private static function matches( string $pattern, string $subject ): bool {
		if ( '' === $pattern || '' === $subject ) {
			return false;
		}

		return 1 === preg_match( '{' . $pattern . '}', $subject );
	}
}

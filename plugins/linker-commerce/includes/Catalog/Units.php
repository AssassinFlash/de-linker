<?php
/**
 * Unit conversion of product figures.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

/**
 * Converts a product figure ({value, unit}) to kW, kVA or kWh by its unit
 * alone, never by its key name: among the 89 live inverters and batteries of
 * 2026-10-09 (tests/fixtures/live-products-2026-10-09.json)
 * `ac_output_kw_nominal` holds W in 29 products and kW in 28. Every method
 * returns null when the value is not a plain non-negative number (or range) or
 * the unit is not one of its table.
 */
final class Units {

	/**
	 * Divisor from each active-power unit to kW. Wp and kWp are the PV array's
	 * peak power, the unit the live figures use for `max_pv_input_power_w`.
	 */
	private const TO_KW = array(
		'w'   => 1000,
		'wp'  => 1000,
		'kw'  => 1,
		'kwp' => 1,
	);

	/**
	 * Divisor from each apparent-power unit to kVA. Apparent power is not active
	 * power: a kVA figure never becomes a kW figure.
	 */
	private const TO_KVA = array(
		'va'  => 1000,
		'kva' => 1,
	);

	/**
	 * Divisor from each energy unit to kWh.
	 */
	private const TO_KWH = array(
		'wh'  => 1000,
		'kwh' => 1,
	);

	/**
	 * Separators of the energy ranges and option lists on the live site:
	 * "57.3–100.3", "5.0-25.0", "5-108", "5.02 / 10.04 / 15.06".
	 */
	private const RANGE_SEPARATOR = '/\s*[–\-\/]\s*/u';

	/**
	 * Active power in kW.
	 *
	 * @param mixed $value Figure value.
	 * @param mixed $unit  Figure unit.
	 */
	public static function power_kw( mixed $value, mixed $unit ): ?float {
		return self::convert( $value, $unit, self::TO_KW );
	}

	/**
	 * Apparent power in kVA.
	 *
	 * @param mixed $value Figure value.
	 * @param mixed $unit  Figure unit.
	 */
	public static function apparent_power_kva( mixed $value, mixed $unit ): ?float {
		return self::convert( $value, $unit, self::TO_KVA );
	}

	/**
	 * Energy in kWh.
	 *
	 * @param mixed $value Figure value.
	 * @param mixed $unit  Figure unit.
	 */
	public static function energy_kwh( mixed $value, mixed $unit ): ?float {
		return self::convert( $value, $unit, self::TO_KWH );
	}

	/**
	 * An energy range ("57.3–100.3") or list of options ("5.0/10.0/15.0") in kWh,
	 * as its smallest and largest value.
	 *
	 * @param mixed $value Figure value.
	 * @param mixed $unit  Figure unit.
	 * @return array{min: float, max: float}|null
	 */
	public static function energy_range_kwh( mixed $value, mixed $unit ): ?array {
		$divisor = self::divisor( $unit, self::TO_KWH );
		if ( null === $divisor || ! is_string( $value ) ) {
			return null;
		}

		$parts = preg_split( self::RANGE_SEPARATOR, trim( $value ) );
		if ( false === $parts || count( $parts ) < 2 ) {
			return null;
		}

		$numbers = array();
		foreach ( $parts as $part ) {
			$number = self::number( $part );
			if ( null === $number ) {
				return null;
			}
			$numbers[] = $number / $divisor;
		}

		return array(
			'min' => min( $numbers ),
			'max' => max( $numbers ),
		);
	}

	/**
	 * A plain non-negative decimal number ("29999", "9.999", 125); anything else,
	 * such as "4*45", "55.2 / 67.5" or "12000*", is not a number.
	 *
	 * @param mixed $value Figure value.
	 */
	public static function number( mixed $value ): ?float {
		if ( is_int( $value ) || is_float( $value ) ) {
			return is_finite( (float) $value ) && $value >= 0 ? (float) $value : null;
		}
		if ( ! is_string( $value ) || 1 !== preg_match( '/^\d+(?:\.\d+)?$/', trim( $value ) ) ) {
			return null;
		}

		return (float) trim( $value );
	}

	/**
	 * Converts a scalar value by the unit's divisor.
	 *
	 * @param mixed              $value Figure value.
	 * @param mixed              $unit  Figure unit.
	 * @param array<string, int> $table Divisor per lower-case unit.
	 */
	private static function convert( mixed $value, mixed $unit, array $table ): ?float {
		$divisor = self::divisor( $unit, $table );
		$number  = self::number( $value );

		return null === $divisor || null === $number ? null : $number / $divisor;
	}

	/**
	 * The divisor of a unit; case and surrounding space do not matter.
	 *
	 * @param mixed              $unit  Figure unit.
	 * @param array<string, int> $table Divisor per lower-case unit.
	 */
	private static function divisor( mixed $unit, array $table ): ?int {
		return is_string( $unit ) ? ( $table[ strtolower( trim( $unit ) ) ] ?? null ) : null;
	}
}

<?php
/**
 * Tests for the unit conversion of product figures.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Units;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Units. A null result is what the selection facts report as unknown.
 *
 * @covers \Linker\Commerce\Products\Units
 */
final class UnitsTest extends TestCase {

	/**
	 * Active power converts by the unit only.
	 *
	 * @dataProvider power_cases
	 *
	 * @param mixed      $value    Figure value.
	 * @param mixed      $unit     Figure unit.
	 * @param float|null $expected kW, or null.
	 */
	public function test_power_kw( mixed $value, mixed $unit, ?float $expected ): void {
		$this->assertSame( $expected, Units::power_kw( $value, $unit ) );
	}

	/**
	 * Cases of power_kw(): the spec's table (docs/specs/7-selection-facts.md) first.
	 *
	 * @return array<string, array{mixed, mixed, float|null}>
	 */
	public function power_cases(): array {
		return array(
			'10 kW'                           => array( '10', 'kW', 10.0 ),
			'10000 W'                         => array( '10000', 'W', 10.0 ),
			'7500 Wp'                         => array( '7500', 'Wp', 7.5 ),
			'no unit'                         => array( '10', '', null ),
			'unit missing'                    => array( '10', null, null ),
			'29999 W, 1181'                   => array( '29999', 'W', 29.999 ),
			'9.999 kW, 6514'                  => array( '9.999', 'kW', 9.999 ),
			'numeric value'                   => array( 125, 'kW', 125.0 ),
			'kWp'                             => array( '12', 'kWp', 12.0 ),
			'unit case and space'             => array( '5000', ' w ', 5.0 ),
			'apparent power is not kW'        => array( '29900', 'VA', null ),
			'energy unit is not power'        => array( '10', 'kWh', null ),
			'charge/discharge pair, 1954'     => array( '55.2 / 67.5', 'kW', null ),
			'multiplication, 1959 DC current' => array( '4*45', 'A', null ),
			'starred value'                   => array( '12000*', 'W', null ),
			'German decimal comma'            => array( '29,9', 'kW', null ),
			'negative'                        => array( -5, 'kW', null ),
			'empty'                           => array( '', 'kW', null ),
		);
	}

	/**
	 * Apparent power converts to kVA and never from an active-power unit.
	 *
	 * @testWith ["29900", "VA", 29.9]
	 *           ["15", "kVA", 15.0]
	 *           ["15", "kW", null]
	 *           ["15", "", null]
	 *
	 * @param string     $value    Figure value.
	 * @param string     $unit     Figure unit.
	 * @param float|null $expected kVA, or null.
	 */
	public function test_apparent_power_kva( string $value, string $unit, ?float $expected ): void {
		$this->assertSame( $expected, Units::apparent_power_kva( $value, $unit ) );
	}

	/**
	 * Energy converts to kWh by the unit only.
	 *
	 * @testWith ["5120", "Wh", 5.12]
	 *           ["10", "kWh", 10.0]
	 *           ["261.25", "kWh", 261.25]
	 *           ["10", "", null]
	 *           ["10", "kW", null]
	 *           ["57.3–100.3", "kWh", null]
	 *
	 * @param string     $value    Figure value.
	 * @param string     $unit     Figure unit.
	 * @param float|null $expected kWh, or null.
	 */
	public function test_energy_kwh( string $value, string $unit, ?float $expected ): void {
		$this->assertSame( $expected, Units::energy_kwh( $value, $unit ) );
	}

	/**
	 * Energy ranges and option lists become their smallest and largest value.
	 *
	 * @dataProvider range_cases
	 *
	 * @param string                             $value    Figure value.
	 * @param string                             $unit     Figure unit.
	 * @param array{min: float, max: float}|null $expected Range in kWh, or null.
	 */
	public function test_energy_range_kwh( string $value, string $unit, ?array $expected ): void {
		$this->assertSame( $expected, Units::energy_range_kwh( $value, $unit ) );
	}

	/**
	 * Cases of energy_range_kwh(): every form on the live site, then non-ranges.
	 *
	 * @return array<string, array{string, string, array{min: float, max: float}|null}>
	 */
	public function range_cases(): array {
		return array(
			'en dash, 1959'            => array(
				'57.3–100.3',
				'kWh',
				array(
					'min' => 57.3,
					'max' => 100.3,
				),
			),
			'hyphen, 1832'             => array(
				'5.0-25.0',
				'kWh',
				array(
					'min' => 5.0,
					'max' => 25.0,
				),
			),
			'integers, 3556'           => array(
				'5-108',
				'kWh',
				array(
					'min' => 5.0,
					'max' => 108.0,
				),
			),
			'option list, 2092'        => array(
				'5.0/10.0/15.0/20.0/25.0',
				'kWh',
				array(
					'min' => 5.0,
					'max' => 25.0,
				),
			),
			'spaced option list, 3581' => array(
				'5.02 / 10.04 / 15.06 / 20.08 / 25.10 / 30.12',
				'kWh',
				array(
					'min' => 5.02,
					'max' => 30.12,
				),
			),
			'Wh'                       => array(
				'5000-25000',
				'Wh',
				array(
					'min' => 5.0,
					'max' => 25.0,
				),
			),
			'single value'             => array( '10', 'kWh', null ),
			'no unit'                  => array( '5-108', '', null ),
			'power unit'               => array( '55.2 / 67.5', 'kW', null ),
			'open range'               => array( '5-', 'kWh', null ),
			'words'                    => array( 'up to 25', 'kWh', null ),
		);
	}

	/**
	 * Only plain non-negative decimals are numbers.
	 *
	 * @testWith ["29999", 29999.0]
	 *           [" 9.999 ", 9.999]
	 *           ["0", 0.0]
	 *           ["1e3", null]
	 *           ["4*45", null]
	 *           ["", null]
	 *
	 * @param string     $value    Figure value.
	 * @param float|null $expected Number, or null.
	 */
	public function test_number( string $value, ?float $expected ): void {
		$this->assertSame( $expected, Units::number( $value ) );
	}
}

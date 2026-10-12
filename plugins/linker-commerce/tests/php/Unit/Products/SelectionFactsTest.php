<?php
/**
 * Tests for the reading of selection facts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Tests\Support\MocksProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for SelectionFacts on constructed products; the live products are in
 * SelectionFactsLiveProductsTest.
 *
 * @covers \Linker\Commerce\Products\SelectionFacts
 * @covers \Linker\Commerce\Products\SelectionFactSet
 */
final class SelectionFactsTest extends TestCase {

	use MocksProducts;

	private const ID = 4242;

	private const INVERTERS = array( 449 => 'inverters' );

	/**
	 * Without pa_phase the phase is read from the phase figure; a voltage is no
	 * evidence of a phase count, and a text naming both counts is unknown.
	 *
	 * @dataProvider phase_texts
	 *
	 * @param string     $text     Value of the phases figure.
	 * @param int|string $expected Phase fact.
	 */
	public function test_phase_from_the_figure_text( string $text, int|string $expected ): void {
		$this->mock_product(
			self::ID,
			self::INVERTERS,
			array(),
			array(),
			self::figures(
				array(
					'phases' => array(
						'value' => $text,
						'unit'  => '',
					),
				)
			)
		);

		$this->assertSame( $expected, SelectionFacts::for_product( self::ID )->phase );
	}

	/**
	 * Phase texts: the spec's forms, the live forms, then the ones that say nothing.
	 *
	 * @return array<string, array{string, int|string}>
	 */
	public function phase_texts(): array {
		return array(
			'1/N/PE a.c. 230 V'         => array( '1/N/PE a.c. 230 V', 1 ),
			'1/N/PE'                    => array( '1/N/PE', 1 ),
			'L+N+PE'                    => array( 'L+N+PE', 1 ),
			'single-phase'              => array( 'single-phase', 1 ),
			'Single-phase'              => array( 'Single-phase', 1 ),
			'three-phase'               => array( 'three-phase', 3 ),
			'Three Phase'               => array( 'Three Phase', 3 ),
			'3L+N+PE'                   => array( '3L+N+PE', 3 ),
			'3/N/PE'                    => array( '3/N/PE', 3 ),
			'3+N+PE, 380/400'           => array( '3+N+PE, 380/400', 3 ),
			'3L + N + PE with voltages' => array( 'L–L: 380 / 400 V AC; L–N: 220 / 230 V AC; 3L + N + PE', 3 ),
			'230 V'                     => array( '230 V', SelectionFactSet::UNKNOWN ),
			'400 V'                     => array( '400 V', SelectionFactSet::UNKNOWN ),
			'both counts'               => array( '1/N/PE or 3/N/PE', SelectionFactSet::UNKNOWN ),
			'empty'                     => array( '', SelectionFactSet::UNKNOWN ),
		);
	}

	/**
	 * The pa_phase attribute comes before the figures; the figure key "phase"
	 * (GoodWe ETR) is read like "phases".
	 */
	public function test_phase_attribute_before_figures(): void {
		$this->mock_product( self::ID, self::INVERTERS, array(), array( 'single-phase' ), self::figures( array( 'phase' => array( 'value' => 'Three-phase' ) ) ) );
		$this->mock_product( self::ID + 1, self::INVERTERS, array(), array(), self::figures( array( 'phase' => array( 'value' => 'Three-phase' ) ) ) );

		$this->assertSame( 1, SelectionFacts::for_product( self::ID )->phase );
		$this->assertSame( 3, SelectionFacts::for_product( self::ID + 1 )->phase );
	}

	/**
	 * Only a single home or commercial term is an application.
	 *
	 * @testWith [["home"], "home"]
	 *           [["commercial"], "commercial"]
	 *           [["commercial-industrial"], "unknown"]
	 *           [["home", "commercial"], "unknown"]
	 *           [[], "unknown"]
	 *
	 * @param string[] $terms    pa_application term slugs.
	 * @param string   $expected Application fact.
	 */
	public function test_application( array $terms, string $expected ): void {
		$this->mock_product( self::ID, self::INVERTERS, $terms, array(), '' );

		$this->assertSame( $expected, SelectionFacts::for_product( self::ID )->application );
	}

	/**
	 * A category that is not a device class takes its nearest listed ancestor.
	 */
	public function test_device_class_from_the_nearest_listed_ancestor(): void {
		$this->mock_product( self::ID, array( 458 => 'backup-power' ), array(), array(), '' );
		WP_Mock::userFunction(
			'get_ancestors',
			array(
				'args'   => array( 458, 'product_cat', 'taxonomy' ),
				'return' => array( 456 ),
			)
		);
		WP_Mock::userFunction(
			'get_term_field',
			array(
				'args'   => array( 'slug', 456, 'product_cat' ),
				'return' => 'accessories',
			)
		);

		$this->assertSame( 'accessories', SelectionFacts::for_product( self::ID )->device_class );
	}

	/**
	 * No listed category, or categories that lead to two device classes, give unknown.
	 */
	public function test_device_class_unknown(): void {
		$this->mock_product( self::ID, array( 28 => 'uncategorized' ), array(), array(), '' );
		$this->mock_product(
			self::ID + 1,
			array(
				449 => 'inverters',
				450 => 'home-storage',
			),
			array(),
			array(),
			''
		);
		$this->mock_product( self::ID + 2, array(), array(), array(), '' );
		WP_Mock::userFunction(
			'get_ancestors',
			array(
				'args'   => array( 28, 'product_cat', 'taxonomy' ),
				'return' => array(),
			)
		);

		$this->assertSame( SelectionFactSet::UNKNOWN, SelectionFacts::for_product( self::ID )->device_class );
		$this->assertSame( SelectionFactSet::UNKNOWN, SelectionFacts::for_product( self::ID + 1 )->device_class );
		$this->assertSame( SelectionFactSet::UNKNOWN, SelectionFacts::for_product( self::ID + 2 )->device_class );
	}

	/**
	 * The first present AC power key decides, converted by its unit; an empty
	 * value is not present, and a figure without a unit is unknown.
	 */
	public function test_ac_power_first_present_key_by_unit(): void {
		$this->mock_product(
			self::ID,
			self::INVERTERS,
			array(),
			array(),
			self::figures(
				array(
					'ac_output_kw_nominal' => array(
						'value' => '',
						'unit'  => 'W',
					),
					'ac_output_w_nominal'  => array(
						'value' => '3680',
						'unit'  => 'W',
					),
					'rated_ac_power_kw'    => array(
						'value' => '5',
						'unit'  => 'kW',
					),
				)
			)
		);
		$this->mock_product( self::ID + 1, self::INVERTERS, array(), array(), self::figures( array( 'ac_output_kw_nominal' => array( 'value' => '10000' ) ) ) );

		$this->assertSame( 3.68, SelectionFacts::for_product( self::ID )->ac_power_kw );
		$this->assertSame( SelectionFactSet::UNKNOWN, SelectionFacts::for_product( self::ID + 1 )->ac_power_kw );
	}

	/**
	 * An AC power stated in kVA is kept apart as ac_apparent_kva, never as kW.
	 */
	public function test_ac_power_in_kva_is_kept_apart(): void {
		$this->mock_product(
			self::ID,
			self::INVERTERS,
			array(),
			array(),
			self::figures(
				array(
					'ac_output_kw_nominal' => array(
						'value' => '15',
						'unit'  => 'kVA',
					),
				)
			)
		);

		$facts = SelectionFacts::for_product( self::ID );

		$this->assertSame( SelectionFactSet::UNKNOWN, $facts->ac_power_kw );
		$this->assertSame( 15.0, $facts->ac_apparent_kva );
		$this->assertSame( 15.0, $facts->to_array()['ac_apparent_kva'] ?? null );
	}

	/**
	 * A range under an energy key stays out of the scalar and becomes kwh_range;
	 * system_energy_kwh_range comes first.
	 */
	public function test_energy_range_is_not_a_scalar(): void {
		$this->mock_product(
			self::ID,
			array( 452 => 'all-in-one-systems' ),
			array(),
			array(),
			self::figures(
				array(
					'battery_rated_energy' => array(
						'value' => '57.3–100.3',
						'unit'  => 'kWh',
					),
				)
			)
		);
		$this->mock_product(
			self::ID + 1,
			array( 450 => 'home-storage' ),
			array(),
			array(),
			self::figures(
				array(
					'battery_rated_energy'    => array(
						'value' => '57.3–100.3',
						'unit'  => 'kWh',
					),
					'system_energy_kwh_range' => array(
						'value' => '5-108',
						'unit'  => 'kWh',
					),
				)
			)
		);

		$facts = SelectionFacts::for_product( self::ID );
		$this->assertSame( SelectionFactSet::UNKNOWN, $facts->nominal_kwh );
		$this->assertSame(
			array(
				'min' => 57.3,
				'max' => 100.3,
			),
			$facts->kwh_range
		);
		$this->assertSame(
			array(
				'min' => 5.0,
				'max' => 108.0,
			),
			SelectionFacts::for_product( self::ID + 1 )->kwh_range
		);
	}

	/**
	 * The product's own energy figure comes before one module's.
	 */
	public function test_system_energy_before_module_energy(): void {
		$this->mock_product(
			self::ID,
			array( 453 => 'battery-systems' ),
			array(),
			array(),
			self::figures(
				array(
					'module_energy_kwh_nominal' => array(
						'value' => '10.24',
						'unit'  => 'kWh',
					),
					'system_nominal_energy_kwh' => array(
						'value' => '61.4',
						'unit'  => 'kWh',
					),
					'system_usable_energy_kwh'  => array(
						'value' => '60',
						'unit'  => 'kWh',
					),
				)
			)
		);

		$facts = SelectionFacts::for_product( self::ID );

		$this->assertSame( 61.4, $facts->nominal_kwh );
		$this->assertSame( 60.0, $facts->usable_kwh );
	}

	/**
	 * Missing or broken figures leave every figure fact unknown.
	 *
	 * @testWith [""]
	 *           ["not json"]
	 *           ["[]"]
	 *           [false]
	 *
	 * @param mixed $stored What get_post_meta() returns.
	 */
	public function test_without_figures_the_figure_facts_are_unknown( mixed $stored ): void {
		$this->mock_product( self::ID, self::INVERTERS, array( 'home' ), array( 'three-phase' ), $stored );

		$this->assertSame(
			array(
				'device_class' => 'inverters',
				'application'  => 'home',
				'phase'        => 3,
				'ac_power_kw'  => SelectionFactSet::UNKNOWN,
				'pv_input_kw'  => SelectionFactSet::UNKNOWN,
				'usable_kwh'   => SelectionFactSet::UNKNOWN,
				'nominal_kwh'  => SelectionFactSet::UNKNOWN,
			),
			SelectionFacts::for_product( self::ID )->to_array()
		);
	}

	/**
	 * Figures as get_post_meta() returns them: a JSON string.
	 *
	 * @param array<string, array<string, string>> $figures Figure entries by key.
	 */
	private static function figures( array $figures ): string {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WordPress is not loaded in unit tests.
		return (string) json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
	}
}

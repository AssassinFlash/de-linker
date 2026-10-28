<?php
/**
 * Tests for the voltage spec key's mapping.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Materials;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use ReflectionProperty;
use WC_Product;
use WP_Mock;

/**
 * The "Nominal voltage" row reads the product-level and system-level
 * registry keys: the live battery cards read them (the GW261.2-BAT-LCD-G10
 * card's model line carried "832.0 V", the GW61.4-BAT-AC-G10 card's row
 * 307.2 V — measured 2026-10-12; recheck 2026-10-14 found the deployed tree
 * at the pack's 166.4 V, or without the row), and the hosted datasheets
 * state exactly those values (GW_BAT-C-208-261_Datasheet_EMEA-EN_V1.1.pdf
 * p.2). A module's own voltage stays a fallback: it shows only where the
 * product states no system value.
 *
 * @covers \Linker\Commerce\Products\Materials::fact_keys
 * @covers \Linker\Commerce\Products\Materials::specs
 */
final class MaterialsVoltageTest extends TestCase {

	/**
	 * Restores the registry statics after each test.
	 */
	public function tearDown(): void {
		$this->seed_registry( null );
		parent::tearDown();
	}

	/**
	 * The labels read the vocabulary arrays; translation returns its input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_terms', array( 'return' => false ) );
	}

	/**
	 * The map routes the product-level and system-level nominal voltages
	 * into the rail's "Nominal voltage" key.
	 */
	public function test_the_nominal_voltage_keys_map_to_the_nom_voltage_row(): void {
		$keys = Materials::fact_keys();

		$this->assertSame( 'nom_voltage', $keys['nominal_voltage_v'] );
		$this->assertSame( 'nom_voltage', $keys['system_nominal_voltage_v'] );
		$this->assertSame( 'nom_voltage', $keys['system_voltage_v_nominal'] );
		$this->assertSame( 'nom_voltage', $keys['module_voltage_v_nominal'] );
	}

	/**
	 * A product's own nominal voltage wins over its pack's, and a pack-only
	 * product keeps its pack's value (the module-suppression rule's own
	 * order: system first, module only where nothing above it answers).
	 */
	public function test_specs_read_the_product_voltage_ahead_of_the_module_value(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_full'   => array(
					'bindings'    => array( 'woo_product_ids' => array( 9001 ) ),
					'identity'    => array(
						'kind'         => 'battery_module',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-BAT-FULL',
					),
					'material_id' => 'mat_test_bat_full',
					'technical'   => array(
						'specifications' => array(
							'module_voltage_v_nominal' => array(
								'value' => '166.4',
								'unit'  => 'V',
							),
							'nominal_voltage_v'        => array(
								'value' => '832.0',
								'unit'  => 'V',
							),
						),
					),
				),
				'mat_test_bat_module' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9002 ) ),
					'identity'    => array(
						'kind'         => 'battery_module',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-BAT-MODULE',
					),
					'material_id' => 'mat_test_bat_module',
					'technical'   => array(
						'specifications' => array(
							'module_voltage_v_nominal' => array(
								'value' => '166.4',
								'unit'  => 'V',
							),
						),
					),
				),
				'mat_test_bat_system' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9003 ) ),
					'identity'    => array(
						'kind'         => 'battery_module',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-BAT-SYSTEM',
					),
					'material_id' => 'mat_test_bat_system',
					'technical'   => array(
						'specifications' => array(
							'system_nominal_voltage_v' => array(
								'value' => '307.2',
								'unit'  => 'V',
							),
						),
					),
				),
			),
		);

		$full   = Materials::specs( $this->product( 9001 ) );
		$module = Materials::specs( $this->product( 9002 ) );
		$system = Materials::specs( $this->product( 9003 ) );

		$this->assertSame( '832.0 V', $full['nom_voltage']['value'] );
		$this->assertSame( '166.4 V', $module['nom_voltage']['value'] );
		$this->assertSame( '307.2 V', $system['nom_voltage']['value'] );
	}

	/**
	 * A product whose registry material states no voltage at all carries no
	 * row (a missing row is skipped, never swapped).
	 */
	public function test_a_product_without_a_voltage_states_no_voltage_row(): void {
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => fn ( int $id ) => $this->product( $id ),
			)
		);
		$this->seed_registry(
			array(
				'mat_test_bat_plain' => array(
					'bindings'    => array( 'woo_product_ids' => array( 9004 ) ),
					'identity'    => array(
						'kind'         => 'battery_module',
						'manufacturer' => 'GoodWe',
						'model'        => 'GW-BAT-PLAIN',
					),
					'material_id' => 'mat_test_bat_plain',
					'technical'   => array(
						'specifications' => array(
							'ip_rating' => array( 'value' => 'IP55' ),
						),
					),
				),
			),
		);

		$specs = Materials::specs( $this->product( 9004 ) );

		$this->assertArrayNotHasKey( 'nom_voltage', $specs );
		$this->assertSame( 'IP55', $specs['ip']['value'] );
	}

	/**
	 * Ireland-variant qualifiers keep their source number, unit and footnote marker.
	 *
	 * @dataProvider ireland_unit_notes
	 * @param string $unit    The registry unit with its qualifier.
	 * @param string $german  The localized qualifier, or the unchanged unknown note.
	 */
	public function test_ireland_unit_notes_are_localized_without_rewriting_unknown_notes( string $unit, string $german ): void {
		$this->assertSame( $unit, Materials::unit_label( $unit, 'en' ) );
		$this->assertSame( $german, Materials::unit_label( $unit, 'de' ) );
	}

	/**
	 * The three qualifier shapes in the SAJ HS3 registry and one unsupported country.
	 *
	 * @return array<string, array{string, string}>
	 */
	public static function ireland_unit_notes(): array {
		return array(
			'active power'   => array( 'W (footnote *: 11000 W for Ireland variant)', 'W (Fußnote *: 11000 W für die Irland-Variante)' ),
			'apparent power' => array( 'VA (footnote *: 11000 VA for Ireland variant)', 'VA (Fußnote *: 11000 VA für die Irland-Variante)' ),
			'current'        => array( 'A @230Vac (footnote **: 15.9 A for Ireland variant)', 'A @230Vac (Fußnote **: 15.9 A für die Irland-Variante)' ),
			'unknown note'   => array( 'W (footnote *: 11000 W for Finland variant)', 'W (footnote *: 11000 W for Finland variant)' ),
		);
	}

	/**
	 * The hero formatter retains its English bytes and the German variant limit.
	 */
	public function test_the_power_formatter_keeps_the_ireland_qualifier(): void {
		$fact = array(
			'value' => '12000*',
			'unit'  => 'W (footnote *: 11000 W for Ireland variant)',
		);
		$this->seed_registry(
			array(
				'mat_test_hs3' => array(
					'bindings'  => array( 'woo_product_ids' => array( 9001 ) ),
					'technical' => array( 'specifications' => array( 'ac_output_kw_nominal' => $fact ) ),
				),
			)
		);
		$product = $this->product( 9001 );
		$english = Materials::spec_text( $product, 'ac_power', 'ac_output_kw_nominal', $fact, false );
		$german  = Materials::spec_text( $product, 'ac_power', 'ac_output_kw_nominal', $fact, true );

		$this->assertSame( '12 kW (footnote *: 11 kW for Ireland variant)', $english['value'] );
		$this->assertSame( '12 kW (Fußnote *: 11 kW für die Irland-Variante)', $german['value'] );
	}

	/**
	 * A voltage suffix needs an identical, explicitly measured fact on the same product.
	 *
	 * Isolate the language function mock so it does not affect other tests.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_key_stats_only_add_verified_companion_voltage_units(): void {
		$german = false;
		WP_Mock::userFunction(
			'linker_i18n_is_de',
			array(
				'return' => static function () use ( &$german ): bool {
					return $german;
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		$materials = array();
		foreach ( array(
			9010 => array(
				'value' => '3+N+PE, 380/400',
				'unit'  => 'V',
			),
			9011 => array(
				'value' => '3+N+PE, 220/230',
				'unit'  => 'V',
			),
			9012 => array(
				'value' => '3+N+PE, 380/400',
				'unit'  => '',
			),
		) as $id => $voltage ) {
			$materials[ 'fixture-' . $id ] = array(
				'bindings'  => array( 'woo_product_ids' => array( $id ) ),
				'identity'  => array( 'kind' => 'all_in_one_system' ),
				'technical' => array(
					'specifications' => array(
						'phases'           => array(
							'value' => '3+N+PE, 380/400',
							'unit'  => '',
						),
						'rated_ac_voltage' => $voltage,
					),
				),
			);
		}
		$registry                              = json_decode( (string) file_get_contents( dirname( __DIR__, 4 ) . '/data/material-registry.json' ), true );
		$actual                                = $registry['materials']['mat_saj_chs2_29_9k_t4_x'];
		$actual['bindings']['woo_product_ids'] = array( 9013 );
		$materials['actual-chs2']              = $actual;
		$materials['phase-count']              = array(
			'bindings'  => array( 'woo_product_ids' => array( 9014 ) ),
			'identity'  => array( 'kind' => 'all_in_one_system' ),
			'technical' => array(
				'specifications' => array(
					'phases'           => array( 'value' => '3' ),
					'rated_ac_voltage' => array(
						'value' => '3',
						'unit'  => 'V',
					),
				),
			),
		);
		$materials['translated-phase-only']    = array(
			'bindings'  => array( 'woo_product_ids' => array( 9015 ) ),
			'identity'  => array( 'kind' => 'all_in_one_system' ),
			'technical' => array(
				'specifications' => array(
					'phases'           => array(
						'value'    => '3+N+PE, 380/400',
						'value_de' => '3-phasig',
					),
					'rated_ac_voltage' => array(
						'value' => '3+N+PE, 380/400',
						'unit'  => 'V',
					),
				),
			),
		);
		$this->seed_registry( $materials );
		foreach ( array( false, true ) as $language ) {
			$german = $language;
			$this->assertSame( '3+N+PE, 380/400 V', Materials::key_stats( $this->product( 9010 ) )[0]['value'] );
			$this->assertSame( '3+N+PE, 380/400', Materials::key_stats( $this->product( 9011 ) )[0]['value'] );
			$this->assertSame( '3+N+PE, 380/400', Materials::key_stats( $this->product( 9012 ) )[0]['value'] );
			$actual_stats = array_column( Materials::key_stats( $this->product( 9013 ) ), 'value', 'key' );
			$this->assertSame( '3+N+PE, 380/400 V', $actual_stats['phase'] );
			$this->assertSame( $language ? '3-phasig' : '3-phase', Materials::key_stats( $this->product( 9014 ) )[0]['value'] );
			$this->assertSame( $language ? '3-phasig' : '3+N+PE, 380/400 V', Materials::key_stats( $this->product( 9015 ) )[0]['value'] );
		}
	}

	/**
	 * A WC_Product double with just the id.
	 *
	 * @param int $id The product id.
	 */
	private function product( int $id ): WC_Product {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( $id );
		return $product;
	}

	/**
	 * Seeds (or clears) the registry statics. Reflection reads and writes
	 * non-public properties as of PHP 8.1 without setAccessible().
	 *
	 * @param array<string, mixed>|null $materials The registry's materials, null to reset.
	 */
	private function seed_registry( ?array $materials ): void {
		$registry = new ReflectionProperty( Materials::class, 'registry' );
		$registry->setValue( null, null === $materials ? null : array( 'materials' => $materials ) );
		$index = new ReflectionProperty( Materials::class, 'product_index' );
		$index->setValue( null, null );
	}
}

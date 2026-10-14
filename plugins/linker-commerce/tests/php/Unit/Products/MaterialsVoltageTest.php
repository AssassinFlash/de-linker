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

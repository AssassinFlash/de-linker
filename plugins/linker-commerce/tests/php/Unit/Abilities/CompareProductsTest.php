<?php
/**
 * Tests for linker/compare-products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\CompareProducts;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for CompareProducts: battery energy and inverter output stay on different rows.
 *
 * @covers \Linker\Commerce\Abilities\CompareProducts
 */
final class CompareProductsTest extends TestCase {

	use MocksLiveProducts;

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * Two inverters: AC power and PV input rows, no battery-energy row.
	 */
	public function test_inverters_do_not_mix_in_a_battery_energy_row(): void {
		$this->mock_live_products( array( 4107, 3556 ) );
		$result = ( new CompareProducts( null, $this->publication_data() ) )->execute(
			array(
				'product_ids' => array( 4107, 3556 ),
				'lang'        => 'en',
			)
		);
		$fields = array_column( $result['rows'], 'field' );

		$this->assertSame( array( 4107, 3556 ), array_column( $result['products'], 'product_id' ) );
		$this->assertContains( 'ac_power_kw', $fields );
		$this->assertContains( 'pv_input_kw', $fields );
		$this->assertNotContains( 'usable_kwh', $fields );
		$this->assertTrue( ( new CompareProducts( null, $this->publication_data() ) )->can_execute() );
	}

	/**
	 * An inverter and a battery: both families of rows, never one mixed "power" field.
	 */
	public function test_mixed_pair_keeps_energy_and_output_apart(): void {
		$this->mock_live_products( array( 4107, 1832 ) );
		$result = ( new CompareProducts( null, $this->publication_data() ) )->execute( array( 'product_ids' => array( 4107, 1832 ) ) );
		$fields = array_column( $result['rows'], 'field' );

		$this->assertContains( 'ac_power_kw', $fields );
		$this->assertContains( 'usable_kwh', $fields );
		$this->assertNotContains( 'power', $fields );
		$schema = ( new CompareProducts( null, $this->publication_data() ) )->args()['output_schema'];
		$this->assertSame( array( 'products', 'rows' ), $schema['required'] );
	}
}

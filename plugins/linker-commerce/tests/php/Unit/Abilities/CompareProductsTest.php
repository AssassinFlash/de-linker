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
	 * Both storefront languages expose the same checked documents.
	 *
	 * @return list<array{string}>
	 */
	public static function storefront_languages(): array {
		return array( array( 'en' ), array( 'de' ) );
	}

	/**
	 * The customer view carries document identity and no hidden numeric price.
	 *
	 * @dataProvider storefront_languages
	 * @param string $lang Storefront language.
	 */
	public function test_customer_comparison_includes_the_public_datasheet_and_model( string $lang ): void {
		WP_Mock::userFunction( 'determine_locale' )->andReturn( 'de' === $lang ? 'de_DE_formal' : 'en_US' );
		$this->mock_live_products( array( 4107, 3556, 1832, 2067, 2092 ), true );
		WP_Mock::userFunction( 'wc_load_cart' );
		$cart = \Mockery::mock();
		$cart->shouldReceive( 'get_cart' )->andReturn(
			array(
				array(
					'product_id' => 4107,
					'quantity'   => 2,
				),
			)
		);
		WP_Mock::userFunction( 'WC' )->andReturn( (object) array( 'cart' => $cart ) );
		$result = ( new CompareProducts( null, $this->publication_data() ) )->execute(
			array(
				'product_ids'  => array( 4107, 3556 ),
				'lang'         => $lang,
				'presentation' => true,
			)
		);
		$column = $result['products'][0]['presentation'];
		$this->assertSame( 'H2-10K-T3', $column['model'] );
		$this->assertNotEmpty( $column['datasheet']['url'] );
		$this->assertArrayHasKey( 'in_stock', $column );
		$this->assertTrue( $column['in_draft'] );
		$storage = array_column( $column['storage'], null, 'model' );
		$this->assertArrayHasKey( 'B2-10.0-HV1', $storage, implode( ', ', array_keys( $storage ) ) );
		$pair = $storage['B2-10.0-HV1'];
		$this->assertSame( array( 'BC2-HV1' ), $pair['accessories'] );
		$this->assertDoesNotMatchRegularExpression( '/\barticles?\b|artikel/iu', implode( ' ', $pair['conditions'] ) );
		$this->assertNotEmpty( $pair['documents'] ?? array() );
		foreach ( $pair['documents'] as $document ) {
			$this->assertNotEmpty( $document['title'] );
			$this->assertStringStartsWith( 'https://de-linker.com/', $document['url'] );
		}
		$this->assertContains( 2, array_column( $pair['documents'], 'page' ) );
		$this->assertContains( 37, array_column( $pair['documents'], 'page' ) );
		$this->assertArrayNotHasKey( 'BC2-HV1', $storage );
		$this->assertArrayNotHasKey( 'price', $column );
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

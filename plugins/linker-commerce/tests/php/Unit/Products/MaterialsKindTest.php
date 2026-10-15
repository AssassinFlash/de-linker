<?php
/**
 * Tests for the identity kind's fallback to the product's own type.
 *
 * A product whose registry material is absent (never exported, or bound to a
 * pre-migration product id) carries the old system's own type in
 * `_delinker_type` — the vocabulary behind the delivered product sets
 * (inverter 83 / battery 79 / system 45 / meter 10 / ems 9 / ct 7 / other 31
 * on the 2026-10-15 production read). Without the fallback every such card
 * fell to the 'other' order and swapped its fourth row (measured live: the
 * ESA cabinet GW125/261 showed "Max. efficiency 98.6 % (PCS)" where the
 * catalogue card shows "Ingress protection IP54").
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
 * The kind fallback and the card order it feeds.
 *
 * @covers \Linker\Commerce\Products\Materials::identity
 * @covers \Linker\Commerce\Products\Materials::card_facts
 */
final class MaterialsKindTest extends TestCase {

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
		// The twin lookup a material-less product walks: function_exists is
		// stubbed true by the suite's pll handling, so answer the language
		// call the way an unpaired product does.
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
	}

	/**
	 * A product with no registry binding reads its own type as the kind.
	 */
	public function test_identity_falls_back_to_the_products_own_type(): void {
		$this->seed_registry( array() );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) {
					return '_delinker_type' === $key ? 'system' : '';
				},
			)
		);

		$identity = Materials::identity( $this->product( 9101 ) );

		$this->assertSame( 'system', $identity['kind'] );
	}

	/**
	 * The card of such a product follows the system order: the ESA cabinet's
	 * fourth row is Ingress protection, not the 'other' order's efficiency.
	 */
	public function test_card_facts_read_the_system_order_for_a_typed_product(): void {
		$this->seed_registry( array() );
		$figures = array(
			'ac_output_kw_nominal'      => array(
				'value' => '125',
				'unit'  => 'kW',
			),
			'system_nominal_energy_kwh' => array(
				'value' => '261.25',
				'unit'  => 'kWh',
			),
			'phases'                    => array( 'value' => 'Three-phase' ),
			'ip_rating'                 => array( 'value' => 'IP54' ),
			'max_efficiency_pct'        => array(
				'value' => '98.6',
				'unit'  => '%',
			),
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( $figures ) {
					return match ( $key ) {
						'_tv_b2b_figures' => (string) json_encode( $figures ),
						'_delinker_type'  => 'system',
						default           => '',
					};
				},
			)
		);

		$card = Materials::card_facts( $this->product( 9102 ), 4 );

		$this->assertSame( array( 'ac_power', 'nominal_kwh', 'phase', 'ip' ), array_column( $card, 'key' ) );
	}

	/**
	 * A product with neither a material nor a type keeps the fallback order.
	 */
	public function test_an_untyped_product_keeps_the_other_order(): void {
		$this->seed_registry( array() );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) {
					return match ( $key ) {
						'_tv_b2b_figures' => (string) json_encode(
							array(
								'ac_output_kw_nominal' => array(
									'value' => '50',
									'unit'  => 'kW',
								),
								'max_efficiency_pct'   => array(
									'value' => '97.0',
									'unit'  => '%',
								),
							)
						),
						default            => '',
					};
				},
			)
		);

		$identity = Materials::identity( $this->product( 9103 ) );

		$this->assertSame( 'other', $identity['kind'] );
	}

	/**
	 * A bare product mock.
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

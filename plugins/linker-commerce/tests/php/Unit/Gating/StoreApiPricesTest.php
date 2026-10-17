<?php
/**
 * Tests for prices in the Store API.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\StoreApiPrices;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Tests for StoreApiPrices.
 *
 * @covers \Linker\Commerce\Gating\StoreApiPrices
 */
final class StoreApiPricesTest extends TestCase {

	/**
	 * Products 1 and 2 exist with a stored price.
	 */
	public function setUp(): void {
		parent::setUp();
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products( array( 1 => 1, 2 => 2 ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => 'orderable' ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ) {
					$product = Mockery::mock( WC_Product::class );
					$product->allows(
						array(
							'get_id'        => $id,
							'get_parent_id' => 0,
						)
					);
					$product->allows( 'get_price' )->with( 'edit' )->andReturn( '100' );
					return $product;
				},
			)
		);
	}

	/**
	 * For a guest, product lists and single products have "prices": null.
	 */
	public function test_guests_get_null_prices(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$filter = new StoreApiPrices( $this->approved_state() );
		$prices = array( 'price' => '0' );

		$list = $filter->filter(
			new WP_REST_Response(
				array(
					array(
						'id'     => 1,
						'prices' => $prices,
					),
					array(
						'id'     => 2,
						'prices' => $prices,
					),
				)
			),
			null,
			new WP_REST_Request( 'GET', '/wc/store/v1/products' )
		);
		$this->assertSame(
			array(
				array(
					'id'     => 1,
					'prices' => null,
				),
				array(
					'id'     => 2,
					'prices' => null,
				),
			),
			$list->get_data()
		);

		$single = $filter->filter(
			new WP_REST_Response(
				array(
					'id'     => 1,
					'prices' => $prices,
				)
			),
			null,
			new WP_REST_Request( 'GET', '/wc/store/v1/products/1' )
		);
		$this->assertSame(
			array(
				'id'     => 1,
				'prices' => null,
			),
			$single->get_data()
		);
	}

	/**
	 * Customers keep the prices; other routes are untouched.
	 */
	public function test_customers_and_other_routes_are_untouched(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$filter = new StoreApiPrices( $this->approved_state() );
		$data   = array(
			array(
				'id'     => 1,
				'prices' => array( 'price' => '10000' ),
			),
		);

		$this->assertSame( $data, $filter->filter( new WP_REST_Response( $data ), null, new WP_REST_Request( 'GET', '/wc/store/v1/products' ) )->get_data() );
		$this->assertSame( $data, $filter->filter( new WP_REST_Response( $data ), null, new WP_REST_Request( 'GET', '/wp/v2/posts' ) )->get_data() );
		$this->assertSame( 'error', $filter->filter( 'error', null, new WP_REST_Request( 'GET', '/wc/store/v1/products' ) ) );
	}
}

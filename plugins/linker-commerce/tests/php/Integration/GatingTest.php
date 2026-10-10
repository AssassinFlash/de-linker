<?php
/**
 * Prices for guests and customers in a real WooCommerce.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Gating\CommerceState;
use WP_REST_Request;

/**
 * Guests see no price, on the product and in the Store API; customers see it;
 * a product quoted per project shows none to anyone.
 *
 * @coversNothing
 */
final class GatingTest extends IntegrationTestCase {

	/**
	 * The product's price and the Store API's prices by visitor.
	 */
	public function test_prices_by_visitor(): void {
		$product = $this->product( '1680' );
		$project = $this->product( '990' );
		update_post_meta( $project->get_id(), CommerceState::MODE_META, CommerceState::RFQ_ONLY );

		$this->as_user( 0 );
		$this->assertSame( '', $this->price( $product->get_id() ) );
		$this->assertNull( $this->store_api_prices( $product->get_id() ) );

		$this->as_user( $this->customer()->get_id() );
		$this->assertSame( '1680', $this->price( $product->get_id() ) );
		$this->assertSame( '168000', $this->store_api_prices( $product->get_id() )['price'] ?? null );
		$this->assertSame( '', $this->price( $project->get_id() ) );
		$this->assertNull( $this->store_api_prices( $project->get_id() ) );
	}

	/**
	 * A product's price as the visitor's pages read it.
	 *
	 * @param int $product_id Product.
	 */
	private function price( int $product_id ): string {
		$product = wc_get_product( $product_id );
		$this->assertInstanceOf( \WC_Product::class, $product );
		return (string) $product->get_price();
	}

	/**
	 * The prices block of a product in WooCommerce's Store API.
	 *
	 * @param int $product_id Product.
	 * @return array<string, mixed>|null
	 */
	private function store_api_prices( int $product_id ): ?array {
		$response = rest_do_request( new WP_REST_Request( 'GET', '/wc/store/v1/products/' . $product_id ) );
		$this->assertSame( 200, $response->get_status() );
		$data = $response->get_data();
		$this->assertIsArray( $data );
		// The Store API gives "prices" as an object.
		return null === $data['prices'] ? null : (array) $data['prices'];
	}
}

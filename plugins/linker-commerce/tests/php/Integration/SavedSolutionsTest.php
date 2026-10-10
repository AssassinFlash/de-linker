<?php
/**
 * Saving a solution through the REST route.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use WP_REST_Request;

/**
 * POST linker/v1/solutions as the Solution Configurator (#14) sends it: a
 * customer's solution is saved in the account; a guest's waits in the
 * WooCommerce session and joins the account at login.
 *
 * @coversNothing
 */
final class SavedSolutionsTest extends IntegrationTestCase {

	/**
	 * A customer's save and a guest's save that is claimed at login.
	 */
	public function test_customer_and_guest(): void {
		$product  = $this->product( '1680' );
		$customer = $this->customer();
		$store    = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' );

		$this->as_user( $customer->get_id() );
		$response = $this->save( 'House Barleben', $product->get_id() );
		$this->assertSame( 201, $response->get_status() );
		$data = $response->get_data();
		$this->assertIsArray( $data );
		$saved = (int) $data['id'];
		$this->forget( $saved );
		$this->assertSame( $customer->get_id(), $store->owner( $saved ) );
		$this->assertSame(
			array(
				array(
					'product_id' => $product->get_id(),
					'quantity'   => 2,
				),
			),
			$store->items( $saved )
		);

		$this->as_user( 0 );
		$response = $this->save( 'Guest house', $product->get_id() );
		$this->assertSame( 202, $response->get_status() );
		$this->assertSame( array(), $store->for_customer( 0 ) );

		$this->as_user( $customer->get_id() );
		// WooCommerce fires this when the logged-in customer's next page loads the session.
		/** This action is documented in woocommerce/includes/class-wc-cart-session.php */
		do_action( 'woocommerce_load_cart_from_session' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own action.
		$titles = array();
		foreach ( $store->for_customer( $customer->get_id() ) as $solution ) {
			$this->forget( $solution->ID );
			$titles[] = $solution->post_title;
		}
		sort( $titles );
		$this->assertSame( array( 'Guest house', 'House Barleben' ), $titles );
		$this->assertNull( WC()->session->get( SavedSolutions::SESSION_KEY ) );

		$this->assertSame( 400, $this->save( 'Unknown product', PHP_INT_MAX )->get_status() );
	}

	/**
	 * Sends a solution with one product.
	 *
	 * @param string $title      Name.
	 * @param int    $product_id Product.
	 */
	private function save( string $title, int $product_id ): \WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker/v1/solutions' );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_body(
			(string) wp_json_encode(
				array(
					'kind'  => 'residential',
					'title' => $title,
					'input' => array( 'plz' => '39179' ),
					'lines' => array(
						array(
							'product_id' => $product_id,
							'quantity'   => 2,
						),
					),
				)
			)
		);
		return rest_do_request( $request );
	}

	/**
	 * Removes a saved solution after the test.
	 *
	 * @param int $solution_id Solution.
	 */
	private function forget( int $solution_id ): void {
		$this->later(
			static function () use ( $solution_id ): void {
				wp_delete_post( $solution_id, true );
			}
		);
	}
}

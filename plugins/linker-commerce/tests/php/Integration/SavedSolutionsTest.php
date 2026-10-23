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
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Protection\Identity;
use WP_REST_Request;

/**
 * POST linker/v1/solutions as the Solution Configurator (#14) sends it: a
 * customer's solution is saved in the account; a guest's waits in the
 * WooCommerce session and joins the account at login.
 *
 * @coversNothing
 */
final class SavedSolutionsTest extends IntegrationTestCase {
	/** Native guest admission sees a browser cookie, as a real REST request does. */
	protected function setUp(): void {
		parent::setUp();
		$cookies                     = $_COOKIE;
		$_COOKIE[ Identity::COOKIE ] = bin2hex( random_bytes( 16 ) );
		$this->later(
			static function () use ( $cookies ): void {
				$_COOKIE = $cookies;
			}
		);
	}

	/**
	 * A customer's save and a guest's save that is claimed at login.
	 */
	public function test_customer_and_guest(): void {
		$product  = $this->product( '1680' );
		$customer = $this->customer();
		$store    = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' );

		$this->as_user( $customer->get_id() );
		$response = $this->save( 'House Barleben', $product->get_id() );
		$this->assertSame( 201, $response->get_status(), (string) wp_json_encode( $response->get_data() ) );
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
		$this->assertSame( 202, $response->get_status(), (string) wp_json_encode( $response->get_data() ) );
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

		$this->assertSame( 409, $this->save( 'Unknown product', PHP_INT_MAX )->get_status() );
	}

	/**
	 * The save answers the account page of the request's language (#473).
	 *
	 * The configurator's "Open saved solution" link is the route's `url`, which
	 * SavedSolutions::url() builds with wc_get_account_endpoint_url(). That
	 * function is language-blind in itself; linker-i18n answers it in German
	 * while the request is German (RestLang's `?lang=`, Storefront's German
	 * page id, GermanRoutes' endpoint), so the client's `lang` decides the
	 * address: English without it, the German account path in a German save.
	 */
	public function test_the_open_link_follows_the_request_language(): void {
		$account = (int) get_option( 'woocommerce_myaccount_page_id' );
		if ( ! function_exists( 'pll_get_post' ) || ! pll_get_post( $account, 'de' ) ) {
			$this->markTestSkipped( 'The instance has no German account page; load a live snapshot (just pull load).' );
		}
		$product  = $this->product( '1680' );
		$customer = $this->customer();
		// The guest's drafts would join the next test's account; they are this
		// test's own writes and leave with it.
		$this->later(
			static function (): void {
				WC()->session->set( SavedSolutions::SESSION_KEY, null );
			}
		);

		$this->as_user( 0 );
		$english = $this->save( 'Guest house', $product->get_id(), 'en' )->get_data();
		$this->assertIsArray( $english );
		$this->assertSame( home_url( '/my-account/saved-solutions/' ), $english['url'] );

		$german = $this->save( 'Guest house', $product->get_id(), 'de' )->get_data();
		$this->assertIsArray( $german );
		$this->assertSame( home_url( '/de/mein-konto/gespeicherte-loesungen/' ), $german['url'] );

		// A logged-in save takes the same url() with the solution's fragment.
		$this->as_user( $customer->get_id() );
		$response = $this->save( 'Haus Barleben', $product->get_id(), 'de' );
		$this->assertSame( 201, $response->get_status() );
		$data = $response->get_data();
		$this->assertIsArray( $data );
		$saved = (int) $data['id'];
		$this->forget( $saved );
		$this->assertSame(
			home_url( '/de/mein-konto/gespeicherte-loesungen/#linker-solution-' . $saved ),
			$data['url']
		);
	}

	/**
	 * Sends a solution with one product.
	 *
	 * @param string      $title      Name.
	 * @param int         $product_id Product.
	 * @param string|null $language   The request's `lang` (linker-i18n RestLang), absent for English.
	 */
	private function save( string $title, int $product_id, ?string $language = null ): \WP_REST_Response {
		$fingerprint = str_repeat( 'a', 64 );
		$request     = new WP_REST_Request( 'POST', '/linker/v1/solutions' );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_body(
			(string) wp_json_encode(
				array(
					'kind'                  => 'residential',
					'selection_fingerprint' => $fingerprint,
					'title'                 => $title,
					'input'                 => array( 'plz' => '39179' ),
					'lines'                 => array(
						array(
							'product_id' => $product_id,
							'quantity'   => 2,
						),
					),
				)
			)
		);
		// After the body: parsing JSON replaces the JSON params, while the
		// client's language rides in the query string (linker-tools
		// solutions.ts asks `?lang=`).
		if ( null !== $language ) {
			$request->set_query_params( array( 'lang' => $language ) );
		}
		// Only the private engine transport is a fixture. REST, Woo publication,
		// account persistence and guest claiming use the running native instance.
		$manifest  = Publication::manifest();
		$products  = array_column( $manifest['products'], null, 'product_id' );
		$version   = hash( 'sha256', 'saved-solution-fixture-engine' );
		$result    = array(
			'selection_fingerprint' => $fingerprint,
			'publication'           => array(
				'engineering_contract'   => 2,
				'reference_inputs'       => array(),
				'products'               => isset( $products[ $product_id ] ) ? array(
					array(
						'product_id'       => $product_id,
						'product_revision' => $products[ $product_id ]['product_revision'],
					),
				) : array(),
				'documents'              => array(),
				'compatibility_revision' => $manifest['compatibility_revision'],
			),
			'selected'              => array(
				'lines' => array(
					array(
						'product'  => array(
							'id'    => $product_id,
							'brand' => 'Fixture',
							'model' => 'Recorded model',
						),
						'quantity' => 2,
					),
				),
			),
		);
		$transport = static function ( mixed $pre, array $args, string $url ) use ( $result, $version ): mixed {
			unset( $args );
			if ( ! str_ends_with( $url, '/resource/version' ) && ! str_ends_with( $url, '/selection/validate' ) ) {
				return $pre;
			}
			return array(
				'headers'  => array( 'x-linker-engine-version' => $version ),
				'body'     => wp_json_encode( str_ends_with( $url, '/resource/version' ) ? array( 'version' => $version ) : $result ),
				'response' => array(
					'code'    => 200,
					'message' => 'OK',
				),
				'cookies'  => array(),
				'filename' => null,
			);
		};
		add_filter( 'pre_http_request', $transport, -10, 3 );
		try {
			return rest_do_request( $request );
		} finally {
			remove_filter( 'pre_http_request', $transport, -10 );
		}
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

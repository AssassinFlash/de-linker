<?php
/**
 * Tests for the empty Proforma-request login gate.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Tests for LoginGate.
 *
 * @covers \Linker\Commerce\Presentation\LoginGate
 */
final class LoginGateTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * WooCommerce must not send an empty Proforma request to the solution draft.
	 */
	public function test_register_stops_the_empty_checkout_redirect(): void {
		$gate = new LoginGate();
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );

		$gate->register();

		$this->assertConditionsMet();
	}

	/**
	 * The Proforma-request slug stays on the page; a default checkout still redirects.
	 */
	public function test_keep_empty_checkout_only_on_the_proforma_slug(): void {
		$gate = new LoginGate();
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 36 ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => new WP_Post(
					(object) array(
						'ID'        => 36,
						'post_name' => LoginGate::SLUG,
						'post_type' => 'page',
					)
				),
			)
		);

		$this->assertFalse( $gate->keep_empty_checkout( true ) );
	}

	/**
	 * A default WooCommerce checkout (no Proforma-request slug) still redirects.
	 */
	public function test_default_checkout_still_redirects(): void {
		$gate = new LoginGate();
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 8 ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => new WP_Post(
					(object) array(
						'ID'        => 8,
						'post_name' => 'checkout',
						'post_type' => 'page',
					)
				),
			)
		);

		$this->assertTrue( $gate->keep_empty_checkout( true ) );
	}

	/**
	 * A guest sees the live login-gate copy and the account + products links.
	 */
	public function test_guest_html(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		$html = ( new LoginGate() )->html();

		$this->assertStringContainsString( 'Get your Proforma', $html );
		$this->assertStringContainsString( 'Sign in with your partner account', $html );
		$this->assertStringContainsString( 'reserved for Linker partner accounts', $html );
		$this->assertStringContainsString( 'https://example.test/my-account/', $html );
		$this->assertStringContainsString( 'https://example.test/products/', $html );
		$this->assertStringContainsString( 'sf-checkout-empty', $html );
	}

	/**
	 * A logged-in customer with an empty draft is told to add products, not to sign in.
	 */
	public function test_customer_empty_html(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		$html = ( new LoginGate() )->html();

		$this->assertStringContainsString( 'Nothing to submit yet', $html );
		$this->assertStringContainsString( 'Browse products', $html );
		$this->assertStringNotContainsString( 'Sign in with your partner account', $html );
	}
}

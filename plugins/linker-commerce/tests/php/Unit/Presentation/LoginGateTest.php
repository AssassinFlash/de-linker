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
	 * Without Polylang the gate decides on the checkout page id alone and
	 * never calls into it. This test stubs no pll_* function on purpose: once
	 * one is stubbed, WP_Mock has defined pll_get_post_translations for the
	 * rest of the PHP process and function_exists() would no longer be false —
	 * so this test runs before the ones that stub it (declaration order).
	 */
	public function test_without_polylang_the_checkout_page_alone_decides(): void {
		$this->assertFalse( function_exists( 'pll_get_post_translations' ), 'a pll_* stub from an earlier test leaked into this process' );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 36 ) );
		WP_Mock::userFunction(
			'is_page',
			array(
				'args'   => array( array( 36 ) ),
				'return' => true,
			)
		);

		$this->assertFalse( ( new LoginGate() )->keep_empty_checkout( true ) );
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
	 * The checkout page keeps its empty draft in any language of its
	 * translation group: WooCommerce's checkout is the English page (36),
	 * whose German twin — the Proforma-Anfrage page (4701, a different
	 * post_name) — shares the decision, so the gate reads the Polylang group,
	 * never a slug.
	 */
	public function test_the_checkout_translation_group_keeps_the_empty_draft(): void {
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 36 ) );
		WP_Mock::userFunction(
			'pll_get_post_translations',
			array(
				'return' => array(
					'en' => 36,
					'de' => 4701,
				),
			)
		);
		WP_Mock::userFunction(
			'is_page',
			array(
				'args'   => array( array( 36, 4701 ) ),
				'return' => true,
			)
		);

		$this->assertFalse( ( new LoginGate() )->keep_empty_checkout( true ) );
	}

	/**
	 * A default WooCommerce checkout (not in the checkout page's translation
	 * group) still redirects.
	 */
	public function test_default_checkout_still_redirects(): void {
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 8 ) );
		WP_Mock::userFunction( 'pll_get_post_translations', array( 'return' => array( 'en' => 8 ) ) );
		WP_Mock::userFunction(
			'is_page',
			array(
				'args'   => array( array( 8 ) ),
				'return' => false,
			)
		);

		$this->assertTrue( ( new LoginGate() )->keep_empty_checkout( true ) );
	}

	/**
	 * Without a translation group (Polylang empty) the decision falls back to
	 * the checkout page id alone.
	 */
	public function test_without_translations_only_the_checkout_page_counts(): void {
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 36 ) );
		WP_Mock::userFunction( 'pll_get_post_translations', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'is_page',
			array(
				'args'   => array( array( 36 ) ),
				'return' => true,
			)
		);

		$this->assertFalse( ( new LoginGate() )->keep_empty_checkout( true ) );
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

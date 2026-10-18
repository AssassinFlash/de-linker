<?php
/**
 * Tests for the solution draft summary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\DraftSummary;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Cart;
use WC_Product;
use WP_Mock;

/**
 * Tests for DraftSummary.
 *
 * @covers \Linker\Commerce\Gating\DraftSummary
 */
final class DraftSummaryTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products(
			array(
				1 => 1,
				2 => 2,
			)
		);
		$this->plain_text();
	}

	/**
	 * Guests get the login box instead of the totals. "Register" is the
	 * account's own register page (AuthTemplates::register_url), not the
	 * sign-in page (owner ruling 2026-10-16: sign-in and sign-up split).
	 */
	public function test_guests_see_the_login_box(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction(
			'remove_action',
			array(
				'times' => 1,
				'args'  => array( 'woocommerce_cart_collaterals', 'woocommerce_cart_totals', 10 ),
			)
		);
		WP_Mock::userFunction( 'wc_get_checkout_url', array( 'return' => 'https://example.test/proforma-request/' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/' ) );

		ob_start();
		( new DraftSummary( $this->approved_state(), new PriceDisplay( $this->approved_state() ) ) )->guest_totals();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'href="https://example.test/proforma-request/">Send inquiry</a>', $html );
		$this->assertStringContainsString( 'href="https://example.test/my-account/register/">No account yet? Register</a>', $html );
	}

	/**
	 * Customers keep WooCommerce's totals.
	 */
	public function test_customers_keep_the_totals(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'remove_action', array( 'times' => 0 ) );

		ob_start();
		( new DraftSummary( $this->approved_state(), new PriceDisplay( $this->approved_state() ) ) )->guest_totals();
		$this->assertSame( '', ob_get_clean() );
	}

	/**
	 * A draft with a line without a price says that the Proforma prices it; a fully priced draft says nothing.
	 */
	public function test_unpriced_note(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => 'orderable' ) );
		$priced = Mockery::mock( WC_Product::class );
		$priced->allows(
			array(
				'get_id'        => 1,
				'get_parent_id' => 0,
			)
		);
		$priced->allows( 'get_price' )->with( 'edit' )->andReturn( '10' );
		$unpriced = Mockery::mock( WC_Product::class );
		$unpriced->allows(
			array(
				'get_id'        => 2,
				'get_parent_id' => 0,
			)
		);
		$unpriced->allows( 'get_price' )->with( 'edit' )->andReturn( '' );
		$cart = Mockery::mock( WC_Cart::class );
		$cart->allows( 'get_cart' )->andReturn( array( array( 'data' => $priced ), array( 'data' => $unpriced ) ), array( array( 'data' => $priced ) ) );
		$woocommerce       = new \stdClass();
		$woocommerce->cart = $cart;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		$summary = new DraftSummary( $this->approved_state(), new PriceDisplay( $this->approved_state() ) );

		ob_start();
		$summary->unpriced_note();
		$summary->unpriced_note();
		$this->assertSame( '<tr class="linker-unpriced-note"><td colspan="2">For products without a price, we state the price in your Proforma invoice.</td></tr>', ob_get_clean() );
	}

	/**
	 * Under an inquiry with lines still without a price, the same note, as text in a plain email; under a priced one
	 * and in the team's email, none.
	 */
	public function test_inquiry_note(): void {
		$unpriced = Mockery::mock( \WC_Order_Item_Product::class );
		$unpriced->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( 'unpriced' );
		$unpriced->allows( 'get_total' )->andReturn( '0' );
		$open = Mockery::mock( \WC_Order::class );
		$open->allows( 'get_items' )->andReturn( array( $unpriced ) );
		$priced = Mockery::mock( \WC_Order::class );
		$priced->allows( 'get_items' )->andReturn( array() );
		$summary = new DraftSummary( $this->approved_state(), new PriceDisplay( $this->approved_state() ) );

		ob_start();
		$summary->inquiry_note( $open );
		$summary->inquiry_note( $priced );
		$summary->inquiry_note( $open, true );
		$this->assertSame( '<p class="linker-unpriced-note">For products without a price, we state the price in your Proforma invoice.</p>', ob_get_clean() );

		ob_start();
		$summary->inquiry_note( $open, false, true );
		$this->assertSame( "\nFor products without a price, we state the price in your Proforma invoice.\n", ob_get_clean() );
	}
}

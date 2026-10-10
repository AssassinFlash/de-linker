<?php
/**
 * Tests for the presentation shortcodes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Product;
use WP_Mock;

/**
 * Tests for Shortcodes.
 *
 * @covers \Linker\Commerce\Presentation\Shortcodes
 */
final class ShortcodesTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The shortcodes this plugin adds.
	 */
	public function test_register_adds_the_shortcodes(): void {
		$codes = $this->shortcodes();
		foreach (
			array(
				'linker_price'           => 'price',
				'linker_checkout'        => 'checkout',
				'linker_inquiry_status'  => 'inquiry_status',
				'linker_proforma'        => 'proforma',
				'linker_saved_solutions' => 'saved_solutions',
				'linker_documents'       => 'documents',
			) as $tag => $method
		) {
			WP_Mock::userFunction(
				'add_shortcode',
				array(
					'times' => 1,
					'args'  => array( $tag, array( $codes, $method ) ),
				)
			);
		}

		$codes->register();

		$this->assertConditionsMet();
	}

	/**
	 * A guest sees the gated price HTML of the current product.
	 */
	public function test_price_wraps_the_gated_html(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_price_html' )->andReturn( '<a class="linker-price-login" href="https://example.test/my-account/">Log in for prices</a>' );
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- WooCommerce's global.

		$html = $this->shortcodes()->price();

		$this->assertStringContainsString( 'linker-price', $html );
		$this->assertStringContainsString( 'Log in for prices', $html );
		unset( $GLOBALS['product'] );
	}

	/**
	 * Without a product the price shortcode is empty.
	 */
	public function test_price_without_a_product_is_empty(): void {
		unset( $GLOBALS['product'] );

		$this->assertSame( '', $this->shortcodes()->price() );
	}

	/**
	 * An empty Proforma request prints the login gate instead of WooCommerce's checkout.
	 */
	public function test_checkout_of_an_empty_draft_is_the_login_gate(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		$cart = new class() {
			/**
			 * Empty draft.
			 */
			public function is_empty(): bool {
				return true;
			}
		};
		WP_Mock::userFunction(
			'WC',
			array(
				'return' => (object) array( 'cart' => $cart ),
			)
		);

		$html = $this->shortcodes()->checkout();

		$this->assertStringContainsString( 'Get your Proforma', $html );
		$this->assertStringContainsString( 'Sign in with your partner account', $html );
		$this->assertStringNotContainsString( 'woocommerce_checkout', $html );
	}

	/**
	 * A filled draft, or the confirmation, still uses WooCommerce's checkout shortcode.
	 */
	public function test_checkout_of_a_filled_draft_uses_woocommerce(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$cart = new class() {
			/**
			 * Filled draft.
			 */
			public function is_empty(): bool {
				return false;
			}
		};
		WP_Mock::userFunction(
			'WC',
			array(
				'return' => (object) array( 'cart' => $cart ),
			)
		);
		WP_Mock::userFunction(
			'do_shortcode',
			array(
				'args'   => array( '[woocommerce_checkout]' ),
				'return' => '<form class="checkout">pay</form>',
			)
		);

		$this->assertSame( '<form class="checkout">pay</form>', $this->shortcodes()->checkout() );
	}

	/**
	 * The inquiry status shortcode prints the current inquiry's status.
	 */
	public function test_inquiry_status(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_status' )->andReturn( 'inquiry-received' );
		WP_Mock::userFunction(
			'is_wc_endpoint_url',
			array(
				'return' => static fn ( string $endpoint ): bool => 'view-order' === $endpoint,
			)
		);
		$wp             = new \stdClass();
		$wp->query_vars = array( 'view-order' => 88 );
		$GLOBALS['wp']  = $wp;
		WP_Mock::userFunction( 'absint', array( 'return' => 88 ) );
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'args'   => array( 88 ),
				'return' => $order,
			)
		);
		WP_Mock::userFunction(
			'wc_get_order_status_name',
			array(
				'args'   => array( 'inquiry-received' ),
				'return' => 'Inquiry received',
			)
		);

		$html = $this->shortcodes()->inquiry_status();

		$this->assertStringContainsString( 'Inquiry received', $html );
		$this->assertStringContainsString( 'linker-inquiry-status', $html );
	}

	/**
	 * The Proforma shortcode is a download link when the inquiry has a number.
	 */
	public function test_proforma_download_link(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0007' );
		$order->allows( 'get_id' )->andReturn( 44 );
		WP_Mock::userFunction(
			'is_wc_endpoint_url',
			array(
				'return' => static fn ( string $endpoint ): bool => 'view-order' === $endpoint,
			)
		);
		$wp             = new \stdClass();
		$wp->query_vars = array( 'view-order' => 44 );
		$GLOBALS['wp']  = $wp;
		WP_Mock::userFunction( 'absint', array( 'return' => 44 ) );
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'args'   => array( 44 ),
				'return' => $order,
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => 'https://example.test/?linker-document=proforma&id=44',
			)
		);
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );

		$html = $this->shortcodes()->proforma();

		$this->assertStringContainsString( 'PI-2026-0007', $html );
		$this->assertStringContainsString( 'linker-document=proforma', $html );
	}

	/**
	 * Saved solutions reuse the account template.
	 */
	public function test_saved_solutions(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wc_get_template',
			array(
				'return' => static function (): void {
					echo '<p class="linker-empty">Solutions you save</p>';
				},
			)
		);

		$this->assertStringContainsString( 'linker-empty', $this->shortcodes()->saved_solutions() );
	}

	/**
	 * Documents reuse the account template.
	 */
	public function test_documents(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wc_get_template',
			array(
				'return' => static function (): void {
					echo '<p class="linker-empty">Your Proforma invoices</p>';
				},
			)
		);

		$this->assertStringContainsString( 'linker-empty', $this->shortcodes()->documents() );
	}

	/**
	 * Shortcodes under test, with empty stores.
	 */
	private function shortcodes(): Shortcodes {
		$saved = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		return new Shortcodes(
			new LoginGate(),
			$saved,
			new Documents( $saved, '/plugin/templates/' )
		);
	}
}

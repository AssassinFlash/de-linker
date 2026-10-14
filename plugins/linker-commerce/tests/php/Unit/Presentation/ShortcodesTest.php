<?php
/**
 * Tests for the presentation shortcodes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

require_once dirname( __DIR__, 4 ) . '/includes/Presentation/template-functions.php';

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
	 * The shortcodes this plugin adds — the two the exported templates consume.
	 * The cart template's conditions are the global functions in
	 * template-functions.php; no filter under a condition name exists, because
	 * LiveCanvas resolves lc_if with function_exists().
	 */
	public function test_register_adds_the_shortcodes(): void {
		$codes = $this->shortcodes();
		foreach (
		array(
			'linker_price'        => 'price',
			'linker_checkout'     => 'checkout',
			'linker_draft_empty'  => 'draft_empty',
			'linker_faqs'         => 'faqs',
			'linker_contact_link' => 'contact_link',
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
			WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
			WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/genie/' ) );
			WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
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
			$this->assertStringContainsString( 'Sign in to get your Proforma.', $html );
			$this->assertStringContainsString( 'sf-checkout-genie__pill', $html );
			$this->assertStringContainsString( 'data-linker-genie-open', $html );
			$this->assertStringNotContainsString( 'rounded-xl border', $html );
			$this->assertStringNotContainsString( 'woocommerce_checkout', $html );
	}

		/**
		 * An empty solution draft is the designed empty state: icon, title,
		 * the review note, and the two ways back that still have a page.
		 * The retired batch import is neither a button nor a promise in the
		 * note (GAP-11, owner 2026-10-11).
		 */
	public function test_empty_draft_is_the_designed_empty_state(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		$this->cart_is( true );

		$html = $this->shortcodes()->draft_empty();

		$this->assertStringContainsString( 'sf-cart-empty__icon', $html );
		$this->assertStringContainsString( '<h1>Your solution draft is empty.</h1>', $html );
		$this->assertStringContainsString( 'Browse the products now.', $html );
		$this->assertStringContainsString( 'href="https://example.test/products/"', $html );
		$this->assertStringContainsString( 'href="https://example.test/my-account/"', $html );
		$this->assertStringContainsString( 'Sign in or register', $html );
		$this->assertStringNotContainsString( 'bulk-order', $html );
		$this->assertStringNotContainsString( 'Batch item-number import', $html );
		$this->assertStringNotContainsString( 'item-number', $html );
		$this->assertSame( 2, substr_count( $html, 'class="sf-cart-btn' ) );
		$this->assertStringNotContainsString( 'style=', $html );
	}

		/**
		 * The gate reads the same condition functions the cart template's
		 * [lc_if] calls, so it can never disagree with the branch the visitor
		 * sees: with a filled draft the filled branch holds and the checkout
		 * shortcode stays WooCommerce's own. (The empty side is the login
		 * gate test above; the confirmation side is TemplateFunctionsTest's.)
		 */
	public function test_the_gate_agrees_with_the_condition_on_a_filled_draft(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$this->cart_is( false );
		WP_Mock::userFunction(
			'do_shortcode',
			array(
				'args'   => array( '[woocommerce_checkout]' ),
				'return' => '<form class="checkout">pay</form>',
			)
		);

		$this->assertTrue( linker_commerce_draft_filled() );
		$this->assertFalse( linker_commerce_draft_empty() );
		$this->assertSame( '<form class="checkout">pay</form>', $this->shortcodes()->checkout() );
	}

	/**
	 * A filled draft, or the confirmation, still uses WooCommerce's checkout
	 * shortcode; a signed-in account without approval gets the gate instead.
	 */
	public function test_checkout_of_a_filled_draft_uses_woocommerce(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => fn (): int => $this->signed_in_user ) );
		$this->signed_in( 0 );
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
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

		$this->signed_in( 5 );
		$this->approval_meta( array() );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		$html = $this->shortcodes()->checkout();
		$this->assertStringContainsString( 'under review', $html );
		$this->assertStringNotContainsString( 'woocommerce_checkout', $html );
	}

	/**
	 * The product FAQ lists the English question, answer and citation.
	 */
	public function test_faqs_lists_the_english_question_and_citation(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 1178 );
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- WooCommerce's global.
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 1178, '_linker_faqs', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode(
					array(
						array(
							'question'    => 'What current does the ATS1-T63-A carry?',
							'answer'      => 'Rated current is 50 A.',
							'question_de' => 'Welchen Strom führt die ATS1-T63-A?',
							'answer_de'   => 'Der Nennstrom beträgt 50 A.',
							'citation'    => array(
								'url'   => 'https://de-linker.com/manual.pdf',
								'page'  => 31,
								'title' => 'ATS1 manual',
							),
						),
					)
				),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::passthruFunction( 'wpautop' );

		$html = $this->shortcodes()->faqs();

		$this->assertStringContainsString( '<details class="pdp-disclose"><summary>What current does the ATS1-T63-A carry?', $html );
		$this->assertStringContainsString( 'Rated current is 50 A.', $html );
		$this->assertStringContainsString( '<div class="pdp-disclose-body pdp-reading">', $html );
		$this->assertStringNotContainsString( 'Welchen Strom', $html );
		$this->assertStringNotContainsString( '<section', $html );
		unset( $GLOBALS['product'] );
	}

	/**
	 * A German request uses the German question and answer.
	 */
	public function test_faqs_uses_german_on_a_german_request(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 1178 );
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- WooCommerce's global.
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 1178, '_linker_faqs', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode(
					array(
						array(
							'question'    => 'What current does the ATS1-T63-A carry?',
							'answer'      => 'Rated current is 50 A.',
							'question_de' => 'Welchen Strom führt die ATS1-T63-A?',
							'answer_de'   => 'Der Nennstrom beträgt 50 A.',
							'citation'    => array(
								'url'  => 'https://de-linker.com/manual.pdf',
								'page' => 31,
							),
						),
					)
				),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::passthruFunction( 'wpautop' );

		$html = $this->shortcodes()->faqs();

		$this->assertStringContainsString( 'Welchen Strom führt die ATS1-T63-A?', $html );
		$this->assertStringContainsString( 'Der Nennstrom beträgt 50 A.', $html );
		$this->assertStringNotContainsString( 'What current', $html );
		unset( $GLOBALS['product'] );
	}

	/**
	 * A German request with an empty German answer falls back to the English
	 * answer: the paragraph is never empty.
	 */
	public function test_faqs_falls_back_to_the_english_answer_when_the_german_one_is_empty(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 1178 );
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- WooCommerce's global.
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 1178, '_linker_faqs', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode(
					array(
						array(
							'question'    => 'What current does the ATS1-T63-A carry?',
							'answer'      => 'Rated current is 50 A.',
							'question_de' => 'Welchen Strom führt die ATS1-T63-A?',
							'answer_de'   => '',
							'citation'    => array(
								'url'  => 'https://de-linker.com/manual.pdf',
								'page' => 31,
							),
						),
					)
				),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::passthruFunction( 'wpautop' );

		$html = $this->shortcodes()->faqs();

		$this->assertStringContainsString( 'Welchen Strom führt die ATS1-T63-A?', $html );
		$this->assertStringContainsString( 'Rated current is 50 A.', $html );
		unset( $GLOBALS['product'] );
	}

		/**
		 * The request's cart, empty or not.
		 *
		 * @param bool $vacant Whether the draft has no lines.
		 */
	private function cart_is( bool $vacant ): void {
		$cart = new class( $vacant ) {
			/**
			 * Sets whether the draft has no lines.
			 *
			 * @param bool $vacant Whether the draft has no lines.
			 */
			public function __construct( private bool $vacant ) {}

			/**
			 * Whether the draft has no lines.
			 */
			public function is_empty(): bool {
				return $this->vacant;
			}
		};
			WP_Mock::userFunction(
				'WC',
				array(
					'return' => (object) array( 'cart' => $cart ),
				)
			);
	}

		/**
		 * The shortcodes under test.
		 */
	private function shortcodes(): Shortcodes {
		return new Shortcodes( new LoginGate( new Approval() ), new Approval() );
	}
}

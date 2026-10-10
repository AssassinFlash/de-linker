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
use Linker\Commerce\Tests\TestCase;
use Mockery;
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
	 * The shortcodes this plugin adds — the two the exported templates consume.
	 */
	public function test_register_adds_the_shortcodes(): void {
		$codes = $this->shortcodes();
		foreach (
			array(
				'linker_price'    => 'price',
				'linker_checkout' => 'checkout',
				'linker_faqs'     => 'faqs',
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

		$this->assertStringContainsString( 'data-faq-count="1"', $html );
		$this->assertStringContainsString( 'What current does the ATS1-T63-A carry?', $html );
		$this->assertStringContainsString( 'Rated current is 50 A.', $html );
		$this->assertStringContainsString( 'manual.pdf#page=31', $html );
		$this->assertStringContainsString( 'ATS1 manual, p. 31', $html );
		$this->assertStringNotContainsString( 'Welchen Strom', $html );
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
	 * Shortcodes under test.
	 */
	private function shortcodes(): Shortcodes {
		return new Shortcodes( new LoginGate() );
	}
}

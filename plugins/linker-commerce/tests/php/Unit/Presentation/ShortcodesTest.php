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
					'linker_price'              => 'price',
					'linker_checkout'           => 'checkout',
					'linker_faqs'               => 'faqs',
					'linker_contact_link'       => 'contact_link',
					'linker_contact_invitation' => 'contact_invitation',
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
	 * Each surface prints the live band's English words, the button and the
	 * team mailbox. Words read off the old live pages (2026-10-12/13 captures).
	 *
	 * @dataProvider invitation_surfaces_english
	 * @param string $surface The shortcode's surface.
	 * @param string $eyebrow The band's eyebrow.
	 * @param string $heading The band's heading.
	 * @param string $button  The band's button.
	 */
	public function test_invitation_prints_the_english_band( string $surface, string $eyebrow, string $heading, string $button ): void {
		$this->invitation_page( 'en' );

		$html = $this->shortcodes()->contact_invitation( array( 'surface' => $surface ) );

		$this->assertStringContainsString( 'linker-contact-invitation linker-contact-' . $surface, $html );
		$this->assertStringContainsString( $eyebrow, $html );
		$this->assertStringContainsString( $heading, $html );
		$this->assertStringContainsString( '>' . $button . '</a>', $html );
		$this->assertStringContainsString( 'href="mailto:sales@de-linker.com"', $html );
		$this->assertStringContainsString( 'sales@de-linker.com', $html );
		$this->assertStringNotContainsString( '<style', $html );
		$this->assertStringNotContainsString( 'style=', $html );
	}

	/**
	 * Each surface prints the live band's German words on a German page.
	 *
	 * @dataProvider invitation_surfaces_german
	 * @param string $surface The shortcode's surface.
	 * @param string $eyebrow The band's eyebrow.
	 * @param string $heading The band's heading.
	 * @param string $button  The band's button.
	 */
	public function test_invitation_prints_the_german_band( string $surface, string $eyebrow, string $heading, string $button ): void {
		$this->invitation_page( 'de' );

		$html = $this->shortcodes()->contact_invitation( array( 'surface' => $surface ) );

		$this->assertStringContainsString( $eyebrow, $html );
		$this->assertStringContainsString( $heading, $html );
		$this->assertStringContainsString( '>' . $button . '</a>', $html );
		$this->assertStringNotContainsString( 'A storage solution built around the whole project.', $html );
		$this->assertStringNotContainsString( 'Discuss an EPC requirement', $html );
		$this->assertStringNotContainsString( 'Talk to our technical team', $html );
		$this->assertStringNotContainsString( 'Talk through your storage options', $html );
	}

	/**
	 * An unknown surface uses the solution band, the page the shortcode was
	 * written for. It does not echo the attribute back as text.
	 */
	public function test_invitation_of_an_unknown_surface_uses_the_solution_band(): void {
		$this->invitation_page( 'en' );

		$html = $this->shortcodes()->contact_invitation( array( 'surface' => 'not-a-surface' ) );

		$this->assertStringContainsString( 'linker-contact-solution', $html );
		$this->assertStringContainsString( 'A storage solution built around the whole project.', $html );
		$this->assertStringNotContainsString( 'linker-contact-not-a-surface', $html );
		$this->assertStringNotContainsString( 'not-a-surface', $html );
	}

	/**
	 * An omitted surface is the solution band.
	 */
	public function test_invitation_without_a_surface_uses_the_solution_band(): void {
		$this->invitation_page( 'en' );

		$html = $this->shortcodes()->contact_invitation();

		$this->assertStringContainsString( 'linker-contact-solution', $html );
		$this->assertStringContainsString( 'Explore your project with us', $html );
	}

	/**
	 * The article band is the editorial shape and opens a product request;
	 * the others open a project request and carry the page as context.
	 */
	public function test_invitation_carries_the_page_and_the_request_kind(): void {
		$this->invitation_page( 'en' );

		$article = $this->shortcodes()->contact_invitation( array( 'surface' => 'article' ) );
		$epc     = $this->shortcodes()->contact_invitation( array( 'surface' => 'epc' ) );

		$this->assertStringContainsString( 'linker-contact-editorial', $article );
		$this->assertStringContainsString( 'intent=product', $article );
		$this->assertStringContainsString( 'intent=project', $epc );
		$this->assertStringContainsString( 'Utility storage', $epc );
		$this->assertStringContainsString( 'source=https%3A%2F%2Fexample.test%2Fsolutions%2Futility-storage%2F', $epc );
		$this->assertStringContainsString( 'source_id=746', $epc );
		$this->assertStringNotContainsString( 'linker-contact-editorial', $epc );
	}

	/**
	 * English bands, verbatim from the old live pages.
	 *
	 * @return array<string, array{string, string, string, string}>
	 */
	public static function invitation_surfaces_english(): array {
		return array(
			'solution' => array( 'solution', 'UTILITY-SCALE SOLUTIONS', 'A storage solution built around the whole project.', 'Explore your project with us' ),
			'epc'      => array( 'epc', 'CONTACT LINKER', 'Discuss the project before preparing the full brief.', 'Discuss an EPC requirement' ),
			'services' => array( 'services', 'TECHNICAL PARTNERSHIP', 'A technical partner, wherever your project stands.', 'Talk to our technical team' ),
			'article'  => array( 'article', 'YOUR PROJECT, IN PRACTICE', 'What could the right storage solution do for your site?', 'Talk through your storage options' ),
		);
	}

	/**
	 * German bands, the live page's own wording.
	 *
	 * @return array<string, array{string, string, string, string}>
	 */
	public static function invitation_surfaces_german(): array {
		return array(
			'solution' => array( 'solution', 'LÖSUNGEN FÜR GROSSSPEICHER', 'Ihr Großspeicherprojekt als Gesamtlösung gedacht.', 'Ihr Projekt gemeinsam entwickeln' ),
			'epc'      => array( 'epc', 'KONTAKT ZU LINKER', 'Das Projekt vor dem vollständigen Briefing besprechen.', 'EPC-Anforderung besprechen' ),
			'services' => array( 'services', 'TECHNISCHE ZUSAMMENARBEIT', 'Ein technischer Partner in jeder Projektphase.', 'Mit unserem Technikteam sprechen' ),
			'article'  => array( 'article', 'IHR PROJEKT IN DER PRAXIS', 'Was kann die passende Speicherlösung an Ihrem Standort leisten?', 'Ihre Speicheroptionen besprechen' ),
		);
	}

	/**
	 * A page the band can name, in the given language.
	 *
	 * @param string $language `en` or `de`.
	 */
	private function invitation_page( string $language ): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => $language ) );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 746 ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'Utility storage' ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/solutions/utility-storage/' ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'sanitize_html_class', array( 'return' => fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'shortcode_atts', array( 'return' => fn ( array $pairs, array $atts ): array => array_merge( $pairs, $atts ) ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => function ( array $args, string $url ): string {
					return $url . '?' . http_build_query( $args );
				},
			)
		);
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => fn ( $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => '' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => null ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/contact/' ) );
	}

	/**
	 * Shortcodes under test.
	 */
	private function shortcodes(): Shortcodes {
		return new Shortcodes( new LoginGate( new Approval() ), new Approval() );
	}
}

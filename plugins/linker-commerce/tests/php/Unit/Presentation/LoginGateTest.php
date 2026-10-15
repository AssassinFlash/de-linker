<?php
/**
 * Tests for the empty Proforma-request login gate.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Registration\Approval;
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
			WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
			WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/genie/' ) );
			WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		$this->cart( true );

			$html = ( new LoginGate( $this->approval() ) )->html();

			$this->assertStringContainsString( 'Get your Proforma', $html );
			$this->assertStringContainsString( 'Sign in to get your Proforma.', $html );
			$this->assertStringContainsString( 'reserved for Linker partner accounts', $html );
			$this->assertStringContainsString( 'https://example.test/my-account/', $html );
			$this->assertStringContainsString( 'https://example.test/products/', $html );
			$this->assertStringContainsString( 'linker-gate', $html );
			$this->assertStringContainsString( 'linker-gate-genie-pill', $html );
			$this->assertStringContainsString( 'linker-gate-btn', $html );
			$this->assertStringContainsString( 'data-linker-genie-open', $html );
			// The collapsed state is declared in the markup: the dock flips it
			// to true only when it reports the panel open, and the e2e asserts
			// the strict "false" before any click (closure decision 10).
			$this->assertStringContainsString( 'aria-expanded="false"', $html );
			$this->assertStringContainsString( '>Genie<', $html );
			$this->assertStringContainsString( 'href="https://example.test/genie/"', $html );
			$this->assertStringNotContainsString( 'mx-auto', $html );
			$this->assertStringNotContainsString( 'border-neutral-200', $html );
			$this->assertStringNotContainsString( 'style=', $html );
	}

		/**
		 * On a German request the pill keeps its place and names Genie, and
		 * its address is the German Genie page.
		 */
	public function test_guest_html_on_german_opens_the_german_genie_page(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/de/mein-konto/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static function ( int $id ): string {
					return 77 === $id ? 'https://example.test/de/genie/' : 'https://example.test/de/produkte/';
				},
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => new \WP_Post( (object) array( 'ID' => 40 ) ) ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 77 ) );
		$this->cart( true );

		$html = ( new LoginGate( $this->approval() ) )->html();

		$this->assertStringContainsString( 'href="https://example.test/de/genie/"', $html );
		$this->assertStringContainsString( 'linker-gate-genie-pill', $html );
		$this->assertStringContainsString( '>Genie<', $html );
		$this->assertStringContainsString( 'Sign in to get your Proforma.', $html );
	}

	/**
	 * A logged-in customer with an empty draft is told to add products, not to sign in.
	 */
	public function test_customer_empty_html(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		$html = ( new LoginGate( $this->approval( Approval::APPROVED ) ) )->html();

		$this->assertStringContainsString( 'Nothing to submit yet', $html );
		$this->assertStringContainsString( 'Browse products', $html );
		$this->assertStringNotContainsString( 'Sign in with your partner account', $html );
	}

	/**
	 * A pending account reads the review gate: no sign-in, no Proforma, the
	 * products stay open.
	 */
	public function test_pending_html(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		$html = ( new LoginGate( $this->approval( Approval::PENDING ) ) )->html();

		$this->assertStringContainsString( 'under review', $html );
		$this->assertStringContainsString( 'Browse products', $html );
		$this->assertStringNotContainsString( 'Sign in with your partner account', $html );
		$this->assertStringNotContainsString( 'Nothing to submit yet', $html );
	}

	/**
	 * A restricted account reads its own gate with the team's reason.
	 */
	public function test_restricted_html_carries_the_reason(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		$this->approval_meta(
			array(
				Approval::STATUS_META => Approval::RESTRICTED,
				Approval::REASON_META => 'Net prices are for businesses.',
			)
		);
		$html = ( new LoginGate( new Approval() ) )->html();
		$this->assertStringContainsString( 'limited', $html );
		$this->assertStringContainsString( 'Net prices are for businesses.', $html );
		$this->assertStringContainsString( 'linker-gate-badge is-restricted', $html );
		// The team's mailbox is the mailto link the prototype draws.
		$this->assertStringContainsString( '<a href="mailto:sales@de-linker.com">sales@de-linker.com</a>', $html );
		$this->assertStringNotContainsString( 'Sign in with your partner account', $html );
	}

	/**
	 * A guest with products in the draft reads the draft gate: the draft waits
	 * for the account, and the sign-in card is one tap away (ticket #184).
	 */
	public function test_guest_with_a_filled_draft_reads_the_draft_gate(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		WP_Mock::userFunction( 'wp_lostpassword_url', array( 'return' => 'https://example.test/my-account/lost-password/' ) );
		$this->cart( false );

		$html = ( new LoginGate( $this->approval() ) )->html();

		$this->assertStringContainsString( 'Sign in to request your Proforma', $html );
		$this->assertStringContainsString( 'Your solution draft is saved.', $html );
		$this->assertStringContainsString( 'href="https://example.test/my-account/"', $html );
		$this->assertStringContainsString( 'https://example.test/my-account/lost-password/', $html );
		$this->assertStringContainsString( 'linker-gate-btn is-ghost', $html );
		// The Genie pill belongs to the request itself, not to a draft that exists.
		$this->assertStringNotContainsString( 'linker-gate-genie-pill', $html );
	}

	/**
	 * The pending gate names the review state on the card's badge.
	 */
	public function test_pending_gate_carries_the_state_badge(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		$html = ( new LoginGate( $this->approval( Approval::PENDING ) ) )->html();

		$this->assertStringContainsString( 'linker-gate-badge is-pending', $html );
		$this->assertStringContainsString( 'Under review', $html );
	}

	/**
	 * The approval rule of user 5 with the given state.
	 *
	 * @param string $state The state user 5 is in.
	 */
	private function approval( string $state = Approval::APPROVED ): Approval {
		$this->approval_meta( array( Approval::STATUS_META => $state ) );
		return new Approval();
	}

	/**
	 * The draft condition the gate reads, answered with the given draft. The
	 * cart itself is the shared WC_Cart double.
	 *
	 * @param bool $empty Whether the solution draft holds nothing.
	 */
	private function cart( bool $empty ): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$this->cart_is( $empty );
	}
}

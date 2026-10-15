<?php
/**
 * Tests for the pending-account review page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\PendingGate;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * A pending account is held on the review page. An approved account is not,
 * and neither is a restricted one: that account keeps the workplace and reads
 * its own gate on the Proforma request.
 *
 * @covers \Linker\Commerce\Account\PendingGate
 */
final class PendingGateTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
	}

	/**
	 * A guest is not held: the account page's own login form stays.
	 */
	public function test_a_guest_is_not_held(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$this->assertFalse( ( new PendingGate( new Approval() ) )->holds() );
	}

	/**
	 * A pending sign-in is held; an approved one and a restricted one are not.
	 */
	public function test_holds_only_a_pending_account(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		$this->assertTrue( ( new PendingGate( new Approval() ) )->holds() );

			$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
			$this->signed_in( 5 );
			$this->assertFalse( ( new PendingGate( new Approval() ) )->holds(), 'Approved is let through.' );

			$this->approval_meta( array( Approval::STATUS_META => Approval::RESTRICTED ) );
			$this->signed_in( 5 );
			$this->assertFalse( ( new PendingGate( new Approval() ) )->holds(), 'Restricted keeps the workplace.' );
	}

	/**
	 * Direct requests for an account endpoint are sent back to the account page.
	 */
	public function test_an_endpoint_request_is_sent_back(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'myaccount' ),
				'return' => 'https://example.test/my-account/',
			)
		);
		WP_Mock::userFunction(
			'wp_safe_redirect',
			array(
				'args'   => array( 'https://example.test/my-account/' ),
				'times'  => 1,
				'return' => static function (): void {
					throw new \RuntimeException( 'redirect' );
				},
			)
		);

		try {
			( new PendingGate( new Approval() ) )->redirect();
			$this->fail( 'The redirect must exit, the same as the plugin\'s other redirects.' );
		} catch ( \RuntimeException $stopped ) {
			$this->assertSame( 'redirect', $stopped->getMessage(), 'exit stops the request after the redirect.' );
		}
		$this->assertConditionsMet();
	}

	/**
	 * The account page itself is not redirected: there the account template is
	 * swapped for the review card, and the workplace shell never starts.
	 */
	public function test_the_account_page_swaps_its_template(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
			WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
			WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
			// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
			WP_Mock::expectFilterAdded( 'wc_get_template', array( new WP_Mock\Matcher\AnyInstance( PendingGate::class ), 'template' ), 40, 2 );

			$gate = new PendingGate( new Approval() );
			$gate->redirect();
			$this->assertConditionsMet();

			// The account page's own template is the review card; every other
			// template keeps WooCommerce's path.
			$this->assertStringEndsWith( '/templates/myaccount/auth/pending.php', $gate->template( '/woo/my-account.php', 'myaccount/my-account.php' ) );
			$this->assertSame( '/woo/orders.php', $gate->template( '/woo/orders.php', 'myaccount/orders.php' ) );
	}

	/**
	 * An approved account is not redirected off an endpoint.
	 */
	public function test_an_approved_endpoint_stays(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );

		( new PendingGate( new Approval() ) )->redirect();
		$this->assertFalse( ( new PendingGate( new Approval() ) )->holds() );
	}

	/**
	 * The review page is one card that names the review rather than the
	 * inquiries, and its look is auth.css's own (ticket #184).
	 */
	public function test_render_is_the_review_card(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		ob_start();
		( new PendingGate( new Approval() ) )->render();
		$html = (string) ob_get_clean();

			$this->assertStringContainsString( 'Your account is under review', $html );
			$this->assertStringContainsString( 'Under review', $html );
			$this->assertStringContainsString( 'linker-gate-badge is-pending', $html );
			$this->assertStringContainsString( 'https://example.test/products/', $html );
			$this->assertStringNotContainsString( 'Inquiry received', $html );
			$this->assertStringContainsString( 'linker-gate-btn is-primary', $html );
			$this->assertStringNotContainsString( 'style=', $html );
			$css = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/windpress/auth.css' );
			$this->assertStringContainsString( '.linker-gate {', $css );
			$this->assertStringContainsString( '.linker-gate-badge.is-pending', $css );
	}

	/**
	 * A restricted account is not replaced by the pending page.
	 */
	public function test_a_restricted_account_is_not_replaced(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::RESTRICTED ) );
		$this->signed_in( 5 );

		ob_start();
		( new PendingGate( new Approval() ) )->render();
		$this->assertSame( '', (string) ob_get_clean() );
	}
}

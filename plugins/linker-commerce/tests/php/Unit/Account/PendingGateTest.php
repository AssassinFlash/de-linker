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
				'args'  => array( 'https://example.test/my-account/' ),
				'times' => 1,
			)
		);

		( new PendingGate( new Approval() ) )->redirect();
		$this->assertConditionsMet();
	}

	/**
	 * The account page itself is not redirected: that is where the review page is shown.
	 */
	public function test_the_account_page_itself_stays(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
			WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
			WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
			WP_Mock::userFunction( 'remove_all_actions' );
			WP_Mock::expectActionAdded( 'woocommerce_account_content', array( new WP_Mock\Matcher\AnyInstance( PendingGate::class ), 'render' ), 1 );

			( new PendingGate( new Approval() ) )->redirect();
			$this->assertConditionsMet();
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
	 * The review page replaces the workplace, and names the review rather than the inquiries.
	 */
	public function test_render_replaces_the_workplace(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );
		WP_Mock::userFunction( 'remove_all_actions' );

		ob_start();
		( new PendingGate( new Approval() ) )->render();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'Your account is under review', $html );
		$this->assertStringContainsString( 'https://example.test/products/', $html );
		$this->assertStringNotContainsString( 'Inquiry received', $html );
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

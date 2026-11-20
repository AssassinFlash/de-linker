<?php
/**
 * Guest receipts and the signed-in inquiry owner.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\AccountLink;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;
use WP_User;

/**
 * Account destinations respect inquiry ownership.
 *
 * @covers \Linker\Commerce\Inquiry\AccountLink
 */
final class AccountLinkTest extends TestCase {

	/** Merely opening the signed-in account link never transfers the guest inquiry. */
	public function test_reading_the_receipt_leaves_the_owner_unchanged(): void {
		$saved = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore the test request.
		try {
			$_GET = array(
				'linker_inquiry' => '31',
				'linker_key'     => 'wc_order_test',
			);
			WP_Mock::userFunction( 'absint', array( 'return' => 31 ) );
			WP_Mock::userFunction( 'wp_unslash', array( 'return' => 'wc_order_test' ) );
			WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => 'wc_order_test' ) );
			$order = Mockery::mock( WC_Order::class );
			$order->allows( 'get_order_key' )->andReturn( 'wc_order_test' );
			$order->allows( 'get_customer_id' )->andReturn( 0 );
			$order->allows( 'get_billing_email' )->andReturn( 'buyer@example.test' );
			$buyer             = new WP_User();
			$buyer->user_email = 'buyer@example.test';
			WP_Mock::userFunction( 'get_userdata', array( 'return' => $buyer ) );
			$order->shouldNotReceive( 'set_customer_id' );
			WP_Mock::userFunction( 'wc_get_order', array( 'return' => $order ) );
			$this->assertSame( '/my-account/', AccountLink::destination( '/my-account/', 13 ) );
		} finally {
			$_GET = $saved;
		}
	}
	/**
	 * The browser remembers an inquiry across a native reset. A successful login
	 * must still belong to the inquiry's current owner and consumes the target.
	 *
	 * @dataProvider reset_accounts
	 * @param int    $user_id Authenticated customer.
	 * @param string $destination Expected page after login.
	 */
	public function test_reset_returns_only_the_owner_to_the_saved_quotation( int $user_id, string $destination ): void {
		$get  = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore the test request.
		$post = $_POST; // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Restore the test request.
		try {
			$_GET  = array(
				'linker_quotation' => '31',
				'redirect_to'      => 'https://other.example/path',
			);
			$_POST = array( 'wc_reset_password' => 'true' );
			$order = Mockery::mock( WC_Order::class );
			$order->allows( 'get_customer_id' )->andReturn( 13 );
			$order->allows( 'get_view_order_url' )->andReturn( '/my-account/inquiry/31/' );
			$order->shouldNotReceive( 'set_customer_id' );
			WP_Mock::userFunction( 'wc_get_order', array( 'return' => $order ) );
			WP_Mock::userFunction( 'absint', array( 'return' => 31 ) );
			$session = Mockery::mock( \WC_Session::class );
			$session->expects( 'set' )->with( 'linker_inquiry_after_reset', array( 'linker_quotation' => 31 ) );
			$session->expects( 'get' )->with( 'linker_inquiry_after_reset' )->andReturn( array( 'linker_quotation' => 31 ) );
			$session->expects( '__unset' )->with( 'linker_inquiry_after_reset' );
			$woo = Mockery::mock( \stdClass::class );
			$woo->allows( 'initialize_session' );
			$woo->session = $session;
			WP_Mock::userFunction( 'WC', array( 'return' => $woo ) );
			$link = new AccountLink();
			$link->remember_recovery();
			$_GET     = array();
			$_POST    = array();
			$user     = new WP_User();
			$user->ID = $user_id;
			$this->assertSame( $destination, $link->after_login( '/my-account/', $user ) );
		} finally {
			$_GET  = $get;
			$_POST = $post;
		}
	}

	/**
	 * Two customers follow the same saved quotation.
	 *
	 * @return array<string,array{int,string}> Account and expected destination.
	 */
	public static function reset_accounts(): array {
		return array(
			'owner'         => array( 13, '/my-account/inquiry/31/' ),
			'other account' => array( 14, '/my-account/' ),
		);
	}
}

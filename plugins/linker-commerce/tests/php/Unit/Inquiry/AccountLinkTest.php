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
			$order->shouldNotReceive( 'set_customer_id' );
			WP_Mock::userFunction( 'wc_get_order', array( 'return' => $order ) );
			$this->assertSame( '/my-account/', AccountLink::destination( '/my-account/', 13 ) );
		} finally {
			$_GET = $saved;
		}
	}
}

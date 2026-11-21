<?php
/**
 * Native Woo receipts for a validated customer submission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Protection\Business;
use Linker\Commerce\Protection\Identity;
use WC_Order;
use WP_Error;

/**
 * Exercises a verified customer submission and its native Woo receipt.
 *
 * @coversNothing
 */
final class NativeInquirySubmissionTest extends IntegrationTestCase {
	/** A second request recovers the same order after its first native response is lost. */
	public function test_confirmed_order_recovers_before_rechecking_the_submit_action(): void {
		$id      = wp_generate_uuid4();
		$owner   = new Identity( 'native-submission-guest', '' );
		$payload = array( 'message' => 'Please contact me about a storage system.' );
		$writes  = 0;
		$checks  = 0;
		$write   = function () use ( &$writes ): WC_Order {
			++$writes;
			$order = new WC_Order();
			$order->set_status( Statuses::RECEIVED );
			$order->save();
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
			return $order;
		};
		$check   = static function () use ( &$checks ): bool {
			++$checks;
			return true;
		};
		$first   = Business::write_once( $id, 'contact', $payload, $write, $check, $owner );
		$this->assertInstanceOf( WC_Order::class, $first );
		$again = Business::write_once( $id, 'contact', $payload, $write, $check, $owner );
		$this->assertInstanceOf( WC_Order::class, $again );
		$this->assertSame( $first->get_id(), $again->get_id() );
		$this->assertInstanceOf( WP_Error::class, Business::write_once( $id, 'contact', array( 'message' => 'changed' ), $write, $check, $owner ) );
		$this->assertInstanceOf( WP_Error::class, Business::write_once( $id, 'contact', $payload, $write, $check, new Identity( 'other-guest', '' ) ) );
		$this->assertSame( 1, $checks );
		$this->assertSame( 1, $writes );
	}
}

<?php
/**
 * Native Woo receipts for a validated customer submission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
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

	/** Public admin-post and JSON submissions preserve consent without changing genuine manual orders. */
	public function test_source_on_native_receipts_follows_marketing_consent(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Native request fixture.
		$post    = $_POST;
		$cookies = $_COOKIE;
		$screen  = $GLOBALS['current_screen'] ?? null;
		$this->later(
			static function () use ( $post, $cookies, $screen ): void {
				$_POST                     = $post;
				$_COOKIE                   = $cookies;
				$GLOBALS['current_screen'] = $screen;
			}
		);
		set_current_screen( 'dashboard' );
		$this->assertTrue( is_admin() );
		$details = Submission::from_post(
			array(
				'name'    => 'Source test',
				'email'   => self::TESTER,
				'message' => 'Please review my project.',
				'consent' => '1',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$sender                                   = new Sender();
		$record                                   = function ( WC_Order $order ): WC_Order {
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
			$fresh = wc_get_order( $order->get_id() );
			$this->assertInstanceOf( WC_Order::class, $fresh );
			return $fresh;
		};
		$_COOKIE['cookieyes-consent']             = 'consent:yes,advertisement:no';
		$_POST['wc_order_attribution_utm_source'] = 'linkedin';
		$denied                                   = $sender->message( $details );
		$this->assertInstanceOf( WC_Order::class, $denied );
		foreach ( $record( $denied )->get_meta_data() as $meta ) {
			$this->assertStringStartsNotWith( '_wc_order_attribution_', $meta->key );
		}

		$_COOKIE['cookieyes-consent'] = 'consent:yes,advertisement:yes';
		unset( $_COOKIE['wp_consent_marketing'] );
		$_POST['wc_order_attribution_source_type']   = 'utm';
		$_POST['wc_order_attribution_utm_medium']    = 'social';
		$_POST['wc_order_attribution_session_entry'] = 'https://example.org/contact/?utm_source=linkedin';
		$allowed                                     = $sender->message( $details );
		$this->assertInstanceOf( WC_Order::class, $allowed );
		$allowed = $record( $allowed );
		$this->assertSame( 'utm', $allowed->get_meta( '_wc_order_attribution_source_type' ) );
		$this->assertSame( 'linkedin', $allowed->get_meta( '_wc_order_attribution_utm_source' ) );
		$this->assertSame( 'social', $allowed->get_meta( '_wc_order_attribution_utm_medium' ) );
		$this->assertSame( 'https://example.org/contact/', $allowed->get_meta( '_wc_order_attribution_session_entry' ) );
		$this->assertSame( array( 'utm' ), array_map( static fn ( $meta ) => $meta->value, $allowed->get_meta( '_wc_order_attribution_source_type', false ) ) );

		$_POST                       = array();
		$_COOKIE['sbjs_current']     = 'typ=referral|||src=linkedin.com|||mdm=referral';
		$_COOKIE['sbjs_current_add'] = 'ep=https://example.org/genie/|||rf=https://www.linkedin.com/feed/';
		$genie                       = $sender->message( $details );
		$this->assertInstanceOf( WC_Order::class, $genie );
		$genie = $record( $genie );
		$this->assertSame( 'referral', $genie->get_meta( '_wc_order_attribution_source_type' ) );
		$this->assertSame( 'https://www.linkedin.com/feed/', $genie->get_meta( '_wc_order_attribution_referrer' ) );

		$manual = new WC_Order();
		$manual->set_created_via( 'admin' );
		$manual->save();
		$this->assertSame( 'admin', $record( $manual )->get_meta( '_wc_order_attribution_source_type' ) );
	}

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
	/** A historical order cannot issue a receipt until Woo saves its received status. */
	public function test_historical_pending_order_waits_for_a_successful_woo_status_save(): void {
		$id      = wp_generate_uuid4();
		$owner   = new Identity( 'stored-contact', '' );
		$payload = array( 'message' => 'Please check our existing inquiry.' );
		$order   = new WC_Order();
		$order->set_status( 'pending' );
		$order->update_meta_data( \Linker\Commerce\Protection\BusinessRecord::REQUEST, $id );
		$order->update_meta_data( \Linker\Commerce\Protection\BusinessRecord::SUBJECT, $owner->binding() );
		$fingerprint = \Linker\Commerce\Protection\Fingerprint::make( $owner, 'contact', $payload );
		$this->assertIsString( $fingerprint );
		$order->update_meta_data( \Linker\Commerce\Protection\BusinessRecord::INPUT, $fingerprint );
		$order->update_meta_data( \Linker\Commerce\Protection\IntakeStore::META, array( 'lane' => 'verification' ) );
		$order->update_meta_data( \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'verification_review' ) );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$fail = static function ( WC_Order $saving ) use ( $order ): void {
			if ( $order->get_id() === $saving->get_id() && $saving->has_status( Statuses::RECEIVED ) ) {
				throw new \RuntimeException( 'Native status storage unavailable.' );
			}
		};
		add_action( 'woocommerce_before_order_object_save', $fail );
		try {
			$result = Business::write_once( $id, 'contact', $payload, static fn () => self::fail( 'An existing order cannot be written twice.' ), static fn () => true, $owner );
		} finally {
			remove_action( 'woocommerce_before_order_object_save', $fail );
		}
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_inquiry_pending', $result->get_error_code() );
		$saved = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $saved );
		$this->assertSame( 'pending', $saved->get_status() );
	}
}

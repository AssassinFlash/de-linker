<?php
/**
 * The two public submission doors and their shared abuse boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Inquiry\Handler;
use Linker\Commerce\Mail\Throttle;
use WC_Order;

/**
 * Public request acceptance and rejection.
 *
 * @coversNothing
 */
final class PublicSubmissionTest extends IntegrationTestCase {

	/**
	 * Round-one decision: three accepted messages per connection per hour,
	 * shared across both doors; the next attempt cannot queue any mail.
	 *
	 * @dataProvider doors
	 * @param string $door The door used for the over-limit attempt.
	 */
	public function test_an_over_limit_guest_cannot_queue_mail_on_either_door( string $door ): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$stamp = (string) ( time() - 5 );
		$post  = array(
			'name'                 => '246 Tester',
			'email'                => 'tester246-limit-' . self::tag() . '@example.test',
			'message'              => 'A test inquiry.',
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_contact_nonce' => wp_create_nonce( 'linker_contact_form' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		for ( $attempt = 0; $attempt < 3; ++$attempt ) {
			$order = ( new Handler() )->process( $post );
			$this->assertInstanceOf( WC_Order::class, $order );
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
		}
		$marker = self::newest_mail_job();
		$result = 'request' === $door ? ( new Handler() )->process( $post ) : ( new ContactHandler() )->process( $post );
		if ( $result instanceof WC_Order ) {
			$this->later(
				static function () use ( $result ): void {
					$result->delete( true );
				}
			);
		}
		if ( 'request' === $door ) {
			$this->assertInstanceOf( \WP_Error::class, $result );
		} else {
			$this->assertSame( 'throttled', $result );
		}
		$this->assertSame( array(), self::mail_jobs_after( $marker ), 'The rejected attempt creates no team mail or customer receipt.' );
	}

	/**
	 * Both public doors.
	 *
	 * @return array<string, array{string}>
	 */
	public static function doors(): array {
		return array(
			'request' => array( 'request' ),
			'contact' => array( 'contact' ),
		);
	}
}

<?php
/**
 * The two public submission doors and their shared abuse boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;

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
	/** Install only this test's bound local service seam. */
	protected function setUp(): void {
		parent::setUp();
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
	}

	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

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
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
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

	/** Eight independent requests share three slots across both doors. */
	public function test_parallel_public_requests_accept_exactly_three_and_queue_no_rejected_mail(): void {
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$email = 'tester246-parallel-' . self::tag() . '@example.test';
		$this->later(
			static function () use ( $email ): void {
				$orders = wc_get_orders(
					array(
						'billing_email' => $email,
						'limit'         => -1,
					)
				);
				self::assertIsArray( $orders );
				foreach ( $orders as $order ) {
					$order->delete( true );
				}
			}
		);
		$marker  = self::newest_mail_job();
		$workers = array();
		$start   = (string) ( microtime( true ) + 8 );
		for ( $i = 0; $i < 8; ++$i ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- independent requests are necessary to exercise database serialization.
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', __DIR__ . '/fixtures/public-submit.php', $email, 0 === $i % 2 ? 'request' : 'contact', $start ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes
			);
			$this->assertIsResource( $process );
			$workers[] = array( $process, $pipes );
		}
		$accepted = 0;
		foreach ( $workers as list( $process, $pipes ) ) {
			$output = trim( (string) stream_get_contents( $pipes[1] ) );
			$error  = (string) stream_get_contents( $pipes[2] );
			fclose( $pipes[1] );
			fclose( $pipes[2] );
			$this->assertSame( 0, proc_close( $process ), $error . $output );
			$accepted += 'sent' === $output ? 1 : 0;
		}
		// Other PHP requests invalidated persistent caches; discard this process's stale runtime cache.
		wp_cache_flush_runtime();
		$this->assertSame( 3, $accepted, 'Parallel posts cannot share the last allowance.' );
		$orders = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $orders );
		$this->assertCount( 3, $orders );
		foreach ( $orders as $accepted_order ) {
			$native = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $accepted_order->get_id() );
			$this->assertIsArray( $native );
			$this->assertSame( 0, $native['attempts'], 'The submitting child must not let an unrelated background request consume this fixture source before the parent installs its typed service.' );
			$accepted_order->read_meta_data( true );
			$this->assertSame( 'yes', $accepted_order->get_meta( \Linker\Commerce\Inquiry\Assessment\Queue::PENDING ) );
			$this->assertSame( 'Parallel public inquiry.', $accepted_order->get_customer_note() );
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $accepted_order->get_id() );
			$this->authorization->process( $accepted_order );
		}
		$this->authorization->drain();
		$this->assertCount( 6, self::mail_jobs_after( $marker ), 'Only the three accepted inquiries produce a team row and receipt.' );
	}

	/**
	 * Ten receipts are the chosen tenth of the sourced 100/day host quota.
	 * A later inquiry still creates its record and team mail through either door.
	 *
	 * @dataProvider doors
	 * @param string $door Public door used after the site-wide cap.
	 */
	public function test_receipt_cap_keeps_the_inquiry_and_team_mail_and_discloses_the_omitted_receipt( string $door ): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$seed_email = 'tester246-seed-' . self::tag() . '@example.test';
		$details    = \Linker\Commerce\Contact\Submission::from_handoff(
			array(
				'email'   => $seed_email,
				'message' => 'Please contact me.',
				'consent' => '1',
			)
		);
		$this->assertInstanceOf( \Linker\Commerce\Contact\Submission::class, $details );
		$before = self::newest_mail_job();
		for ( $i = 0; $i < 10; ++$i ) {
			$order = ( new \Linker\Commerce\Inquiry\Sender() )->message( $details );
			$this->assertInstanceOf( \WC_Order::class, $order );
			$this->assertSame( '', $order->get_billing_first_name(), 'A hand-off name is optional.' );
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
		}
		$this->authorization->drain();
		$this->assertCount( 20, self::mail_jobs_after( $before ), 'Each allowed nameless message still gets the ordinary receipt and team mail.' );
		$stamp  = (string) ( time() - 5 );
		$email  = 'tester246-cap-' . self::tag() . '@example.test';
		$post   = array(
			'name'                 => '246 Tester',
			'email'                => $email,
			'message'              => 'A test inquiry.',
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_contact_nonce' => wp_create_nonce( 'linker_contact_form' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$marker = self::newest_mail_job();
		$result = 'request' === $door ? ( new Handler() )->process( $post ) : ( new ContactHandler() )->process( $post );
		$orders = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $orders );
		foreach ( $orders as $order ) {
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			); }
		$this->assertCount( 1, $orders );
		$this->assertSame( 'inquiry-received', $orders[0]->get_status() );
		if ( 'contact' === $door ) {
			$this->assertSame( 'sent_no_receipt', $result, 'An exhausted receipt allowance is not reported as a sent receipt.' );
			$this->assertSame( 'sent_no_receipt', \Linker\Commerce\Contact\Handler::receipt_state( $orders[0] ) );
			$before_handoff = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- retain and restore the display state in this test.
			$_GET           = array(
				\Linker\Commerce\Contact\Form::STATE_PARAM => 'sent_no_receipt',
			);
			$pending_html   = ( new \Linker\Commerce\Contact\Form() )->render();
			$_GET           = $before_handoff;
			$this->assertStringContainsString( 'linker-form-success', $pending_html );
			$this->assertStringContainsString( 'We have not sent a confirmation email.', $pending_html );
		}
		$this->authorization->drain();
		$jobs = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $jobs, 'Only the team notification is queued after the receipt cap.' );
		$message = json_decode( (string) get_post_meta( $jobs[0], '_linker_mail_message', true ), true );
		$this->assertSame( array( ( new \Linker\Commerce\Settings\Options() )->notify_to() ), $message['to'] );
		$this->assertNotContains( $email, $message['to'] );
		$orders[0]->read_meta_data( true );
		$this->assertSame( 'daily_cap', $orders[0]->get_meta( '_linker_receipt_skipped' ) );
		if ( 'contact' === $door ) {
			$this->assertSame( 'sent_no_receipt', $result, 'Saving must not report an exhausted receipt allowance as sent.' );
			$this->assertSame( 'sent_no_receipt', \Linker\Commerce\Contact\Handler::receipt_state( $orders[0] ) );
			$previous = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- retain and restore the display state in this test.
			try {
				$_GET = array(
					\Linker\Commerce\Contact\Form::STATE_PARAM => 'receipt_pending',
					\Linker\Commerce\Contact\Form::ORDER_PARAM => $orders[0]->get_order_key(),
				);
				$html = ( new \Linker\Commerce\Contact\Form() )->render();
				$this->assertStringNotContainsString( 'http-equiv="refresh"', $html, 'A decided omission does not keep reloading.' );
				switch_to_locale( 'de_DE_formal' );
				$german = ( new \Linker\Commerce\Contact\Form() )->render();
			} finally {
				restore_previous_locale();
				$_GET = $previous;
			}
			$this->assertStringContainsString( 'Eine Bestätigung per E-Mail wurde nicht versendet.', $german );
		} else {
			$this->assertInstanceOf( WC_Order::class, $result );
			ob_start();
			( new \Linker\Commerce\Inquiry\Checkout() )->next_steps( $orders[0]->get_id() );
			$html = (string) ob_get_clean();
		}
		$this->assertStringContainsString( 'linker-form-success', $html );
		$this->assertStringContainsString( 'We have not sent a confirmation email.', $html );
	}

	/**
	 * Optional-name callers get complete, localized letters without blank placeholders.
	 *
	 * @testWith ["en", "Hello,"]
	 *           ["de", "Guten Tag,"]
	 * @param string $language Inquiry language.
	 * @param string $greeting Independently reviewed generic salutation.
	 */
	public function test_nameless_handoff_has_complete_customer_and_team_letters( string $language, string $greeting ): void {
		$this->as_user( 0 );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$email   = 'tester246-nameless-' . self::tag() . '@example.test';
		$details = \Linker\Commerce\Contact\Submission::from_handoff(
			array(
				'email'   => $email,
				'message' => 'Please contact me.',
				'consent' => '1',
				'lang'    => $language,
			)
		);
		$this->assertInstanceOf( \Linker\Commerce\Contact\Submission::class, $details );
		$marker = self::newest_mail_job();
		$order  = ( new \Linker\Commerce\Inquiry\Sender() )->message( $details );
		$this->assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->authorization->drain();
		$rows     = array_map( static fn ( int $id ): array => json_decode( (string) get_post_meta( $id, '_linker_mail_message', true ), true ), self::mail_jobs_after( $marker ) );
		$receipts = array_values( array_filter( $rows, static fn ( array $row ): bool => array( $email ) === $row['to'] ) );
		$team     = array_values( array_filter( $rows, static fn ( array $row ): bool => array( $email ) !== $row['to'] ) );
		$this->assertCount( 1, $receipts );
		$this->assertSame( 1, preg_match( '/<p[^>]*>\s*' . preg_quote( $greeting, '/' ) . '\s*<\/p>/', $receipts[0]['body'] ), 'The receipt has a complete salutation without an empty name.' );
		$this->assertCount( 1, $team );
		$this->assertStringEndsWith( $email, $team[0]['subject'] );
		$this->assertStringContainsString( $email . '.', $team[0]['body'] );
		$this->assertStringNotContainsString( '().', $team[0]['body'] );
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

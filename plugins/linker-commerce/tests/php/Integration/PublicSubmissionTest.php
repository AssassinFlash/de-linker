<?php
/**
 * The two public submission doors and their shared abuse boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;

use Linker\Commerce\Contact\Form as ContactForm;
use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\ReceiptBudget;
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
		$this->use_empty_mail_queue();
		$before = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$this->later(
			static function () use ( $before ): void {
				if ( false === $before ) {
					delete_option( Ledger::OPTION );
				} else {
					update_option( Ledger::OPTION, $before, false );
				}
			}
		);
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

	/** The received transition persists its recovery marker before handing a committed inquiry to the Outbox. */
	public function test_outbox_handoff_uses_the_committed_inquiry(): void {
		$details = \Linker\Commerce\Contact\Submission::from_post(
			array(
				'name'    => 'Installer',
				'email'   => 'commit-' . self::tag() . '@example.test',
				'message' => 'Please advise on storage for our building.',
				'consent' => '1',
			)
		);
		self::assertInstanceOf( \Linker\Commerce\Contact\Submission::class, $details );
		$during  = null;
		$observe = static function ( int $id ) use ( &$during ): void {
			$during = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $id );
		};
		$event   = 'woocommerce_order_status_pending_to_inquiry-received_notification';
		add_action( $event, $observe, PHP_INT_MAX );
		try {
			$order = ( new \Linker\Commerce\Inquiry\Sender() )->message( $details );
		} finally {
			remove_action( $event, $observe, PHP_INT_MAX );
		}
		self::assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		self::assertIsArray( $during );
		self::assertSame( 'pending', $during['status'] );
		self::assertSame( array(), $during['jobs'] );
		self::assert_awaiting_assessment( $order );
	}

	/**
	 * A repeat recipient can have mail withheld while the team receives the full inquiry.
	 *
	 * @dataProvider doors
	 * @param string $door Native form.
	 */
	public function test_recipient_suppression_preserves_woo_and_the_team_handoff( string $door ): void {
		$this->as_user( $this->customer()->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$cookies = $_COOKIE; // phpcs:ignore WordPress.Security.NonceVerification -- Restore the customer's original native request cookies.
		$this->later(
			static function () use ( $cookies ): void {
				$_COOKIE = $cookies;
			}
		);
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'c', 32 );
		$email                       = 'repeat-recipient-' . self::tag() . '@example.test';
		$this->assertTrue( ReceiptBudget::take( $email, wp_generate_uuid4() ) );
		$this->assertTrue( ReceiptBudget::take( $email, wp_generate_uuid4() ) );
		$post   = array(
			'name'                 => 'Installer',
			'email'                => $email,
			'message'              => 'Please advise on this storage project.',
			'consent'              => '1',
			'linker_request_id'    => wp_generate_uuid4(),
			'linker_draft_hash'    => WC()->cart->get_cart_hash(),
			'linker_inquiry_nonce' => wp_create_nonce( Handler::ACTION ),
			'linker_contact_nonce' => wp_create_nonce( ContactForm::NONCE_ACTION ),
		);
		$result = 'contact' === $door ? ( new ContactHandler() )->process( $post ) : ( new Handler() )->process( $post );
		$orders = wc_get_orders( array( 'billing_email' => $email ) );
		$this->assertIsArray( $orders );
		$this->assertCount( 1, $orders );
		$order = $orders[0];
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( $post['message'], $order->get_customer_note() );
		if ( 'contact' === $door ) {
			$this->assertSame( 'receipt_pending', $result );
		} else {
			$this->assertInstanceOf( WC_Order::class, $result );
			$this->assertSame( $order->get_id(), $result->get_id() );
		}
		$state = $this->authorization->process( $order );
		$this->assertSame( array( 'team' ), array_keys( $state['jobs'] ) );
		$job = ( new \Linker\Commerce\Mail\JobStore() )->load( $state['jobs']['team']['id'] );
		$this->assertNotNull( $job );
		$this->assertStringContainsString( $post['message'], $job['message']->body );
		$this->assertNotContains( $email, $job['message']->to );
		$order->read_meta_data( true );
		$this->assertSame( 'target_cap', $order->get_meta( ReceiptLimit::SKIPPED_META ) );

		$previous = $_GET; // phpcs:ignore WordPress.Security.NonceVerification -- Render the receipt returned by the form.
		$_GET     = array(
			ContactForm::STATE_PARAM => 'receipt_pending',
			ContactForm::ORDER_PARAM => $order->get_order_key(),
		);
		try {
			foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
				$switch = new LocaleSwitch();
				$switch->to( $locale );
				try {
					if ( 'contact' === $door ) {
						$html    = ( new ContactForm() )->render();
						$message = 'en_US' === $locale ? 'We have not sent a confirmation email.' : 'Eine Bestätigung per E-Mail wurde nicht versendet.';
					} else {
						ob_start();
						( new \Linker\Commerce\Inquiry\Checkout() )->next_steps( $order->get_id() );
						$html    = (string) ob_get_clean();
						$message = 'en_US' === $locale ? 'We have not sent a confirmation email.' : 'Es wurde keine Bestätigungs-E-Mail versendet.';
					}
					$this->assertStringContainsString( $message, $html );
					$this->assertStringContainsString( '#' . $order->get_order_number(), $html );
				} finally {
					$switch->back();
				}
			}
		} finally {
			$_GET = $previous;
		}
	}

	/**
	 * The fixed acknowledgement and team notification remain usable when a visitor gives no name.
	 *
	 * @testWith ["en", "We reply within one business day."]
	 *           ["de", "Wir antworten innerhalb eines Arbeitstags."]
	 * @param string $language Inquiry language.
	 * @param string $promise Localized reply promise.
	 */
	public function test_nameless_handoff_has_complete_customer_and_team_letters( string $language, string $promise ): void {
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
		$this->assertStringContainsString( $promise, $receipts[0]['body'] );
		$this->assertStringContainsString( '#' . $order->get_order_number(), $receipts[0]['body'] );
		$this->assertStringNotContainsString( 'Please contact me.', $receipts[0]['body'] );
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

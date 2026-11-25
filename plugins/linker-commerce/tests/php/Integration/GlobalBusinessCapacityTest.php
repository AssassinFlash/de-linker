<?php
/**
 * Woo intake and recovery of its notification jobs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Private fixture configuration is restored, never production.

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Registration\Approval;
use WC_Order;
use WP_Error;

/**
 * A durable customer inquiry can outlive temporary mail congestion.
 *
 * @coversNothing
 */
final class GlobalBusinessCapacityTest extends IntegrationTestCase {
	/**
	 * Customer destination unique to this case.
	 *
	 * @var string
	 */
	private string $recipient;

	/** Preserve the local snapshot's pre-existing jobs and capacity ledger. */
	protected function setUp(): void {
		parent::setUp();
		$this->recipient = wp_generate_uuid4() . '@example.test';
		foreach ( array( IntakeStore::OPTION, Ledger::OPTION, \Linker\Commerce\Mail\CapacityHealth::OPTION ) as $option ) {
			$before = get_option( $option );
			delete_option( $option );
			$this->later(
				static function () use ( $before, $option ): void {
					delete_option( $option );
					if ( false !== $before ) {
						update_option( $option, $before, false );
					}
				}
			);
		}
		$this->use_empty_mail_queue();
	}

	/** A previous capacity snapshot cannot refuse a customer's new inquiry. */
	public function test_native_contact_is_received_when_the_old_ordinary_pool_is_full(): void {
		$this->seed_business( 128 );
		$details = $this->details();
		$order   = ( new Sender() )->message( $details );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$received = wc_get_order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $received );
		self::assertSame( Statuses::RECEIVED, $received->get_status() );
		self::assertSame( $details->email, $received->get_billing_email() );
		self::assertSame( $details->message, $received->get_customer_note() );
		self::assertCount( 128, get_option( IntakeStore::OPTION )['business'] );
	}

	/** Native approved changes stop before account/session changes when critical is full. */
	public function test_approval_preflight_preserves_previous_decision_when_critical_pool_is_full(): void {
		$customer    = $this->customer();
		$id          = $customer->get_id();
		$before      = get_user_meta( $id, Approval::STATUS_META, true );
		$reservation = Capacity::reserve_critical( 'synthetic-full-critical-' . self::tag(), 64, 1 );
		self::assertIsArray( $reservation );
		$this->as_user( 1 );
		self::assertFalse( ( new Approval() )->set( $id, Approval::RESTRICTED, str_repeat( 'Complete staff reason. ', 14000 ) ) );
		self::assertSame( $before, get_user_meta( $id, Approval::STATUS_META, true ) );
	}

	/** Saved team notices survive a full queue, recover once and spend no model.
	 *
	 * @dataProvider notification_modes
	 * @param bool $assessment Whether native classification is enabled.
	 */
	public function test_saved_inquiry_stays_durably_pending_when_queue_is_full_then_recovers_one_original_job( bool $assessment ): void {
		$this->seed_business( 0 );
		$normal = $this->normal();
		update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, $assessment ? 'yes' : 'no' );
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 1; $i <= 190; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					); }
				IntakeStore::save( $state );
				return array();
			}
		);
		$spaces = array();
		for ( $i = 0; $i < 2; ++$i ) {
			$spaces[] = ( new JobStore() )->create( new Message( array( self::TESTER ), 'Synthetic occupied native slot', 'No transport.', array(), array() ) ); }
		foreach ( $spaces as $space ) {
			self::assertGreaterThan( 0, $space ); }
		$budget = get_option( OptionBudgetLedger::OPTION );
		$before = self::newest_mail_job();
		$order  = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		self::assertSame( array(), self::mail_jobs_after( $before ) );
		\Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::consume( \Linker\Commerce\Inquiry\Assessment\Queue::PROCESS, $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'approved', $state['status'] );
		self::assertSame( 'normal', $state['verdict']['decision'] );
		self::assertCount( 1, $normal->requests );
		self::assertSame( array(), self::mail_jobs_after( $before ) );
		$order = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( 'yes', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Queue::PENDING ) );
		self::assertSame( 'assessment_pending', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		foreach ( $spaces as $space ) {
			( new JobStore() )->delete( $space ); }
		\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$order->get_id(),
			static function ( array &$state ): void {
				$state['next_at'] = time() - 1;
			}
		);
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'normal', $state['status'] );
		self::assertEqualsCanonicalizing( array( 'team', 'receipt' ), array_keys( $state['jobs'] ) );
		self::assertCount( 2, self::mail_jobs_after( $before ) );
		$jobs = $state['jobs'];
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$repeat = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $repeat );
		self::assertSame( $jobs, $repeat['jobs'] );
		self::assertCount( 1, $normal->requests, 'Queue recovery reuses the bound verdict without another model.' );
	}

	/**
	 * Real connection loss before/after the first native order row cannot replay partial saves.
	 *
	 * @testWith ["contact", false]
	 *           ["contact", true]
	 *           ["inquiry", false]
	 *           ["inquiry", true]
	 * @param string $door Real native entry.
	 * @param bool   $partial Whether the native HPOS row already exists uncommitted.
	 */
	public function test_actual_sender_disconnect_has_no_partial_native_business_or_notification( string $door, bool $partial ): void {
		global $wpdb;
		$this->seed_business( 0 );
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$product = $this->product( '100' );
		self::assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
		$this->later( static fn () => WC()->cart->empty_cart() );
		$draft   = WC()->cart->get_cart();
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic connection',
				'email'   => 'atomic568-' . self::tag() . '@example.test',
				'message' => 'Keep this full native request.',
				'lang'    => 'en',
				'consent' => '1',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		$other  = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$hpos   = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled();
		$table  = $hpos ? $wpdb->prefix . 'wc_orders' : $wpdb->posts;
		$field  = $hpos ? 'billing_email' : 'post_excerpt';
		$value  = $hpos ? $details->email : $details->message;
		$killed = false;
		$native = 0;
		$before = self::newest_mail_job();
		$kill   = static function ( string $sql ) use ( $partial, $table, $field, $value, $other, &$killed, &$native ): string {
			global $wpdb;
			$target = $partial ? str_contains( $sql, '_linker_inquiry_source' ) : str_contains( str_replace( '`', '', $sql ), $table . ' (' );
			if ( ! $killed && str_starts_with( ltrim( $sql ), 'INSERT' ) && $target ) {
				$killed = true;
				$native = (int) $wpdb->get_var( $wpdb->prepare( 'SELECT id FROM %i WHERE %i=%s', $table, $field, $value ) );
				$other->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill, 999 );
		try {
			$result = 'contact' === $door ? ( new Sender() )->message( $details ) : ( new Sender() )->request( $details, array(), false );
		} finally {
			remove_filter( 'query', $kill, 999 );
		}
		if ( $result instanceof WC_Order ) {
			$this->later(
				static function () use ( $result ): void {
					$result->delete( true );
				}
			);
		}
		self::assertTrue( $killed );
		self::assertInstanceOf( WP_Error::class, $result );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE %i=%s', $table, $field, $value ) ) );
		if ( $partial ) {
			self::assertGreaterThan( 0, $native );
			self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE %i=%d', $hpos ? $wpdb->prefix . 'wc_orders_meta' : $wpdb->postmeta, $hpos ? 'order_id' : 'post_id', $native ) ) );
		}
		self::assertTrue( $wpdb->db_connect( false ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( $draft, WC()->cart->get_cart() );
		self::assertSame( 'Keep this full native request.', $details->message );
		$other->close();
	}

	/** Sender's native phase rolls back an exception before notifications and keeps the draft. */
	public function test_sender_native_failure_does_not_leave_a_partially_received_record(): void {
		$this->seed_business( 0 );
		$details = $this->details();
		$marker  = self::newest_mail_job();
		$draft   = WC()->cart->get_cart();
		$fail    = static function (): void {
			throw new \Error( 'synthetic_failure_before_notification' );
		};
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $fail, 1 );
		try {
			$result = ( new Sender() )->message( $details );
		} finally {
			remove_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $fail, 1 );
		}
		self::assertInstanceOf( WP_Error::class, $result );
		self::assertSame( 'linker_intake_pending', $result->get_error_code() );
		$orders = wc_get_orders(
			array(
				'billing_email' => $details->email,
				'limit'         => -1,
			)
		);
		self::assertIsArray( $orders );
		self::assertCount( 0, $orders );
		self::assertSame( $marker, self::newest_mail_job() );
		self::assertSame( $draft, WC()->cart->get_cart() );
		self::assertSame( 'Please advise on equipment for this project.', $details->message );
	}

	/** The native received save survives PHP failure before the first mail callback. */
	public function test_first_save_without_status_callback_recovers_only_after_current_normal_permission(): void {
		$this->seed_business( 0 );
		$before = get_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED );
		update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, 'no' );
		$this->later(
			static function () use ( $before ): void {
				false === $before ? delete_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED ) : update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, $before, false );
			}
		);
		$details = $this->details();
		// Direct native committed-source seam remains recoverable even when a
		// caller outside Sender dies before status-triggered notification hooks.
		$record = new WC_Order();
		$record->set_billing_email( $details->email );
		$record->set_billing_first_name( $details->name );
		$record->set_customer_note( $details->message );
		$record->update_meta_data( '_linker_inquiry_source', 'contact' );
		\Linker\Commerce\Inquiry\Assessment\Queue::prepare( $record, array() );
		$record->save();
		WC()->mailer();
		$this->later(
			static function () use ( $record ): void {
				$record->delete( true );
			}
		);
		$marker = self::newest_mail_job();
		$fail   = static function (): void {
			throw new \Error( 'synthetic_failure_before_notification' );
		};
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $fail, 1 );
		$caught = false;
		try {
			$record->update_status( Statuses::RECEIVED );
		} catch ( \Error $error ) {
			$caught = 'synthetic_failure_before_notification' === $error->getMessage();
		} finally {
			remove_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $fail, 1 );
		}
		self::assertTrue( $caught );
		$orders = wc_get_orders(
			array(
				'billing_email' => $details->email,
				'limit'         => -1,
			)
		);
		self::assertIsArray( $orders );
		$orders = array_values( array_filter( $orders, static fn ( WC_Order $candidate ): bool => $record->get_id() === $candidate->get_id() ) );
		self::assertCount( 1, $orders );
		$order = $orders[0];
		$data  = \Linker\Commerce\Inquiry\Assessment\Queue::data( $order );
		self::assertSame( Statuses::RECEIVED, $order->get_status() );
		self::assertArrayNotHasKey( 'notification_only', $data );
		self::assertSame( 'yes', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Queue::PENDING ) );
		self::assertSame( 0, $data['notification_job'] );
		self::assertSame( $marker, self::newest_mail_job() );
		$normal = $this->normal();
		$queue  = new \Linker\Commerce\Inquiry\Assessment\Queue();
		$queue->expire( $order->get_id() );
		$state = $normal->process( $order );
		self::assertSame( 'normal', $state['verdict']['decision'] );
		self::assertCount( 2, $state['jobs'] );
		$jobs = $state['jobs'];
		$queue->expire( $order->get_id() );
		$repeat = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $repeat );
		self::assertSame( $jobs, $repeat['jobs'] );
		self::assertCount( 1, $normal->requests );
	}

	/** The old display switch cannot disable the mandatory final send permission. */
	public function test_legacy_display_switch_cannot_bypass_classification_or_strip_complete_normal_content(): void {
		$this->seed_business( 0 );
		$normal = $this->normal();
		update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, 'no' );
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$state = $normal->process( $order );
		self::assertSame( 'normal', $state['verdict']['decision'] );
		$stored = ( new JobStore() )->load( $state['jobs']['team']['id'] );
		self::assertNotNull( $stored );
		self::assertStringContainsString( $this->details()->message, $stored['message']->body );
		self::assertTrue( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::allows( $stored['message'], $state['jobs']['team']['id'] ) );
		self::assertCount( 1, $normal->requests, 'The legacy display switch does not bypass mandatory classification.' );
		$attempts = 0;
		$observe  = static function () use ( &$attempts ): void {
			++$attempts;
		};
		add_action( 'phpmailer_init', $observe, PHP_INT_MAX );
		try {
			foreach ( $state['jobs'] as $entry ) {
				do_action( Outbox::HOOK, $entry['id'] ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer.
				self::assertNull( ( new JobStore() )->load( $entry['id'] ) ); }
		} finally {
			remove_action( 'phpmailer_init', $observe, PHP_INT_MAX ); }
		self::assertSame( 2, $attempts );
	}

	/** An unresolved or malicious content verdict creates no team job or additional mail charge.
	 *
	 * @dataProvider withheld_decisions
	 * @param string $decision Typed classifier decision.
	 * @param string $basis Typed evidence basis.
	 * @param string $reason Wire diagnostic.
	 */
	public function test_withheld_team_mail_preserves_complete_woo_inquiry( string $decision, string $basis, string $reason ): void {
		$this->seed_business( 0 );
		$normal   = $this->normal();
		$provider = static function ( $pre, $args, $url ) use ( $decision, $basis, $reason ) {
			if ( 'http://127.0.0.1:9/inquiries/assess' !== $url ) {
				return $pre; }
			$request = json_decode( $args['body'], true );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode( \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::verdict( $request['binding'], $decision, $basis, $reason ) ),
			);
		};
		add_filter( 'pre_http_request', $provider, 10, 3 );
		$this->later(
			static function () use ( $provider ): void {
				remove_filter( 'pre_http_request', $provider, 10 );
			}
		);
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$budget   = get_option( OptionBudgetLedger::OPTION );
		$receipts = get_option( Ledger::OPTION );
		$marker   = self::newest_mail_job();
		\Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::consume( \Linker\Commerce\Inquiry\Assessment\Queue::PROCESS, $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( $decision, $state['verdict']['decision'] );
		self::assertSame( 'malicious' === $decision ? 'quarantined' : 'normal', $state['status'] );
		self::assertArrayNotHasKey( 'receipt', $state['jobs'] );
		self::assertSame( 'malicious' === $decision ? array() : array( $state['jobs']['team']['id'] ), self::mail_jobs_after( $marker ) );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertSame( $receipts, get_option( Ledger::OPTION ) );
		$fresh = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $fresh );
		self::assertSame( $this->details()->message, $fresh->get_customer_note() );
		self::assertCount( 1, $normal->requests );
	}

	/** Typed service outcomes that do not confer any sending permission.
	 *
	 * @return array<string,array{string,string,string}>
	 */
	public static function withheld_decisions(): array {
		return array(
			'unknown'   => array( 'unknown', 'insufficient_context', 'insufficient_confidence' ),
			'malicious' => array( 'malicious', 'fraud_or_phishing', 'classified' ),
		);
	}

	/** Install only the real wire boundary; final grants and native writers remain active. */
	private function normal(): \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture {
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		return \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
	}

	/** Both legacy label-display settings retain mandatory classification and recovery.
	 *
	 * @return array<string,array{bool}>
	 */
	public static function notification_modes(): array {
		return array(
			'classification'     => array( true ),
			'legacy-display-off' => array( false ),
		);
	}

	/** A saved scope from before the native Woo cutover.
	 *
	 * @param int $count Existing synthetic entries.
	 */
	private function seed_business( int $count ): void {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $count ): array {
				$state['business'] = array();
				for ( $i = 0; $i < $count; ++$i ) {
					$state['business'][ 'synthetic-' . $i ] = array(
						'pool'  => 'ordinary',
						'order' => 0,
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
		self::assertIsArray( $result );
	}

	/** Native validated synthetic inquiry details. */
	private function details(): Submission {
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic capacity tester',
				'email'   => $this->recipient,
				'company' => 'Synthetic Solar GmbH',
				'message' => 'Please advise on equipment for this project.',
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		return $details;
	}
}

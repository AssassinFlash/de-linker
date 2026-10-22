<?php
/**
 * Public identity rotation and the native notification writer (#568).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Private fixture configuration is restored, never production.

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Protection\BusinessPolicy;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Protection\BusinessCapacity;
use Linker\Commerce\Protection\TrustedCustomer;
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
 * The original exploit used successful verification, not a forged nonce.
 *
 * @coversNothing
 */
final class GlobalBusinessCapacityTest extends IntegrationTestCase {
	/** Preserve the local snapshot's pre-existing jobs and capacity ledger. */
	protected function setUp(): void {
		parent::setUp();
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
	}

	/** Changing all cheap identities and the business door does not renew site use. */
	public function test_rotating_public_subjects_cannot_reset_the_site_business_allowance(): void {
		$previous = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$this->later(
			static function () use ( $previous ): void {
				delete_option( Ledger::OPTION );
				if ( false !== $previous ) {
					update_option( Ledger::OPTION, $previous, false );
				}
			}
		);
		$this->as_user( 0 );
		$policy  = new BusinessPolicy();
		$ledger  = new Ledger( static fn (): int => 1792663200 );
		$actions = array( 'contact', 'inquiry', 'genie_contact', 'genie_inquiry', 'conversation_mail' );
		for ( $i = 0; $i < 17; ++$i ) {
			$_SERVER['REMOTE_ADDR'] = '192.0.2.' . ( $i + 1 );
			$identity               = new Identity( hash( 'sha256', 'public-browser-' . $i ), '' );
			$id                     = wp_generate_uuid4();
			$input                  = hash( 'sha256', 'different-domain-and-message-' . $i );
			$permit                 = $ledger->reserve( $id, $input, $policy->limits( array(), $actions[ $i % 5 ], $identity ), 60 );
			if ( $i < 16 ) {
				self::assertIsArray( $permit );
				self::assertIsArray( $ledger->dispatch( $id, $input ) );
				self::assertIsArray( $ledger->complete( $id, $input ) );
			} else {
				self::assertInstanceOf( WP_Error::class, $permit );
				self::assertSame( 'linker_admission_quota', $permit->get_error_code() );
			}
		}
	}


	/** Only a real staff approval of a plain customer grants the independent pool. */
	public function test_reserved_customer_pool_requires_native_staff_approval(): void {
		$this->as_user( 0 );
		self::assertFalse( TrustedCustomer::current() );
		$customer = $this->customer();
		$id       = $customer->get_id();
		$this->as_user( $id );
		self::assertFalse( TrustedCustomer::current(), 'Status alone lacks employee provenance.' );
		update_user_meta( $id, Approval::CHANGED_BY_META, $id );
		update_user_meta( $id, Approval::CHANGED_AT_META, time() );
		self::assertFalse( TrustedCustomer::current(), 'Self-asserted approval is not staff provenance.' );
		update_user_meta( $id, Approval::STATUS_META, Approval::PENDING );
		$this->set_state( $customer, Approval::APPROVED );
		$this->as_user( $id );
		self::assertTrue( TrustedCustomer::current() );
		$user = get_userdata( $id );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'subscriber' );
		wp_set_current_user( 0 );
		wp_set_current_user( $id );
		self::assertFalse( TrustedCustomer::current(), 'Approval defaults for non-customers never grant the reserve.' );
	}

	/** Ordinary exhaustion cannot consume the genuinely staff-approved reserve. */
	public function test_ordinary_persistent_full_preserves_the_independent_staff_approved_pool(): void {
		$this->enforce();
		$this->seed_business( 128 );
		$customer = $this->customer();
		$this->set_state( $customer, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		self::assertInstanceOf( WP_Error::class, ( new Sender() )->message( $this->details() ) );
		$this->set_state( $customer, Approval::APPROVED );
		$this->as_user( $customer->get_id() );
		self::assertTrue( TrustedCustomer::current() );
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$state = get_option( IntakeStore::OPTION );
		self::assertSame( 'approved', $state['business'][ $order->get_meta( BusinessCapacity::KEY ) ]['pool'] );
		self::assertCount( 128, array_filter( $state['business'], static fn ( array $entry ): bool => 'ordinary' === $entry['pool'] ) );
		self::assertCount( 1, array_filter( $state['business'], static fn ( array $entry ): bool => 'approved' === $entry['pool'] ) );
	}

	/** The last writer preserves a large complete payload; the next write is unsaved. */
	public function test_first_save_count_boundary_retains_complete_large_inquiry_and_staff_only_release(): void {
		$this->enforce();
		$this->seed_business( 127 );
		$this->as_user( 0 );
		// HPOS meta_value is native TEXT. Each legal field stays below its
		// 65535-byte storage limit while the complete inquiry exceeds 256 KiB.
		$payload = str_repeat( 'Full product and document context. ', 1600 );
		$meta    = array_fill_keys( array( '_context_a', '_context_b', '_context_c', '_context_d', '_context_e', '_context_f' ), $payload );
		$order   = ( new Sender() )->message( $this->details(), $meta );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$fresh = wc_get_order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $fresh );
		$fresh->read_meta_data( true );
		foreach ( $meta as $field => $value ) {
			self::assertSame( hash( 'sha256', $value ), hash( 'sha256', (string) $fresh->get_meta( $field ) ), 'Complete legal native field is retained.' );
		}
		self::assertGreaterThan( 262144, BusinessCapacity::bytes( $order ), '256 KiB is no per-inquiry cut-off.' );
		$key   = (string) $order->get_meta( BusinessCapacity::KEY );
		$state = get_option( IntakeStore::OPTION );
		self::assertCount( 128, $state['business'] );
		$marker = self::newest_mail_job();
		$next   = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WP_Error::class, $next );
		self::assertSame( 'linker_business_capacity', $next->get_error_code() );
		self::assertSame( $marker, self::newest_mail_job(), 'No new notification is created on full reception.' );
		$order->update_status( 'cancelled' );
		self::assertArrayHasKey( $key, get_option( IntakeStore::OPTION )['business'], 'Anonymous/native cancellation does not attest staff handling.' );
		$this->as_user( 1 );
		$order->update_status( Statuses::RECEIVED );
		$order->update_status( Statuses::PROFORMA );
		self::assertArrayNotHasKey( $key, get_option( IntakeStore::OPTION )['business'], 'Staff Proforma handoff releases unhandled occupancy.' );
		$fresh->read_meta_data( true );
		self::assertSame( $payload, $fresh->get_meta( '_context_a' ), 'Disposition never deletes the original inquiry.' );
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

	/** Pool bytes are checked at the actual writer before any native row is added. */
	public function test_persistent_byte_exhaustion_is_unsaved_even_with_free_count_slots(): void {
		$this->enforce();
		$this->seed_business( 0 );
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['business']['synthetic-byte-debt'] = array(
					'pool'  => 'ordinary',
					'order' => 0,
					'bytes' => BusinessCapacity::LIMITS['ordinary']['bytes'] - 1,
				);
				IntakeStore::save( $state );
				return array();
			}
		);
		$before = wc_get_orders( array( 'limit' => -1 ) );
		self::assertIsArray( $before );
		$jobs = self::newest_mail_job();
		$sent = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WP_Error::class, $sent );
		self::assertSame( 'linker_business_capacity', $sent->get_error_code() );
		$after = wc_get_orders( array( 'limit' => -1 ) );
		self::assertIsArray( $after );
		self::assertSameSize( $before, $after );
		self::assertSame( $jobs, self::newest_mail_job() );
	}

	/** Saved team notices survive a full queue, recover once and spend no model.
	 *
	 * @dataProvider notification_modes
	 * @param bool $assessment Whether native classification is enabled.
	 */
	public function test_saved_inquiry_stays_durably_pending_when_queue_is_full_then_recovers_one_original_job( bool $assessment ): void {
		$this->enforce();
		$this->seed_business( 0 );
		$enabled = get_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED );
		update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, $assessment ? 'yes' : 'no' );
		$this->later(
			static function () use ( $enabled ): void {
				false === $enabled ? delete_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED ) : update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, $enabled, false );
			}
		);
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 1; $i <= 191; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
		$space = ( new JobStore() )->create( new Message( array( self::TESTER ), 'Synthetic occupied final slot', 'No transport.', array(), array() ) );
		self::assertGreaterThan( 0, $space );
		$http = 0;
		$spy  = static function ( $pre ) use ( &$http ) {
			++$http;
			return $pre;
		};
		add_filter( 'pre_http_request', $spy );
		$this->later(
			static function () use ( $spy ): void {
				remove_filter( 'pre_http_request', $spy );
			}
		);
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				foreach ( array( \Linker\Commerce\Inquiry\Assessment\Queue::PROCESS, \Linker\Commerce\Inquiry\Assessment\Queue::EXPIRE ) as $hook ) {
					as_unschedule_all_actions( $hook, array( $order->get_id() ), Outbox::GROUP );
				}
				$order->delete( true );
			}
		);
		$queue            = new \Linker\Commerce\Inquiry\Assessment\Queue();
		$data             = \Linker\Commerce\Inquiry\Assessment\Queue::data( $order );
		$data['deadline'] = microtime( true ) - 1;
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, \Linker\Commerce\Inquiry\Assessment\Queue::META, $data );
		$order->save_meta_data();
		$queue->finish( $order->get_id(), \Linker\Commerce\Inquiry\Assessment\Result::unknown( 'deadline' ) );
		$order->read_meta_data( true );
		self::assertSame( 'yes', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Queue::PENDING ) );
		self::assertSame( 0, \Linker\Commerce\Inquiry\Assessment\Queue::data( $order )['notification_job'] );
		self::assertSame( 'queue_unavailable', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ), 'No successful receipt is fabricated.' );
		( new JobStore() )->delete( $space );
		delete_option( OptionBudgetLedger::OPTION );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_DAY, time() ), false );
		$before = self::newest_mail_job();
		$queue->expire( $order->get_id() );
		$order->read_meta_data( true );
		$job = (int) \Linker\Commerce\Inquiry\Assessment\Queue::data( $order )['notification_job'];
		self::assertGreaterThan( $before, $job );
		$queue->expire( $order->get_id() );
		$order->read_meta_data( true );
		self::assertSame( $job, \Linker\Commerce\Inquiry\Assessment\Queue::data( $order )['notification_job'] );
		self::assertSame( $job, self::newest_mail_job(), 'Repeated recovery never creates a shadow notification.' );
		self::assertSame( 0, $http, 'Neither full-queue recovery path calls a model or a website.' );
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
		$this->enforce();
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
		$table  = $wpdb->prefix . 'wc_orders';
		$killed = false;
		$native = 0;
		$before = self::newest_mail_job();
		$kill   = static function ( string $sql ) use ( $partial, $table, $details, $other, &$killed, &$native ): string {
			global $wpdb;
			$target = $partial ? str_contains( $sql, '_linker_inquiry_source' ) : str_contains( str_replace( '`', '', $sql ), $table . ' (' );
			if ( ! $killed && str_starts_with( ltrim( $sql ), 'INSERT' ) && $target ) {
				$killed = true;
				$native = (int) $wpdb->get_var( $wpdb->prepare( 'SELECT id FROM %i WHERE billing_email=%s', $table, $details->email ) );
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
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE billing_email=%s', $table, $details->email ) ) );
		if ( $partial ) {
			self::assertGreaterThan( 0, $native );
			self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE order_id=%d', $wpdb->prefix . 'wc_orders_meta', $native ) ) );
		}
		self::assertTrue( $wpdb->db_connect( false ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( $draft, WC()->cart->get_cart() );
		self::assertSame( 'Keep this full native request.', $details->message );
		$other->close();
	}

	/** Sender's native phase rolls back an exception before notifications and keeps the draft. */
	public function test_sender_native_failure_does_not_leave_a_partially_received_record(): void {
		$this->enforce();
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
	public function test_notification_only_first_save_recovers_after_failure_before_native_notification_callback(): void {
		$this->enforce();
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
		\Linker\Commerce\Inquiry\Assessment\Queue::prepare( $record, array(), true );
		BusinessCapacity::prepare( $record );
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
		$orders = array_values( array_filter( $orders, static fn ( WC_Order $record ): bool => (bool) $record->get_meta( BusinessCapacity::KEY ) ) );
		self::assertCount( 1, $orders );
		$order = $orders[0];
		$data  = \Linker\Commerce\Inquiry\Assessment\Queue::data( $order );
		self::assertSame( Statuses::RECEIVED, $order->get_status() );
		self::assertTrue( $data['notification_only'] );
		self::assertSame( 'yes', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Queue::PENDING ) );
		self::assertSame( 0, $data['notification_job'] );
		self::assertSame( $marker, self::newest_mail_job() );
		$data['deadline'] = microtime( true ) - 1;
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, \Linker\Commerce\Inquiry\Assessment\Queue::META, $data );
		$order->save_meta_data();
		$http = 0;
		$spy  = static function ( $pre ) use ( &$http ) {
			++$http;
			return $pre;
		};
		add_filter( 'pre_http_request', $spy );
		try {
			$queue = new \Linker\Commerce\Inquiry\Assessment\Queue();
			$queue->expire( $order->get_id() );
			$order->read_meta_data( true );
			$job = (int) \Linker\Commerce\Inquiry\Assessment\Queue::data( $order )['notification_job'];
			self::assertGreaterThan( $marker, $job );
			$queue->expire( $order->get_id() );
			self::assertSame( $job, self::newest_mail_job() );
			self::assertSame( 0, $http );
		} finally {
			remove_filter( 'pre_http_request', $spy );
		}
	}

	/** The disabled team's complete existing native email body is unchanged. */
	public function test_notification_only_recovery_metadata_does_not_add_a_jev_block_to_the_original_body(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$before = get_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED );
		update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, 'no' );
		$this->later(
			static function () use ( $before ): void {
				false === $before ? delete_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED ) : update_option( \Linker\Commerce\Inquiry\Assessment\Queue::ENABLED, $before, false );
			}
		);
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class ];
		self::assertInstanceOf( \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class, $email );
		$actual = $email->capture( $order );
		$data   = \Linker\Commerce\Inquiry\Assessment\Queue::data( $order );
		$order->delete_meta_data( \Linker\Commerce\Inquiry\Assessment\Queue::META );
		$order->save_meta_data();
		$original = $email->capture( $order );
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, \Linker\Commerce\Inquiry\Assessment\Queue::META, $data );
		$order->save_meta_data();
		self::assertNotNull( $actual );
		self::assertNotNull( $original );
		self::assertSame( $original->to_array(), $actual->to_array() );
	}

	/** Independent native writers cannot duplicate the last count or logical-byte slot. */
	public function test_two_business_connections_share_the_last_complete_record_slot(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$off = static fn (): string => 'no';
		add_filter( 'pre_option_linker_inquiry_assessment_enabled', $off );
		add_filter( 'woocommerce_email_enabled_linker_new_inquiry', '__return_false' );
		add_filter( 'woocommerce_email_enabled_linker_inquiry_received', '__return_false' );
		$this->later(
			static function () use ( $off ): void {
				remove_filter( 'pre_option_linker_inquiry_assessment_enabled', $off );
				remove_filter( 'woocommerce_email_enabled_linker_new_inquiry', '__return_false' );
				remove_filter( 'woocommerce_email_enabled_linker_inquiry_received', '__return_false' );
			}
		);
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic business writer',
				'email'   => 'capacity-writer-z@example.test',
				'message' => str_repeat( 'x', 3000 ),
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		$calibration = ( new Sender() )->message( $details );
		self::assertInstanceOf( WC_Order::class, $calibration );
		$bytes = get_option( IntakeStore::OPTION )['business'][ $calibration->get_meta( BusinessCapacity::KEY ) ]['bytes'];
		self::assertGreaterThan( 256, $bytes );
		$calibration->delete( true );
		foreach ( array( 'count', 'bytes' ) as $boundary ) {
			$this->seed_business( 'count' === $boundary ? 127 : 0 );
			if ( 'bytes' === $boundary ) {
				IntakeStore::edit(
					static function ( array &$state ) use ( $bytes ): array {
						$state['business']['synthetic-byte-debt'] = array(
							'pool'  => 'ordinary',
							'order' => 0,
							'bytes' => BusinessCapacity::LIMITS['ordinary']['bytes'] - $bytes - 256,
						);
						IntakeStore::save( $state );
						return array();
					}
				);
			}
			$directory = sys_get_temp_dir() . '/linker-business-568-' . self::tag();
			mkdir( $directory, 0700 );
			$this->later(
				static function () use ( $directory ): void {
					$files = glob( $directory . '/*' );
					foreach ( false === $files ? array() : $files as $file ) {
						unlink( $file );
					}
					rmdir( $directory );
				}
			);
			$workers = array();
			foreach ( array( 'a', 'b' ) as $worker ) {
				$pipes = array();
				// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Test-owned independent native writers; native email consumers explicitly disabled.
				$process = proc_open(
					array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/business_capacity_writer.php', untrailingslashit( ABSPATH ), $directory . '/' . $worker, $directory . '/go', 'capacity-writer-' . $worker . '@example.test' ),
					array(
						0 => array( 'pipe', 'r' ),
						1 => array( 'file', $directory . '/log', 'a' ),
						2 => array( 'file', $directory . '/log', 'a' ),
					),
					$pipes
				);
				self::assertIsResource( $process );
				fclose( $pipes[0] );
				$workers[] = $process;
			}
			$deadline = microtime( true ) + 15;
			while ( ( ! is_file( $directory . '/a.ready' ) || ! is_file( $directory . '/b.ready' ) ) && microtime( true ) < $deadline ) {
				usleep( 1000 );
			}
			self::assertFileExists( $directory . '/a.ready' );
			self::assertFileExists( $directory . '/b.ready' );
			file_put_contents( $directory . '/go', 'go' );
			foreach ( $workers as $process ) {
				self::assertSame( 0, proc_close( $process ) );
			}
			$accepted = 0;
			foreach ( array( 'a', 'b' ) as $worker ) {
				$data = json_decode( (string) file_get_contents( $directory . '/' . $worker ), true );
				self::assertIsArray( $data );
				self::assertLessThan( 2, $data['seconds'], 'A bounded short edit does not serialize whole submissions.' );
				if ( $data['order'] > 0 ) {
					++$accepted;
					$id = $data['order'];
					$this->later(
						static function () use ( $id ): void {
							$order = wc_get_order( $id );
							if ( $order instanceof WC_Order ) {
								$order->delete( true );
							} }
					);
				} else {
					self::assertSame( 'linker_business_capacity', $data['error'] );
				}
			}
			self::assertSame( 1, $accepted, $boundary . ' permits exactly one complete actual native write.' );
			wp_cache_delete( IntakeStore::OPTION, 'options' );
		}
	}

	/** Classification is optional; durable team recovery is not.
	 *
	 * @return array<string,array{bool}>
	 */
	public static function notification_modes(): array {
		return array(
			'classification'    => array( true ),
			'notification-only' => array( false ),
		);
	}

	/** Native fixture settings; no public-proof requirement is bypassed by a live request. */
	private function enforce(): void {
		$mode = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Restored local fixture configuration.
		$this->later(
			static function () use ( $mode ): void {
				putenv( false === $mode ? 'LINKER_PUBLIC_PROTECTION_MODE' : 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			}
		); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv
	}

	/** Synthetic existing occupancy leaves a single real writer slot.
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
				'email'   => self::TESTER,
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

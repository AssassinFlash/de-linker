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
		self::assertSame( array( 'team', 'receipt' ), array_keys( $state['jobs'] ) );
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
	public function test_first_save_without_status_callback_recovers_only_after_current_normal_permission(): void {
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
		\Linker\Commerce\Inquiry\Assessment\Queue::prepare( $record, array() );
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
		$this->enforce();
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

	/** Unknown and malicious classification retain saved debt without mail or receipt spend.
	 *
	 * @dataProvider withheld_decisions
	 * @param string $decision Typed classifier decision.
	 * @param string $basis Typed evidence basis.
	 * @param string $reason Wire diagnostic.
	 */
	public function test_withheld_mail_keeps_complete_business_capacity_without_spending_mail_allowances( string $decision, string $basis, string $reason ): void {
		$this->enforce();
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
		$before   = get_option( IntakeStore::OPTION )['business'];
		$budget   = get_option( OptionBudgetLedger::OPTION );
		$receipts = get_option( Ledger::OPTION );
		$marker   = self::newest_mail_job();
		\Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::consume( \Linker\Commerce\Inquiry\Assessment\Queue::PROCESS, $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( $decision, $state['verdict']['decision'] );
		self::assertSame( 'malicious' === $decision ? 'quarantined' : 'pending', $state['status'] );
		self::assertEmpty( $state['jobs'] ?? array() );
		self::assertSame( $marker, self::newest_mail_job() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertSame( $receipts, get_option( Ledger::OPTION ) );
		self::assertSame( $before, get_option( IntakeStore::OPTION )['business'] );
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

	/** A peer decision change cannot reuse this request's cached approved identity. */
	public function test_peer_approval_revocation_cannot_acquire_the_reserved_pool(): void {
		$this->enforce();
		$this->seed_business( 128 );
		$customer = $this->customer();
		$this->set_state( $customer, Approval::PENDING );
		$this->set_state( $customer, Approval::APPROVED );
		$this->as_user( $customer->get_id() );
		self::assertTrue( TrustedCustomer::current() );
		global $wpdb;
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		try {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Independent native metadata writer, deliberately preserving this request's primed caches.
			self::assertSame(
				1,
				$peer->update(
					$wpdb->usermeta,
					array( 'meta_value' => Approval::RESTRICTED ), // phpcs:ignore WordPress.DB.SlowDBQuery -- Exact synthetic user row on a separate fixture-owned connection.
					array(
						'user_id'  => $customer->get_id(),
						'meta_key' => Approval::STATUS_META, // phpcs:ignore WordPress.DB.SlowDBQuery -- Exact synthetic user row on a separate fixture-owned connection.
					)
				)
			);
			self::assertFalse( TrustedCustomer::current() );
			$before = $this->native_order_count();
			self::assertInstanceOf( WP_Error::class, ( new Sender() )->message( $this->details() ) );
			self::assertSame( $before, $this->native_order_count() );
		} finally {
			$peer->close(); }
	}

	/** A cached status callback is not proof that a peer left the source processed. */
	public function test_stale_processed_status_callback_does_not_refund_received_source(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$this->as_user( 1 );
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$key = $order->get_meta( BusinessCapacity::KEY );
		$order->set_status( Statuses::PROFORMA );
		( new BusinessCapacity() )->status( $order->get_id(), Statuses::RECEIVED, Statuses::PROFORMA, $order );
		self::assertArrayHasKey( $key, get_option( IntakeStore::OPTION )['business'] );
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

	/** Business row-lock recovery cannot extend its initial one-second budget. */
	public function test_uncommitted_outer_owner_keeps_business_retry_within_one_second(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$directory = sys_get_temp_dir() . '/linker-business-budget-' . self::tag();
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
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Test-owned independent native writer; native email consumers are disabled inside the fixture.
		$process = proc_open(
			array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/business_capacity_writer.php', untrailingslashit( ABSPATH ), $directory . '/worker', $directory . '/go', 'capacity-budget@example.test' ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'file', $directory . '/log', 'a' ),
				2 => array( 'file', $directory . '/log', 'a' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		$ready_deadline = microtime( true ) + 15;
		while ( ! is_file( $directory . '/worker.ready' ) && microtime( true ) < $ready_deadline ) {
			usleep( 1000 );
		}
		self::assertFileExists( $directory . '/worker.ready' );
		$finished = false;
		try {
			wc_transaction_query( 'start' );
			$held = IntakeStore::edit(
				static function ( array &$state ): array {
					$state['campaign_count'] = (int) ( $state['campaign_count'] ?? 0 ) + 1;
					IntakeStore::save( $state );
					return array();
				},
				1
			);
			self::assertIsArray( $held );
			file_put_contents( $directory . '/go', 'go' );
			$deadline = microtime( true ) + 2;
			while ( ! is_file( $directory . '/worker' ) && microtime( true ) < $deadline ) {
				usleep( 1000 );
			}
			$finished = is_file( $directory . '/worker' );
		} finally {
			wc_transaction_query( 'rollback' );
		}
		self::assertSame( 0, proc_close( $process ) );
		self::assertTrue( $finished, 'The competing request returns while the outer transaction remains open.' );
		$result = json_decode( (string) file_get_contents( $directory . '/worker' ), true );
		self::assertIsArray( $result );
		self::assertSame( 'linker_intake_pending', $result['error'] );
		self::assertLessThan( 1.2, $result['seconds'], 'Row-lock recovery does not extend the first one-second budget.' );
		wp_cache_delete( IntakeStore::OPTION, 'options' );
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

	/** Complete native association and the exact remaining logical byte use one serializer. */
	public function test_first_save_counts_complete_native_association_and_exact_last_byte(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$context = static fn (): array => array(
			'enforced'    => true,
			'id'          => wp_generate_uuid4(),
			'fingerprint' => str_repeat( 'a', 64 ),
			'binding'     => str_repeat( 'b', 64 ),
		);
		// One stable dispatched native context per actual writer, not browser input.
		$current = $context();
		$filter  = static fn () => $current;
		add_filter( 'linker_commerce_public_business_context', $filter );
		$this->later(
			static function () use ( $filter ): void {
				remove_filter( 'linker_commerce_public_business_context', $filter );
			}
		);
		$observed = 0;
		$reserved = 0;
		$prepared = null;
		$watch    = static function ( WC_Order $order ) use ( &$observed, &$reserved, &$prepared ): void {
			if ( 0 === $order->get_id() && $order->get_meta( BusinessCapacity::KEY ) ) {
				$observed = BusinessCapacity::bytes( $order );
				$reserved = get_option( IntakeStore::OPTION )['business'][ $order->get_meta( BusinessCapacity::KEY ) ]['bytes'];
				self::assertNotEmpty( $order->get_meta( \Linker\Commerce\Protection\BusinessRecord::REQUEST ) );
				$prepared = clone $order;
				$prepared->init_meta_data(
					array_map(
						static fn ( \WC_Meta_Data $meta ): object => (object) array(
							'meta_id'    => $meta->id,
							'meta_key'   => $meta->key, // phpcs:ignore WordPress.DB.SlowDBQuery -- Native in-memory WC metadata shape, no query.
							'meta_value' => $meta->value, // phpcs:ignore WordPress.DB.SlowDBQuery -- Native in-memory WC metadata shape, no query.
						),
						$order->get_meta_data()
					)
				);
			}
		};
		add_action( 'woocommerce_before_order_object_save', $watch, 100 );
		$this->later(
			static function () use ( $watch ): void {
				remove_action( 'woocommerce_before_order_object_save', $watch, 100 );
			}
		);
		$order = ( new Sender() )->message( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		self::assertSame( $observed, $reserved, 'Actual first-save serializer includes all three dispatched association metadata values.' );
		$order->delete( true );
		remove_action( 'woocommerce_before_order_object_save', $watch, 100 );
		foreach ( array( -1, 0 ) as $slack ) {
			$this->seed_business( 0 );
			IntakeStore::edit(
				static function ( array &$state ) use ( $observed, $slack ): array {
					$state['business']['synthetic-exact-byte-debt'] = array(
						'pool'  => 'ordinary',
						'order' => 0,
						'bytes' => BusinessCapacity::LIMITS['ordinary']['bytes'] - $observed - $slack,
					);
					IntakeStore::save( $state );
					return array();
				}
			);
			$before = $this->native_order_count();
			self::assertInstanceOf( WC_Order::class, $prepared );
			$next = clone $prepared;
			$next->init_meta_data(
				array_map(
					static fn ( \WC_Meta_Data $meta ): object => (object) array(
						'meta_id'    => $meta->id,
						'meta_key'   => $meta->key, // phpcs:ignore WordPress.DB.SlowDBQuery -- Native in-memory WC metadata shape, no query.
						'meta_value' => $meta->value, // phpcs:ignore WordPress.DB.SlowDBQuery -- Native in-memory WC metadata shape, no query.
					),
					$prepared->get_meta_data()
				)
			);
			$next->delete_meta_data( BusinessCapacity::KEY );
			try {
				BusinessCapacity::prepare( $next );
				\Linker\Commerce\Mail\NativeTransaction::run(
					static function () use ( $next ): void {
						$next->save();
						self::assertNull( BusinessCapacity::verify( $next ) );
					}
				);
			} catch ( \Linker\Commerce\Protection\CapacityFull $error ) {
				$next = $error->problem; }
			if ( -1 === $slack ) {
				self::assertInstanceOf( WP_Error::class, $next, 'One missing byte refuses before any native record.' );
				self::assertSame( $before, $this->native_order_count() );
			} else {
				self::assertInstanceOf( WC_Order::class, $next, 'Exact complete logical byte envelope is accepted.' );
				$this->later(
					static function () use ( $next ): void {
						$next->delete( true );
					}
				);
				self::assertSame( BusinessCapacity::LIMITS['ordinary']['bytes'], array_sum( array_column( get_option( IntakeStore::OPTION )['business'], 'bytes' ) ) );
			}
		}
	}

	/** A one-shot native binding mutex failure must not publish an unbound received record. */
	public function test_failed_first_save_binding_is_not_accepted_or_left_as_a_received_source(): void {
		$this->enforce();
		$this->seed_business( 0 );
		$before = $this->native_order_count();
		$fault  = false;
		$armed  = false;
		$arm    = static function () use ( &$armed ): void {
			$armed = true;
		};
		$fail   = static function ( string $sql ) use ( &$armed, &$fault ): string {
			if ( $armed && ! $fault && str_contains( $sql, 'GET_LOCK(' ) ) {
				$fault = true;
				return 'SELECT 0'; }
			return $sql;
		};
		add_action( 'woocommerce_new_order', $arm, 29 );
		add_filter( 'query', $fail, 998 );
		try {
			$result = ( new Sender() )->message( $this->details() ); } finally {
			remove_action( 'woocommerce_new_order', $arm, 29 );
			remove_filter( 'query', $fail, 998 ); }
			if ( $result instanceof WC_Order ) {
				$this->later(
					static function () use ( $result ): void {
						$result->delete( true );
					}
				); }
			self::assertTrue( $fault );
			self::assertInstanceOf( WP_Error::class, $result, 'A failed final native bind cannot be announced as received.' );
			self::assertSame( $before, $this->native_order_count(), 'Known failure rolls back the actual native first-save transaction.' );
	}

	/** Actual native row count, not Woo's optional paginated result wrapper. */
	private function native_order_count(): int {
		$orders = wc_get_orders(
			array(
				'limit'  => -1,
				'return' => 'ids',
			)
		);
		self::assertIsArray( $orders );
		return count( $orders );
	}

	/** Native fixture settings restored after each test. */
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

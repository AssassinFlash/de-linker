<?php
/**
 * Native callbacks preserve held inquiry notifications without delivery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Throttle;
use WC_Order;

/**
 * Public native retry and lifecycle seams; no model or remote mail is used.
 *
 * @coversNothing
 */
final class NotificationHoldTest extends IntegrationTestCase {
	/** Manual callbacks must honor the incident hold already stored in production. */
	public function test_manual_retry_of_existing_held_job_spends_no_mail_budget(): void {
		[ $order, $id ] = $this->held_inquiry();
		$jobs           = new JobStore();
		$before         = $jobs->load( $id );
		$this->assertNotNull( $before );
		$budget = get_option( Throttle::OPTION, array() );
		( new Outbox( $jobs, new Throttle() ) )->retry( $id );
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$after = $jobs->load( $id );
		$this->assertNotNull( $after );
		$this->assertSame( $before['message']->to_array(), $after['message']->to_array() );
		$this->assertSame( 0, $after['attempts'] );
		$this->assertSame( 'private', get_post_status( $id ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** Stale callbacks cannot rewrite evidence, spend a model budget or recreate a job. */
	public function test_all_stale_assessment_callbacks_leave_held_inquiry_unchanged(): void {
		[ $order, $id ] = $this->held_inquiry();
		$before         = Queue::data( $order );
		$jobs           = self::mail_jobs_after( 0 );
		$budget         = get_option( Throttle::OPTION, array() );
		$requests       = 0;
		$fetch          = static function ( $pre ) use ( &$requests ) {
			++$requests;
			return $pre;
		};
		add_filter( 'pre_http_request', $fetch );
		try {
			$queue = new Queue();
			$queue->process( $order->get_id() );
			$queue->finish( $order->get_id(), Result::unknown( 'late' ) );
			$queue->expire( $order->get_id() );
			$queue->recover();
		} finally {
			remove_filter( 'pre_http_request', $fetch ); }
		$order->read_meta_data( true );
		$this->assertSame( $before, Queue::data( $order ) );
		$this->assertSame( 'held', $order->get_meta( Queue::PENDING ) );
		$this->assertSame( 0, $requests );
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$this->assertSame( $jobs, self::mail_jobs_after( 0 ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** A repeated staff release keeps one original message and respects the real cap. */
	public function test_staff_release_is_idempotent_and_uses_original_job_with_throttle(): void {
		[ $order, $id ] = $this->held_inquiry();
		$staff          = $this->customer();
		$user           = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$jobs     = new JobStore();
		$original = $jobs->load( $id );
		$this->assertNotNull( $original );
		$evidence  = Queue::data( $order );
		$reference = NotificationHold::reference( $order );
		$budget    = array_fill( 0, Throttle::PER_DAY, time() );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, $budget, false );
		$released = NotificationHold::release( $order->get_id(), $reference );
		$this->assertIsArray( $released );
		$this->assertSame( $id, $released['job'] );
		$this->assertSame( $released, NotificationHold::release( $order->get_id(), $reference ) );
		$order->read_meta_data( true );
		$this->assertSame( $evidence, Queue::data( $order ) );
		$this->assertSame( 'yes', $order->get_meta( Queue::PENDING ) );
		$this->assertFalse( NotificationHold::held( $order ) );
		$after = $jobs->load( $id );
		$this->assertNotNull( $after );
		$this->assertSame( $original['message']->to_array(), $after['message']->to_array() );
		$this->assertSame( $original['attempts'], $after['attempts'] );
		$this->assertSame( $budget, get_option( Throttle::OPTION ) );
		$actions = as_get_scheduled_actions(
			array(
				'hook'   => Outbox::HOOK,
				'args'   => array( $id ),
				'group'  => Outbox::GROUP,
				'status' => 'pending',
			)
		);
		$this->assertCount( 1, $actions );
		$action = reset( $actions );
		$this->assertGreaterThanOrEqual( ( new Throttle() )->next_slot( time() ), $action->get_schedule()->get_date()->getTimestamp() );
		$this->assertGreaterThan( 0, $released['event'] );
	}

	/** A hold established before classification prevents provider work and job creation. */
	public function test_held_unclassified_record_and_stale_recovery_spend_nothing(): void {
		[ $order, $id ] = $this->held_inquiry();
		( new JobStore() )->delete( $id );
		$data                     = Queue::data( $order );
		$data['notification_job'] = 0;
		StructuredMeta::update( $order, Queue::META, $data );
		// A stale recovery selection or an order-only marker must also be safe.
		$order->update_meta_data( Queue::PENDING, 'yes' );
		$order->save_meta_data();
		$budget = get_option( Throttle::OPTION, array() );
		$jobs   = self::mail_jobs_after( 0 );
		$calls  = 0;
		$watch  = static function ( $pre ) use ( &$calls ) {
			++$calls;
			return $pre;
		};
		add_filter( 'pre_http_request', $watch );
		try {
			$queue = new Queue();
			$queue->process( $order->get_id() );
			$queue->finish( $order->get_id(), Result::unknown( 'deadline' ) );
			$queue->expire( $order->get_id() );
			$queue->recover();
		} finally {
			remove_filter( 'pre_http_request', $watch ); }
		$order->read_meta_data( true );
		$this->assertSame( 0, $calls );
		$this->assertSame( $data, Queue::data( $order ) );
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$this->assertSame( $jobs, self::mail_jobs_after( 0 ) );
	}

	/** Source binding keeps an order-only or pending-only hold effective on retries. */
	public function test_bound_job_checks_order_hold_even_without_job_marker(): void {
		[ $order, $id ] = $this->held_inquiry();
		update_post_meta( $id, JobStore::INQUIRY_META, $order->get_id() );
		delete_post_meta( $id, NotificationHold::META );
		$budget = get_option( Throttle::OPTION, array() );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is the fixed native linker_commerce_mail_attempt hook.
		$order->delete_meta_data( NotificationHold::META );
		$order->save_meta_data();
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is the fixed native linker_commerce_mail_attempt hook.
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$this->assertSame( 'private', get_post_status( $id ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** Staff capability and the exact displayed hold are independently required. */
	public function test_release_rejects_nonstaff_and_stale_reference(): void {
		[ $order, $id ] = $this->held_inquiry();
		$reference      = NotificationHold::reference( $order );
		$this->as_user( 0 );
		$result = NotificationHold::release( $order->get_id(), $reference );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( 'forbidden', $result->get_error_code() );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$result = NotificationHold::release( $order->get_id(), str_repeat( 'b', 64 ) );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( 'notification_changed', $result->get_error_code() );
		$this->assertTrue( NotificationHold::job_held( $id ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** Two real connections racing a release keep one audit event and one original attempt. */
	public function test_concurrent_release_and_busy_lock_preserve_one_notification(): void {
		[ $order, $id ] = $this->held_inquiry();
		$staff          = $this->customer();
		$user           = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$basis   = NotificationHold::reference( $order );
		$barrier = tempnam( sys_get_temp_dir(), 'linker-537-' );
		$this->assertIsString( $barrier );
		$this->later(
			static function () use ( $barrier ): void {
				if ( file_exists( $barrier ) ) {
					unlink( $barrier );
				} }
		);
		$start  = static function ( string $mode ) use ( $order, $staff, $basis, $barrier ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Independent local native DB connections prove the mutex boundary.
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/notification_hold_worker.php', (string) $order->get_id(), (string) $staff->get_id(), $basis, $barrier, $mode ),
				array(
					0 => array( 'pipe', 'r' ),
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes
			);
			self::assertIsResource( $process );
			fclose( $pipes[0] );
			return array( $process, $pipes );
		};
		$close  = static function ( array $worker ): void {
			[ $process, $pipes ] = $worker;
			$output              = stream_get_contents( $pipes[1] ) . stream_get_contents( $pipes[2] );
			fclose( $pipes[1] );
			fclose( $pipes[2] );
			self::assertSame( 0, proc_close( $process ), $output );
		};
		$locked = $start( 'hold-lock' );
		$until  = microtime( true ) + 5;
		while ( 'locked' !== file_get_contents( $barrier ) && microtime( true ) < $until ) {
			usleep( 10000 ); }
		$this->assertSame( 'locked', file_get_contents( $barrier ) );
		$result = NotificationHold::release( $order->get_id(), $basis );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( 'notification_busy', $result->get_error_code() );
		$budget = get_option( Throttle::OPTION, array() );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is the fixed native linker_commerce_mail_attempt hook.
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		$late = Result::unknown( 'deadline' );
		( new Queue() )->finish( $order->get_id(), $late );
		$this->assertFalse( as_has_scheduled_action( Queue::FINISH, array( $order->get_id(), $late ), Outbox::GROUP ) );
		$close( $locked );
		file_put_contents( $barrier, '' );
		$one = $start( 'release' );
		$two = $start( 'release' );
		file_put_contents( $barrier, 'go' );
		$close( $one );
		$close( $two );
		$order = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->assertFalse( NotificationHold::held( $order ) );
		$events = array_filter(
			wc_get_order_notes(
				array(
					'order_id' => $order->get_id(),
					'type'     => 'internal',
				)
			),
			static fn ( $note ) => (bool) get_comment_meta( $note->id, NotificationHold::EVENT, true )
		);
		$this->assertCount( 1, $events );
		$this->assertCount(
			1,
			as_get_scheduled_actions(
				array(
					'hook'   => Outbox::HOOK,
					'args'   => array( $id ),
					'group'  => Outbox::GROUP,
					'status' => 'pending',
				)
			)
		);
		$this->assertIsArray( NotificationHold::release( $order->get_id(), $basis ) );
		// A staff hold release does not supply the missing bound content verdict.
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array(), false );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is the fixed native linker_commerce_mail_attempt hook.
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is the fixed native linker_commerce_mail_attempt hook.
		$retained = ( new JobStore() )->load( $id );
		$this->assertNotNull( $retained );
		$this->assertSame( 'Original notification body.', $retained['message']->body );
		$this->assertSame( 0, $retained['attempts'] );
		$this->assertFalse( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		$this->assertSame( array(), get_option( Throttle::OPTION ) );
	}

	/** An invalid or cross-record nonce never reaches the staff release operation. */
	public function test_admin_release_rejects_missing_and_cross_record_nonces(): void {
		// phpcs:disable WordPress.Security.NonceVerification -- Deliberately submit missing and cross-record nonces to the real protected controller.
		[ $order, $id ] = $this->held_inquiry();
		$staff          = $this->customer();
		$user           = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$reference     = NotificationHold::reference( $order );
		$prior_post    = $_POST;
		$prior_request = $_REQUEST;
		$handler       = static function () {
			return static function (): void {
				throw new \RuntimeException( 'nonce-rejected' );
			};
		};
		add_filter( 'wp_die_handler', $handler );
		try {
			foreach ( array( '', wp_create_nonce( 'linker_notification_release_' . ( $order->get_id() + 1 ) . '_' . $reference ) ) as $nonce ) {
				$_POST    = array(
					'inquiry'   => (string) $order->get_id(),
					'reference' => $reference,
				);
				$_REQUEST = array_merge( $_POST, array( '_wpnonce' => $nonce ) );
				$rejected = false;
				try {
					( new \Linker\Commerce\Inquiry\Assessment\Admin() )->release(); } catch ( \RuntimeException $error ) {
					$rejected = 'nonce-rejected' === $error->getMessage(); }
					$this->assertTrue( $rejected );
					$this->assertTrue( NotificationHold::job_held( $id ) );
			}
		} finally {
			$_POST    = $prior_post;
			$_REQUEST = $prior_request;
			remove_filter( 'wp_die_handler', $handler );
		}
	}
	// phpcs:enable WordPress.Security.NonceVerification

	/** Failed native scheduling rolls back release metadata and its private audit note. */
	public function test_failed_release_scheduling_keeps_original_hold_and_message(): void {
		[ $order, $id ] = $this->held_inquiry();
		$staff          = $this->customer();
		$user           = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$before = ( new JobStore() )->load( $id );
		$this->assertNotNull( $before );
		$fail = static function ( $pre, $timestamp, $hook ) {
			return Outbox::HOOK === $hook ? 0 : $pre;
		};
		add_filter( 'pre_as_schedule_single_action', $fail, 10, 3 );
		try {
			$result = NotificationHold::release( $order->get_id(), NotificationHold::reference( $order ) ); } finally {
			remove_filter( 'pre_as_schedule_single_action', $fail, 10 ); }
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( 'notification_release_failed', $result->get_error_code() );
			$order->read_meta_data( true );
			$this->assertTrue( NotificationHold::held( $order ) );
			$this->assertSame( 'held', $order->get_meta( Queue::PENDING ) );
			$this->assertFalse( $order->meta_exists( NotificationHold::RELEASED ) );
			$after = ( new JobStore() )->load( $id );
			$this->assertNotNull( $after );
			$this->assertSame( $before['message']->to_array(), $after['message']->to_array() );
			$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
			$events = array_filter(
				wc_get_order_notes(
					array(
						'order_id' => $order->get_id(),
						'type'     => 'internal',
					)
				),
				static fn ( $note ) => (bool) get_comment_meta( $note->id, NotificationHold::EVENT, true )
			);
		$this->assertCount( 0, $events );
	}

	/** Capturing a retained message must not claim a physical send in native order notes. */
	public function test_capturing_notification_does_not_record_a_false_delivery_note(): void {
		$order = wc_create_order( array( 'status' => 'pending' ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$order->set_billing_email( self::TESTER );
		$order->save();
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class ];
		$this->assertInstanceOf( \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class, $email );
		$before  = wc_get_order_notes(
			array(
				'order_id' => $order->get_id(),
				'type'     => 'internal',
			)
		);
		$budget  = get_option( Throttle::OPTION, array() );
		$message = $email->capture( $order );
		$this->assertInstanceOf( Message::class, $message );
		$this->assertCount(
			count( $before ),
			wc_get_order_notes(
				array(
					'order_id' => $order->get_id(),
					'type'     => 'internal',
				)
			)
		);
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
	}

	/**
	 * Native incident-compatible data.
	 *
	 * @return array{WC_Order, int} Inquiry and retained notification.
	 */
	private function held_inquiry(): array {
		$order = wc_create_order( array( 'status' => 'inquiry-received' ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		// This fixture deliberately represents pre-policy incident data, not a new managed source.
		delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() );
		$order->delete_meta_data( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::MARKER );
		$order->delete_meta_data( \Linker\Commerce\Inquiry\Assessment\AsyncRunner::META );
		foreach ( array( Queue::PROCESS, Queue::EXPIRE ) as $hook ) {
			as_unschedule_all_actions( $hook, array( $order->get_id() ), Outbox::GROUP );
		}
		$this->assertFalse( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::managed( $order->get_id() ) );
		$order->update_meta_data( NotificationHold::META, array( 'reason' => 'synthetic existing incident' ) );
		$order->save_meta_data();
		$message = new Message( array( self::TESTER ), 'Held synthetic inquiry', 'Original notification body.', array( Message::INTERNAL_HEADER ), array() );
		$jobs    = new JobStore();
		$id      = $jobs->create( $message, $order->get_id() );
		$hold    = array(
			'incident'        => 'synthetic-incident',
			'at'              => time(),
			'reason'          => 'confirmed_campaign_notification_hold',
			'manifest_sha256' => str_repeat( 'a', 64 ),
			'order'           => $order->get_id(),
			'job'             => $id,
		);
		StructuredMeta::update(
			$order,
			Queue::META,
			array(
				'notification_job' => $id,
				'accepted_at'      => microtime( true ),
				'deadline'         => microtime( true ) + 10,
				'snapshot'         => array(),
				'result'           => Result::unknown( 'deadline' ),
			)
		);
		StructuredMeta::update( $order, '_linker_incident_hold', $hold );
		$order->update_meta_data( Queue::PENDING, 'held' );
		$order->save_meta_data();
		update_post_meta( $id, '_linker_incident_hold', $hold );
		return array( $order, $id );
	}
}

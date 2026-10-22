<?php
/** Native stop policy for automatic review reminders.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Health\ReviewReminder;
use Linker\Commerce\Health\ReviewSummary;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\RecoverySchedule;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;

/** Real WP/Woo/AS records; the instance mailer never sends externally.
 *
 * @coversNothing
 */
final class ReviewReminderTest extends IntegrationTestCase {
	/** Keep original reminder history and recovery heartbeat intact. */
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( ReviewReminder::OPTION, Queue::HEARTBEAT ) as $name ) {
			$before = get_option( $name );
			$this->later(
				static function () use ( $name, $before ): void {
					false === $before ? delete_option( $name ) : update_option( $name, $before, false );
				}
			);
		}
	}

	/** No reminder is produced and old history remains unchanged. */
	public function test_reminder_producer_is_disabled_without_reading_or_rewriting_history(): void {
		$history = '{"events":[1,2],"active":true,"last":3,"job":4}';
		update_option( ReviewReminder::OPTION, $history, false );
		$reads   = 0;
		$summary = new ReviewSummary(
			static function () use ( &$reads ): array {
				++$reads;
				return array(
					'count'  => 77,
					'oldest' => time() - HOUR_IN_SECONDS,
					'url'    => admin_url(),
				);
			}
		);
		$before  = self::newest_mail_job();
		$budget  = get_option( OptionBudgetLedger::OPTION );
		$legacy  = get_option( Throttle::OPTION );
		$actor   = new ReviewReminder( $summary );
		$actor->tick();
		$actor->tick();
		$this->assertSame( 0, $reads );
		$this->assertSame( array(), self::mail_jobs_after( $before ) );
		$this->assertSame( $history, get_option( ReviewReminder::OPTION ) );
		$this->assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
	}

	/** The production module still runs its other actual minute recovery. */
	public function test_native_recovery_hook_still_updates_the_inquiry_heartbeat(): void {
		$before = microtime( true );
		$jobs   = self::newest_mail_job();
		do_action( RecoverySchedule::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Existing native recovery action.
		$this->assertGreaterThanOrEqual( $before, (float) get_option( Queue::HEARTBEAT ) );
		$this->assertSame( array(), self::mail_jobs_after( $jobs ) );
	}

	/** Existing jobs are retained before transport even when persistence fails.
	 *
	 * @dataProvider hold_failures
	 * @param string $fault Native fault seam.
	 */
	public function test_queued_reminder_never_spends_or_sends_and_keeps_the_original( string $fault ): void {
		$jobs    = new JobStore();
		$message = new Message( array( self::TESTER ), 'Synthetic review reminder', 'Full original body remains unchanged.', array( Message::INTERNAL_HEADER ), array(), true, Message::REVIEW_REMINDER );
		$id      = $jobs->create( $message );
		$this->assertGreaterThan( 0, $id );
		$jobs->record_failure( $id, 2, 'Original diagnostic retained.' );
		as_schedule_single_action( time() + 60, Outbox::HOOK, array( $id ), Outbox::GROUP, true );
		$before    = get_post_meta( $id );
		$budget    = get_option( OptionBudgetLedger::OPTION );
		$legacy    = get_option( Throttle::OPTION );
		$attempts  = 0;
		$observe   = static function () use ( &$attempts ): void {
			++$attempts;
		};
		$fault_hit = false;
		$hold      = static function ( $check, $object_id, $key ) use ( $fault, $id, &$fault_hit ) {
			if ( 'hold' === $fault && $object_id === $id && NotificationHold::META === $key ) {
				$fault_hit = true;
				return false;
			}
			return $check;
		};
		$cancel    = static function ( string $sql ) use ( $fault, &$fault_hit ): string {
			if ( 'cancel' === $fault && str_starts_with( $sql, 'UPDATE' ) && str_contains( $sql, 'actionscheduler_actions' ) && str_contains( $sql, 'canceled' ) ) {
				$fault_hit = true;
				return 'SELECT 0';
			}
			return $sql;
		};
		add_action( 'phpmailer_init', $observe, PHP_INT_MAX );
		add_filter( 'update_post_metadata', $hold, 10, 3 );
		add_filter( 'query', $cancel, 998 );
		try {
			do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Actual original-job consumer.
		} finally {
			remove_action( 'phpmailer_init', $observe, PHP_INT_MAX );
			remove_filter( 'update_post_metadata', $hold, 10 );
			remove_filter( 'query', $cancel, 998 );
		}
		$this->assertSame( 0, $attempts );
		if ( '' !== $fault ) {
			$this->assertTrue( $fault_hit );
		}
		$stored = $jobs->load( $id );
		$this->assertNotNull( $stored );
		$this->assertSame( $message->to_array(), $stored['message']->to_array() );
		$this->assertSame( 2, $stored['attempts'] );
		$this->assertSame( $before['_linker_mail_error'], get_post_meta( $id, '_linker_mail_error', false ) );
		$this->assertSame( 'private', get_post_status( $id ) );
		$this->assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
		if ( '' === $fault ) {
			$this->assertTrue( NotificationHold::job_held( $id ) );
			$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		}
	}

	/** The same final transport gate also rejects a typed nonqueued reminder. */
	public function test_nonqueued_typed_reminder_cannot_reach_transport_or_create_a_job(): void {
		$before  = self::newest_mail_job();
		$budget  = get_option( OptionBudgetLedger::OPTION );
		$legacy  = get_option( Throttle::OPTION );
		$attempt = new \ReflectionMethod( Outbox::class, 'attempt' );
		$message = new Message( array( self::TESTER ), 'Synthetic inline reminder', 'No inline transport.', array(), array(), true, Message::REVIEW_REMINDER );
		$this->assertFalse( $attempt->invoke( new Outbox( new JobStore(), new Throttle() ), $message, 0, 0 ) );
		$this->assertSame( array(), self::mail_jobs_after( $before ) );
		$this->assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
	}

	/** Native success and fault cases.
	 *
	 * @return array<string,array{string}> Cases.
	 */
	public static function hold_failures(): array {
		return array(
			'normal'       => array( '' ),
			'hold-write'   => array( 'hold' ),
			'cancel-write' => array( 'cancel' ),
		);
	}

	/** Normal standard and critical messages remain eligible for local delivery.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $critical Normal notification priority.
	 */
	public function test_normal_mail_still_uses_the_existing_native_transport( bool $critical ): void {
		$jobs = new JobStore();
		$id   = $jobs->create( new Message( array( self::TESTER ), 'Synthetic normal notification', 'Normal original notification.', array(), array(), $critical ) );
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Actual native consumer.
		$this->assertNull( $jobs->load( $id ) );
		$this->assertNotFalse( get_option( OptionBudgetLedger::OPTION ) );
	}
}

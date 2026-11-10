<?php
/** Native transport-budget and trusted-priority evidence.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Producer;
use Linker\Commerce\Mail\Throttle;
use wpdb;

/** Native budget proof.
 *
 * @coversNothing
 */
final class MailBudgetTest extends IntegrationTestCase {
	/** Legacy history is migrated once, not deleted or charged again on restart. */
	public function test_legacy_is_preserved_and_smtp_recovers_without_php_reset(): void {
		$now    = time();
		$legacy = array_fill( 0, 80, $now - 120 );
		update_option( Throttle::OPTION, $legacy, false );
		$t = new Throttle();
		$this->assertSame( $now, $t->reserve( $now, Throttle::SMTP ) );
		$this->assertSame( $now - 120 + DAY_IN_SECONDS, $t->reserve( $now, Throttle::PHP, true ) );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
		$before = get_option( OptionBudgetLedger::OPTION );
		$this->assertCount( 161, json_decode( $before, true )['entries'] );
		$this->assertSame( $now, ( new Throttle() )->next_slot( $now, Throttle::SMTP ) );
		$this->assertSame( $before, get_option( OptionBudgetLedger::OPTION ) );
		$t->next_slot( $now + DAY_IN_SECONDS );
		$this->assertSame( $before, get_option( OptionBudgetLedger::OPTION ), 'Future retry scheduling must not refund real history.' );
	}

	/** Two independent native processes race initialization and the final minute slot. */
	public function test_two_workers_initialize_once_and_only_one_gets_last_slot(): void {
		$now    = time();
		$legacy = array_fill( 0, Throttle::PER_MINUTE - 1, $now - 5 );
		update_option( Throttle::OPTION, $legacy, false );
		$directory = sys_get_temp_dir() . '/linker-budget-' . self::tag();
		mkdir( $directory );
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
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Two test-owned local native workers, no external transport.
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/mail_budget_reserve.php', untrailingslashit( ABSPATH ), $directory . '/' . $worker, $directory . '/go', (string) $now ),
				array(
					0 => array( 'pipe', 'r' ),
					1 => array( 'file', $directory . '/log', 'a' ),
					2 => array( 'file', $directory . '/log', 'a' ),
				),
				$pipes
			);
			$this->assertIsResource( $process );
			fclose( $pipes[0] );
			$workers[] = $process;
		}
		$deadline = microtime( true ) + 15;
		while ( ( ! is_file( $directory . '/a.ready' ) || ! is_file( $directory . '/b.ready' ) ) && microtime( true ) < $deadline ) {
			usleep( 1000 );
		}
		$this->assertFileExists( $directory . '/a.ready' );
		$this->assertFileExists( $directory . '/b.ready' );
		file_put_contents( $directory . '/go', 'go' );
		foreach ( $workers as $worker ) {
			$this->assertSame( 0, proc_close( $worker ) );
		}
		$slots = array( (int) file_get_contents( $directory . '/a' ), (int) file_get_contents( $directory . '/b' ) );
		sort( $slots );
		$this->assertSame( $now, $slots[0] );
		$this->assertGreaterThan( $now, $slots[1] );
		wp_cache_delete( OptionBudgetLedger::OPTION, 'options' );
		wp_cache_delete( 'notoptions', 'options' );
		$entries = json_decode( get_option( OptionBudgetLedger::OPTION ), true )['entries'];
		$this->assertCount( 15, $entries, 'Seven legacy charges in each pool plus exactly one new SMTP attempt.' );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
	}

	/** A second database connection's mutex blocks sends without charging or waiting. */
	public function test_busy_and_corrupt_storage_fail_closed(): void {
		global $wpdb;
		$other = new wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$name  = 'linker-mail-budget-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Independently owned native mutex proves connection isolation.
		$this->assertSame( '1', (string) $other->get_var( $other->prepare( 'SELECT GET_LOCK(%s, 0)', $name ) ) );
		try {
			$now   = time();
			$start = microtime( true );
			$this->assertSame( $now + 1, ( new Throttle() )->reserve( $now ) );
			$this->assertLessThan( 1, microtime( true ) - $start );
			$this->assertFalse( get_option( OptionBudgetLedger::OPTION ) );
		} finally {
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
			$other->close();
		}
		// phpcs:enable
		update_option( OptionBudgetLedger::OPTION, '{bad-json', false );
		$this->assertGreaterThan( time(), ( new Throttle() )->reserve( time() ) );
		$this->assertSame( '{bad-json', get_option( OptionBudgetLedger::OPTION ) );
	}

	/** Priority comes from exact native producers, never message text or headers. */
	public function test_trusted_producers_and_private_staff_priority(): void {
		$atts = array(
			'to'       => self::TESTER,
			'subject'  => 'Password reset critical',
			'message'  => 'critical emergency',
			'headers'  => array( 'X-Linker-Critical: yes' ),
			'critical' => true,
			'category' => Message::REVIEW_REMINDER,
		);
		$this->assertFalse( Message::from_wp_mail( $atts )->critical );
		$this->assertSame( Message::STANDARD, Message::from_wp_mail( $atts )->category );
		$this->assertTrue( Producer::critical( static fn () => Message::from_wp_mail( $atts ) )->critical );
		$this->assertFalse( Message::from_wp_mail( $atts )->critical );
		$producer = new Producer();
		$this->assertSame( $atts, $producer->password_reset( $atts ) );
		$this->assertTrue( Message::from_wp_mail( $atts )->critical );
		$this->assertFalse( Message::from_wp_mail( $atts )->critical, 'A native reset fingerprint is consumed once.' );
		WC()->mailer();
		$reset    = new \WC_Email_Customer_Reset_Password();
		$priority = $producer->woocommerce( static fn () => Message::from_wp_mail( $atts )->critical, $reset );
		$this->assertTrue( $priority() );
		$ordinary     = new class() extends \WC_Email {
			/** A fake producer with no registered native send hooks. */
			public function __construct() {}
		};
		$ordinary->id = 'customer_reset_password';
		$this->assertFalse( $producer->woocommerce( static fn () => Message::from_wp_mail( $atts )->critical, $ordinary )(), 'A forged email ID cannot promote an untrusted producer class.' );
		$jobs    = new \Linker\Commerce\Mail\JobStore();
		$message = new Message( array( self::TESTER ), 'Staff release', 'Original body', array(), array() );
		$id      = $jobs->create( $message );
		$this->assertFalse( $jobs->critical( $id ) );
		$jobs->promote( $id );
		$this->assertTrue( $jobs->critical( $id ) );
		$readback = $jobs->load( $id );
		$this->assertNotNull( $readback );
		$this->assertSame( $message->to_array(), $readback['message']->to_array() );
	}

	/**
	 * Ten retry-exhausted and orphaned jobs terminate into FAILED_STATUS, unschedule
	 * their pending retries, and leave Throttle at now for immediate delivery.
	 */
	public function test_ten_failed_and_orphaned_jobs_terminate_without_blocking_throttle(): void {
		$emails = WC()->mailer()->get_emails();
		$email  = $emails[ \Linker\Commerce\Digest\DigestEmail::class ];
		$this->assertInstanceOf( \WC_Email::class, $email );
		$message = \Linker\Commerce\Mail\Capture::run(
			$email,
			function () use ( $email ): void {
				$this->assertTrue( $email->send( self::TESTER, 'Lifecycle fixture notice', 'Normal body.', '', array() ) );
			}
		);
		$this->assertInstanceOf( Message::class, $message );
		$store       = new \Linker\Commerce\Mail\JobStore();
		$exhausted   = array();
		$orphans     = array();
		$attempts    = count( \Linker\Commerce\Mail\Outbox::RETRY_DELAYS ) + 1;
		$expired_at  = time() - \Linker\Commerce\Mail\NativeAttempt::TIMEOUT - 10;
		$digest_hash = hash( 'sha256', (string) wp_json_encode( $message->to_array() ) );

		for ( $i = 0; $i < 5; ++$i ) {
			$id = $store->create( $message );
			$this->assertGreaterThan( 0, $id );
			$store->record_failure( $id, $attempts, 'Simulated permanent transport failure.' );
			$exhausted[] = $id;
		}
		for ( $i = 0; $i < 5; ++$i ) {
			$id = $store->create( $message );
			$this->assertGreaterThan( 0, $id );
			$witness = 0 === $i % 2
				? array(
					'token'   => wp_generate_uuid4(),
					'message' => $digest_hash,
					'state'   => 'open',
					'at'      => $expired_at,
				)
				: array(
					'token'   => wp_generate_uuid4(),
					'message' => $digest_hash,
					'state'   => 'open',
				);
			update_post_meta( $id, \Linker\Commerce\Mail\NativeAttempt::META, $witness );
			$this->assertTrue( \Linker\Commerce\Mail\NativeAttempt::expired( $id ) );
			$orphans[] = $id;
		}

		// Recovery reclaims all 5 timed-out orphan witnesses; Outbox terminates all 5 exhausted jobs.
		( new \Linker\Commerce\Mail\PreTransportRecovery( $store ) )->recover();
		foreach ( $exhausted as $id ) {
			/** This action is documented in Mail\Module::register(). */
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer.
		}

		$all_jobs   = array_merge( $exhausted, $orphans );
		$failed_ids = array_column( $store->failed(), 'id' );
		foreach ( $all_jobs as $id ) {
			clean_post_cache( $id );
			$this->assertSame( \Linker\Commerce\Mail\JobStore::FAILED_STATUS, get_post_status( $id ) );
			$this->assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP ) );
			$this->assertSame( '', get_post_meta( $id, \Linker\Commerce\Mail\NativeAttempt::META, true ) );
			$this->assertSame( '', get_post_meta( $id, \Linker\Commerce\Mail\PreTransportRecovery::META, true ) );
			$this->assertContains( $id, $failed_ids );
		}
		$this->assertSame( 'notification_not_accepted', get_option( \Linker\Commerce\Mail\CapacityHealth::OPTION )['reason'] );

		// Re-invoking the hook on terminal jobs neither attempts transport nor schedules retries.
		foreach ( $all_jobs as $id ) {
			/** This action is documented in Mail\Module::register(). */
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer.
			$this->assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		}

		// Throttle remains completely unblocked and delivers a new message at once.
		$now = time();
		$this->assertSame( $now, ( new Throttle() )->next_slot( $now ) );
		$live_id = $store->create( $message );
		$this->assertGreaterThan( 0, $live_id );
		$delivered = 0;
		$observe   = static function () use ( &$delivered ): void {
			++$delivered;
		};
		add_action( 'wp_mail_succeeded', $observe );
		try {
			/** This action is documented in Mail\Module::register(). */
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $live_id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer.
		} finally {
			remove_action( 'wp_mail_succeeded', $observe );
		}
		$this->assertSame( 1, $delivered );
		$this->assertNull( $store->load( $live_id ) );
	}
}

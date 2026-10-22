<?php
/**
 * Actual native queue/source/action writes under real local connection loss.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Protection\IntakeStore;

// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.RestrictedFunctions -- Independent native visibility and server-side KILL of only this local test connection are the behavior under test.

/**
 * No HTTP or real mail; the local integration transport is intercepted.
 *
 * @coversNothing
 */
final class AtomicMailConnectionTest extends IntegrationTestCase {
	/** Source acknowledgement observed inside the actual native callback.
	 *
	 * @var bool
	 */
	private bool $acked = false;
	/** Whether the commit acknowledgement seam killed the original connection.
	 *
	 * @var bool
	 */
	private bool $commit_killed = false;
	/** Preserve the instance registry and initialize exact bounded empty queue state. */
	protected function setUp(): void {
		parent::setUp();
		$before = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $before ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $before ) {
					update_option( IntakeStore::OPTION, $before, false );
				}
			}
		);
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				IntakeStore::save( $state );
				return array();
			}
		);
	}

	/**
	 * First native INSERT and later meta INSERT must never replay in autocommit.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $partial Kill after the native post and complete message were written.
	 */
	public function test_actual_job_connection_death_has_no_partial_native_job_source_action_or_capacity( bool $partial ): void {
		global $wpdb;
		$other  = self::observer();
		$title  = 'Synthetic568 atomic ' . self::tag();
		$source = 'synthetic568_source_' . self::tag();
		update_option( $source, 'pending', false );
		$before = $other->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, IntakeStore::OPTION ) );
		$killed = false;
		$kill   = static function ( string $sql ) use ( $other, $title, $partial, &$killed ): string {
			global $wpdb;
			$target = $partial ? str_contains( $sql, '_linker_mail_attempts' ) : str_contains( $sql, $title );
			if ( ! $killed && str_starts_with( $sql, 'INSERT' ) && $target ) {
				$killed = true;
				$other->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill, 999 );
		try {
			$id = ( new JobStore() )->create(
				new Message( array( self::TESTER ), $title, 'Synthetic complete body.', array(), array() ),
				0,
				static function ( int $job ) use ( $source ): void {
					update_option( $source, $job, false );
				}
			);
		} finally {
			remove_filter( 'query', $kill, 999 );
		}
		self::assertTrue( $killed );
		self::assertSame( 0, $id );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE post_title=%s', $wpdb->posts, $title ) ) );
		self::assertSame( 'pending', $other->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, $source ) ) );
		self::assertSame( $before, $other->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, IntakeStore::OPTION ) ) );
		self::assertTrue( $wpdb->db_connect( false ), 'Only reconnect the dead local fixture after observing the real outcome.' );
		delete_option( $source );
		$other->close();
	}

	/** A server-committed but unacknowledged result retains exactly the original job and AS. */
	public function test_unknown_commit_retains_one_native_job_ack_and_recovery_action(): void {
		global $wpdb;
		$other   = self::observer();
		$title   = 'Synthetic568 commit ' . self::tag();
		$source  = 'synthetic568_source_' . self::tag();
		$job     = 0;
		$attempt = 0;
		update_option( $source, 'pending', false );
		$kill = function ( string $sql ) use ( $other ): string {
			global $wpdb;
			if ( $this->acked && ! $this->commit_killed && 'COMMIT' === $sql ) {
				$this->commit_killed = true;
				$handle              = $wpdb->__get( 'dbh' );
				$handle->query( 'COMMIT' );
				$other->query( 'KILL CONNECTION ' . $handle->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill, 999 );
		try {
			$result = ( new JobStore() )->create(
				new Message( array( self::TESTER ), $title, 'Synthetic original job.', array(), array() ),
				0,
				function ( int $id ) use ( $source, &$job ): void {
					$job = $id;
					update_option( $source, $id, false );
					$this->acked = true;
				}
			);
		} finally {
			remove_filter( 'query', $kill, 999 );
		}
		self::assertTrue( $this->commit_killed );
		self::assertSame( 0, $result, 'The lost commit cannot falsely acknowledge success.' );
		self::assertGreaterThan( 0, $job );
		self::assertSame( (string) $job, $other->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, $source ) ) );
		self::assertSame( '1', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE ID=%d AND post_status=%s', $wpdb->posts, $job, 'private' ) ) );
		self::assertSame( '1', (string) $other->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE hook=%s AND args=%s AND status=%s', $wpdb->prefix . 'actionscheduler_actions', Outbox::HOOK, wp_json_encode( array( $job ) ), 'pending' ) ) );
		self::assertTrue( $wpdb->db_connect( false ) );
		clean_post_cache( $job );
		wp_cache_delete( IntakeStore::OPTION, 'options' );
		self::assertArrayHasKey( $job, get_option( IntakeStore::OPTION )['mail_capacity']['entries'] );
		$transport = static function () use ( &$attempt ): void {
			++$attempt;
		};
		add_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		try {
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing original-job consumer.
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Repeated independent recovery cannot send a deleted original job.
		} finally {
			remove_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		}
		self::assertSame( 1, $attempt );
		self::assertNull( ( new JobStore() )->load( $job ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $job ), Outbox::GROUP ) );
		delete_option( $source );
		$other->close();
	}

	/** Actual PHP process death after commit leaves the same original native recovery. */
	public function test_sigkill_after_native_handoff_recovers_original_job_once(): void {
		$source = 'synthetic568_crash_' . self::tag();
		$file   = tempnam( sys_get_temp_dir(), 'linker568-crash-' );
		self::assertIsString( $file );
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Actual isolated PHP process death after durable native handoff is under test.
		$process = proc_open(
			array( PHP_BINARY, dirname( __DIR__, 2 ) . '/fixtures/mail_commit_crash_writer.php', rtrim( ABSPATH, '/' ), $file, $source ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'file', $file . '.log', 'a' ),
				2 => array( 'file', $file . '.log', 'a' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		$deadline = microtime( true ) + 10;
		do {
			$status = proc_get_status( $process );
			if ( ! $status['running'] ) {
				break;
			}
			usleep( 1000 );
		} while ( microtime( true ) < $deadline );
		if ( $status['running'] ) {
			proc_terminate( $process, 9 );
		}
		proc_close( $process );
		$this->later(
			static function () use ( $source, $file ): void {
				delete_option( $source );
				unlink( $file );
				unlink( $file . '.log' );
			}
		);
		self::assertFalse( $status['running'] );
		self::assertTrue( $status['signaled'] );
		self::assertSame( 9, $status['termsig'] );
		$id = (int) file_get_contents( $file );
		self::assertGreaterThan( 0, $id );
		wp_cache_delete( $source, 'options' );
		wp_cache_delete( 'notoptions', 'options' );
		self::assertSame( $id, (int) get_option( $source ) );
		self::assertNotNull( ( new JobStore() )->load( $id ) );
		self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		$count     = 0;
		$transport = static function () use ( &$count ): void {
			++$count;
		};
		add_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		try {
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Committed original-job consumer.
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Duplicate recovery.
		} finally {
			remove_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		}
		self::assertSame( 1, $count );
		self::assertNull( ( new JobStore() )->load( $id ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** A second connection observes actual commits rather than current PHP caches. */
	private static function observer(): \wpdb {
		return new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
	}
}

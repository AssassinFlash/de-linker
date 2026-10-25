<?php
/**
 * Native final Outbox capacity, pre-reservation and transaction boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Protection\IntakeStore;

/**
 * Actual native queue consumers; no real model or mail transport.
 *
 * @coversNothing
 */
final class MailCapacityTest extends IntegrationTestCase {
	/** Preserve the local snapshot's pre-existing jobs and capacity ledger. */
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
	}

	/** Held source jobs remain charged and cannot arm actions, even inside another writer. */
	public function test_held_native_job_has_no_action_before_or_inside_an_outer_retry(): void {
		$this->seed_jobs( 0 );
		$order = new \WC_Order();
		$order->update_meta_data( \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'synthetic retained incident' ) );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$message = new Message( array( self::TESTER ), 'Synthetic held original', 'Complete original body.', array(), array() );
		$id      = ( new JobStore() )->create( $message, $order->get_id() );
		self::assertGreaterThan( 0, $id );
		$before = get_post_meta( $id );
		$ledger = get_option( OptionBudgetLedger::OPTION );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		\Linker\Commerce\Mail\NativeTransaction::run(
			static function () use ( $id ): void {
				do_action( Outbox::HOOK, $id ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer.
			}
		);
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		self::assertSame( $before, get_post_meta( $id ) );
		self::assertSame( $ledger, get_option( OptionBudgetLedger::OPTION ) );
		self::assertArrayHasKey( $id, get_option( IntakeStore::OPTION )['mail_capacity']['entries'] );
	}

	/** Core deletion hooks run before native cache cleanup; real absence frees space. */
	public function test_native_core_deletion_releases_occupancy_despite_a_cached_post(): void {
		$this->seed_jobs( 0 );
		$id = ( new JobStore() )->create( new Message( array( self::TESTER ), 'Synthetic native deletion', 'No transport.', array(), array() ) );
		self::assertGreaterThan( 0, $id );
		self::assertInstanceOf( \WP_Post::class, get_post( $id ) );
		self::assertArrayHasKey( $id, get_option( IntakeStore::OPTION )['mail_capacity']['entries'] );
		wp_delete_post( $id, true );
		self::assertNull( get_post( $id ) );
		self::assertArrayNotHasKey( $id, get_option( IntakeStore::OPTION )['mail_capacity']['entries'] );
	}

	/** A full ordinary queue cannot grow or consume the independent critical reserve. */
	public function test_native_job_creation_is_bounded_and_preserves_critical_capacity(): void {
		$store    = new JobStore();
		$message  = new Message( array( self::TESTER ), 'Synthetic capacity fixture', 'A stored synthetic notification.', array(), array() );
		$existing = 0;
		foreach ( self::mail_jobs_after( 0 ) as $old_id ) {
			$old = $store->load( $old_id );
			if ( null !== $old && ! $old['message']->critical && ! $store->critical( $old_id ) ) {
				++$existing;
			}
		}
		for ( $i = $existing; $i < 192; ++$i ) {
			$id = $store->create( $message );
			self::assertGreaterThan( 0, $id );
		}
		self::assertSame( 0, $store->create( $message ), 'The last native writer must refuse the next ordinary job.' );
		$critical = new Message( array( self::TESTER ), 'Synthetic critical fixture', 'A stored synthetic critical notification.', array(), array(), true );
		self::assertGreaterThan( 0, $store->create( $critical ) );
	}

	/** Native wp_mail cannot claim queued/sent, spend transport or schedule id zero. */
	public function test_full_native_outbox_is_explicit_false_and_does_not_consume_transport(): void {
		$this->seed_jobs( 192 );
		$before = self::newest_mail_job();
		$budget = get_option( OptionBudgetLedger::OPTION );
		self::assertFalse( wp_mail( self::TESTER, 'Synthetic full queue', 'Keep this out of transport.' ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( 0 ), Outbox::GROUP ) );
		self::assertSame( 'notification_not_accepted', get_option( \Linker\Commerce\Mail\CapacityHealth::OPTION )['reason'] );
	}

	/** Exact count/byte preflight cannot be reset by repeated reserve or unknown time. */
	public function test_critical_reservation_is_consumed_once_and_only_unused_notice_can_cancel(): void {
		$this->seed_jobs( 192 );
		$message   = new Message( array( self::TESTER ), 'Reserved critical', 'Complete critical message.', array(), array(), true );
		$bytes     = strlen( (string) wp_json_encode( $message->to_array() ) );
		$operation = 'synthetic-native-' . self::tag();
		$reserved  = Capacity::reserve_critical( $operation, 1, $bytes );
		self::assertIsArray( $reserved );
		self::assertSame( $reserved, Capacity::reserve_critical( $operation, 1, $bytes ) );
		$id = Capacity::within( $reserved, static fn (): int => ( new JobStore() )->create( $message ) );
		self::assertGreaterThan( 0, $id );
		self::assertFalse( Capacity::cancel_before_side_effect( $reserved ) );
		self::assertSame( 0, Capacity::within( $reserved, static fn (): int => ( new JobStore() )->create( $message ) ) );
		self::assertSame( 0, Capacity::reserve_critical( $operation, 1, $bytes )['remaining'] );
		$unused = Capacity::reserve_critical( 'known-optional-skip-' . self::tag(), 1, $bytes );
		self::assertIsArray( $unused );
		self::assertTrue( Capacity::cancel_before_side_effect( $unused ) );
		self::assertFalse( Capacity::cancel_before_side_effect( $unused ) );
	}

	/** A queued message in an outer transaction has no external side effect. */
	public function test_native_outbox_joins_outer_transaction_and_rolls_back_without_transport(): void {
		global $wpdb;
		$this->seed_jobs( 0 );
		$other      = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$deliveries = 0;
		$transport  = static function () use ( &$deliveries ): void {
			++$deliveries;
		};
		add_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		$this->later(
			static function () use ( $transport, $other ): void {
				remove_action( 'phpmailer_init', $transport, PHP_INT_MAX );
				$other->close();
			}
		);
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Independent native visibility and rollback are the behavior under test.
		$before = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) );
		wc_transaction_query( 'start' );
		try {
			self::assertTrue( Capacity::transaction_active() );
			self::assertTrue( wp_mail( self::TESTER, 'Synthetic joined transaction', 'Must not leave an uncommitted transaction.' ) );
			$id = self::newest_mail_job();
			self::assertGreaterThan( 0, $id );
			self::assertSame( 0, $deliveries );
			self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE ID=%d", $id ) ) );
			self::assertSame( $before, $other->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) ) );
			self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		} finally {
			wc_transaction_query( 'rollback' );
		}
		self::assertSame( 0, $deliveries );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE ID=%d", $id ) ) );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->prefix}actionscheduler_actions WHERE hook=%s AND args=%s", Outbox::HOOK, wp_json_encode( array( $id ) ) ) ) );
		self::assertSame( $before, $other->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) ) );
		// phpcs:enable
		clean_post_cache( $id );
	}

	/** Only a later committed consumer may send a joined native Outbox message. */
	public function test_committed_outer_job_is_sent_once_by_independent_consumer(): void {
		$this->seed_jobs( 0 );
		$deliveries = 0;
		$transport  = static function () use ( &$deliveries ): void {
			++$deliveries;
		};
		add_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		$this->later(
			static function () use ( $transport ): void {
				remove_action( 'phpmailer_init', $transport, PHP_INT_MAX );
			}
		);
		wc_transaction_query( 'start' );
		try {
			$customer = $this->customer();
			$user     = get_userdata( $customer->get_id() );
			self::assertInstanceOf( \WP_User::class, $user );
			wp_password_change_notification( $user );
			$id = self::newest_mail_job();
			self::assertSame( 0, $deliveries );
			self::assertNotNull( ( new JobStore() )->load( $id ) );
			wc_transaction_query( 'commit' );
		} finally {
			wc_transaction_query( 'rollback' );
		}
		$this->later(
			static function () use ( $id ): void {
				as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
			}
		);
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer. // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native prefixed hook.
		self::assertSame( 1, $deliveries );
		self::assertNull( ( new JobStore() )->load( $id ) );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native original-job consumer. // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing native prefixed hook.
		self::assertSame( 1, $deliveries );
	}

	/** Real consumer tests use a pre-filled, content-free registry snapshot.
	 *
	 * @param int $count Existing synthetic ordinary occupancy.
	 */
	private function seed_jobs( int $count ): void {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $count ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 1; $i <= $count; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
		self::assertIsArray( $result );
	}

	/** Two independent DB connections cannot spend the final native slot twice. */
	public function test_two_native_workers_share_the_final_count_and_byte_slot(): void {
		foreach ( array( 'count', 'bytes' ) as $boundary ) {
			$this->seed_jobs( 'count' === $boundary ? 191 : 0 );
			if ( 'bytes' === $boundary ) {
				$message = new Message( array( self::TESTER ), 'Synthetic last writer', str_repeat( 'x', 4096 ), array(), array() );
				$bytes   = strlen( (string) wp_json_encode( $message->to_array() ) );
				IntakeStore::edit(
					static function ( array &$state ) use ( $bytes ): array {
						$state['mail_capacity']['entries'][10000001] = array(
							'pool'  => 'ordinary',
							'bytes' => Capacity::LIMITS['ordinary']['bytes'] - $bytes,
						);
						IntakeStore::save( $state );
						return array();
					}
				);
			}
			$directory = $this->workers_directory();
			$first     = $this->start_worker( $directory, 'a' );
			$second    = $this->start_worker( $directory, 'b' );
			$this->await_ready( $directory . '/a.ready' );
			$this->await_ready( $directory . '/b.ready' );
			file_put_contents( $directory . '/go', 'go' );
			self::assertSame( 0, proc_close( $first ) );
			self::assertSame( 0, proc_close( $second ) );
			$a = json_decode( (string) file_get_contents( $directory . '/a' ), true );
			$b = json_decode( (string) file_get_contents( $directory . '/b' ), true );
			self::assertSame( 1, (int) ( $a['job'] > 0 ) + (int) ( $b['job'] > 0 ), $boundary . ': exactly one actual native job.' );
			self::assertLessThan( 1, max( $a['seconds'], $b['seconds'] ), 'Contending public workers never wait for a long DB lock timeout.' );
			wp_cache_delete( IntakeStore::OPTION, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
		}
	}

	/** An uncommitted outer owner cannot make another public writer hang on CAS. */
	public function test_uncommitted_outer_capacity_fails_competing_native_worker_without_waiting(): void {
		$this->seed_jobs( 0 );
		$directory = $this->workers_directory();
		$process   = $this->start_worker( $directory, 'a' );
		$this->await_ready( $directory . '/a.ready' );
		wc_transaction_query( 'start' );
		$finished = false;
		try {
			self::assertTrue( wp_mail( self::TESTER, 'Synthetic held transaction', 'No transport before commit.' ) );
			file_put_contents( $directory . '/go', 'go' );
			$deadline = microtime( true ) + 2;
			while ( ! is_file( $directory . '/a' ) && microtime( true ) < $deadline ) {
				usleep( 1000 );
			}
			$finished = is_file( $directory . '/a' );
		} finally {
			wc_transaction_query( 'rollback' );
		}
		self::assertSame( 0, proc_close( $process ) );
		self::assertTrue( $finished, 'The competing request must return while the outer transaction is still open.' );
		$result = json_decode( (string) file_get_contents( $directory . '/a' ), true );
		self::assertSame( 0, $result['job'] );
		self::assertLessThan( 1, $result['seconds'] );
	}

	/** A failed joined helper cannot roll back or commit unrelated caller work.
	 *
	 * @dataProvider joined_failures
	 * @param string $failure Native failure seam.
	 */
	public function test_joined_failure_preserves_callers_unrelated_uncommitted_write( string $failure ): void {
		global $wpdb;
		$this->seed_jobs( 0 );
		$other    = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$name     = 'synthetic_outer_' . self::tag();
		$filter   = static fn ( string $sql ): string => 'read' === $failure && str_contains( $sql, 'FOR UPDATE NOWAIT' ) ? 'SELECT missing_synthetic_568_column' : $sql;
		$this->later(
			static function () use ( $name, $other ): void {
				delete_option( $name );
				$other->close();
			}
		);
		$previous = $wpdb->suppress_errors( true );
		wc_transaction_query( 'start' );
		try {
			add_option( $name, 'unrelated-native-write', '', false );
			add_filter( 'query', $filter );
			try {
				$id = ( new JobStore() )->create(
					new Message( array( self::TESTER ), 'Synthetic joined failure', 'Never transported.', array(), array() ),
					0,
					static function (): void {
						throw new \RuntimeException( 'synthetic_accepted_callback_failed' );
					}
				);
			} finally {
				remove_filter( 'query', $filter );
			}
			self::assertSame( 0, $id );
			self::assertTrue( Capacity::transaction_active(), 'Only the outer owner may decide this transaction.' );
			// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Independent native transaction visibility is the regression under test.
			self::assertSame( '1', (string) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s", $name ) ) );
			self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s", $name ) ) );
			wc_transaction_query( 'commit' );
			self::assertSame( '1', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s", $name ) ) );
			// phpcs:enable
		} finally {
			wc_transaction_query( 'rollback' );
			$wpdb->suppress_errors( $previous );
		}
	}

	/** Both a native write callback failure and an authoritative read failure.
	 *
	 * @return array<string,array{string}>
	 */
	public static function joined_failures(): array {
		return array(
			'callback' => array( 'callback' ),
			'read'     => array( 'read' ),
		);
	}

	/** Test-owned worker folder; do not touch any shared instance or process.
	 *
	 * @return string Private temporary directory.
	 */
	private function workers_directory(): string {
		$directory = sys_get_temp_dir() . '/linker-capacity-' . self::tag();
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
		return $directory;
	}

	/** Native worker runs this exact checkout against the exclusive local DB.
	 *
	 * @param string $directory Test-owned private folder.
	 * @param string $worker Bounded fixture worker name.
	 * @return resource Native process.
	 */
	private function start_worker( string $directory, string $worker ) {
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Two owned native DB workers, no transport.
		$process = proc_open(
			array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/mail_capacity_writer.php', untrailingslashit( ABSPATH ), $directory . '/' . $worker, $directory . '/go' ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'file', $directory . '/log', 'a' ),
				2 => array( 'file', $directory . '/log', 'a' ),
			),
			$pipes
		); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Two owned native DB workers, no transport.
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		return $process;
	}

	/** Wait only for this test's deterministic ready barrier.
	 *
	 * @param string $file Native worker's ready flag.
	 */
	private function await_ready( string $file ): void {
		$deadline = microtime( true ) + 15;
		while ( ! is_file( $file ) && microtime( true ) < $deadline ) {
			usleep( 1000 );
		}
		self::assertFileExists( $file );
	}
}

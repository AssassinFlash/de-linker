<?php
/** Native one-time confirmation consumes a token only with its original durable mail job.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Tools\Genie\ConversationMail;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\RateLimit;
use Linker\Tools\Genie\Thread;

/** Native acceptance contract.
 *
 * @coversNothing
 */
final class ConversationConfirmationCapacityTest extends IntegrationTestCase {
	/** Native registry and legacy transport quota are owned only by this fixture. */
	protected function setUp(): void {
		parent::setUp();
		$before = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $before ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $before ) {
					update_option( IntakeStore::OPTION, $before, false );
				} }
		);
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false );
	}

	/** Queue-full is a proven no-handoff: zero SMTP/budget, same link then succeeds once. */
	public function test_full_queue_preserves_confirmed_link_until_one_job_is_accepted(): void {
		list( $id, $token ) = $this->source();
		$this->seed( 192 );
		$before  = self::newest_mail_job();
		$pending = get_post_meta( $id, ConversationMail::PENDING, true );
		$budget  = get_option( OptionBudgetLedger::OPTION );
		self::assertSame( 'unavailable', $this->mailer()->confirm( $token )['status'] );
		self::assertSame( $pending, get_post_meta( $id, ConversationMail::PENDING, true ) );
		self::assertFalse( metadata_exists( 'post', $id, ConversationMail::ACCEPTED ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$this->seed( 0 );
		self::assertSame( 'pending', $this->mailer()->confirm( $token )['status'] );
		$receipt = get_post_meta( $id, ConversationMail::ACCEPTED, true );
		self::assertSame( $pending['hash'], $receipt['hash'] );
		self::assertGreaterThan( $before, $receipt['job'] );
		self::assertSame( '', get_post_meta( $id, ConversationMail::PENDING, true ) );
		$job = ( new JobStore() )->load( $receipt['job'] );
		self::assertNotNull( $job );
		self::assertStringContainsString( 'Synthetic exact conversation', $job['message']->body );
		self::assertSame( array( self::TESTER ), $job['message']->to );
		self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $receipt['job'] ), Outbox::GROUP ) );
		self::assertSame( 'expired', $this->mailer()->confirm( $token )['status'] );
		self::assertSame( $receipt['job'], self::newest_mail_job() );
	}

	/** Native job, ACK, capacity and scheduler all roll back with the outer owner. */
	public function test_outer_transaction_keeps_source_and_transport_uncommitted_until_owner_decides(): void {
		list( $id, $token ) = $this->source();
		$this->seed( 0 );
		$pending = get_post_meta( $id, ConversationMail::PENDING, true );
		global $wpdb;
		$other      = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$transports = 0;
		$observe    = static function () use ( &$transports ): void {
			++$transports;
		};
		add_action( 'phpmailer_init', $observe, PHP_INT_MAX );
		$this->later(
			static function () use ( $observe, $other ): void {
				remove_action( 'phpmailer_init', $observe, PHP_INT_MAX );
				$other->close();
			}
		);
		$wpdb->query( 'START TRANSACTION' );
		try {
			self::assertSame( 'pending', $this->mailer()->confirm( $token )['status'] );
			$receipt = get_post_meta( $id, ConversationMail::ACCEPTED, true );
			self::assertTrue( Capacity::transaction_active() );
			self::assertSame( 0, $transports );
			self::assertSame( '0', $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE ID=%d", $receipt['job'] ) ) );
			self::assertSame( 0, (int) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key=%s", $id, ConversationMail::ACCEPTED ) ) );
		} finally {
			$wpdb->query( 'ROLLBACK' );
			clean_post_cache( $id );
		}
		self::assertSame( $pending, get_post_meta( $id, ConversationMail::PENDING, true ) );
		self::assertFalse( metadata_exists( 'post', $id, ConversationMail::ACCEPTED ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $receipt['job'] ), Outbox::GROUP ) );
		self::assertSame( 0, $transports );
		self::assertSame( 'pending', $this->mailer()->confirm( $token )['status'] );
	}

	/** The Tools confirmation's own first mutex cannot replay after losing its caller. */
	public function test_confirmation_first_mutex_failure_keeps_token_and_original_transaction_unpublished(): void {
		list( $id, $token ) = $this->source();
		$this->seed( 0 );
		$pending = get_post_meta( $id, ConversationMail::PENDING, true );
		$budget  = get_option( OptionBudgetLedger::OPTION );
		$before  = self::newest_mail_job();
		global $wpdb;
		$peer   = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$lock   = 'linker-conversation-mail-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $id );
		$marker = 'synthetic-confirmation-caller-' . self::tag();
		$hits   = 0;
		$kill   = static function ( string $sql ) use ( $lock, $peer, &$hits ): string {
			if ( 0 === $hits && str_contains( $sql, 'GET_LOCK(' ) && str_contains( $sql, $lock ) ) {
				++$hits;
				global $wpdb;
				$peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		$wpdb->query( 'START TRANSACTION' );
		$wpdb->insert(
			$wpdb->options,
			array(
				'option_name'  => $marker,
				'option_value' => 'caller-owned',
				'autoload'     => 'off',
			)
		);
		add_filter( 'query', $kill, 999 );
		try {
			try {
				$result = $this->mailer()->confirm( $token );
			} catch ( \Throwable $error ) {
				$result = array( 'status' => 'unavailable' );
			}
			$caller_rows = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, $marker ) );
			$new_jobs    = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE post_type=%s AND ID>%d', $wpdb->posts, JobStore::POST_TYPE, $before ) );
			$ack_rows    = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE post_id=%d AND meta_key=%s', $wpdb->postmeta, $id, ConversationMail::ACCEPTED ) );
		} finally {
			remove_filter( 'query', $kill, 999 );
			self::assertTrue( $wpdb->db_connect( false ) );
			delete_option( $marker );
			$peer->close();
			clean_post_cache( $id );
		}
		self::assertSame( 1, $hits );
		self::assertSame(
			'unavailable',
			$result['status'],
			(string) wp_json_encode(
				array(
					'status'      => $result['status'],
					'caller_rows' => $caller_rows,
					'new_jobs'    => $new_jobs,
					'ack_rows'    => $ack_rows,
				)
			)
		);
		self::assertSame( 0, $caller_rows );
		self::assertSame( 0, $new_jobs );
		self::assertSame( 0, $ack_rows );
		self::assertSame( $pending, get_post_meta( $id, ConversationMail::PENDING, true ) );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
	}

	/** Expiry, wrong token and erased native sources never create a notification. */
	public function test_expired_replaced_or_deleted_source_cannot_be_reused(): void {
		list( $id, $token ) = $this->source();
		$before             = self::newest_mail_job();
		self::assertSame( 'expired', $this->mailer()->confirm( $id . '.' . str_repeat( 'f', 64 ) )['status'] );
		$pending            = get_post_meta( $id, ConversationMail::PENDING, true );
		$pending['expires'] = time() - 1;
		update_post_meta( $id, ConversationMail::PENDING, $pending );
		self::assertSame( 'expired', $this->mailer()->confirm( $token )['status'] );
		list( $id, $token ) = $this->source();
		wp_delete_post( $id, true );
		self::assertSame( 'expired', $this->mailer()->confirm( $token )['status'] );
		self::assertNull( get_post( $id ) );
		self::assertSame( $before, self::newest_mail_job() );
	}

	/** Two independent native requests on one token can create exactly one original job. */
	public function test_two_native_confirmations_create_one_job(): void {
		list( $id, $token ) = $this->source();
		$this->seed( 0 );
		$before    = self::newest_mail_job();
		$directory = sys_get_temp_dir() . '/linker568-confirm-' . self::tag();
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
		foreach ( array( 'a', 'b' ) as $name ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Two fixture-owned local native workers, no transport.
			$worker = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/conversation_confirmation_writer.php', untrailingslashit( ABSPATH ), $directory . '/' . $name, $directory . '/go', $token ),
				array(
					0 => array( 'pipe', 'r' ),
					1 => array( 'file', $directory . '/log', 'a' ),
					2 => array( 'file', $directory . '/log', 'a' ),
				),
				$pipes
			);
			self::assertIsResource( $worker );
			fclose( $pipes[0] );
			$workers[] = $worker;
		}
		foreach ( array( 'a', 'b' ) as $name ) {
			$deadline = microtime( true ) + 15;
			while ( ! is_file( $directory . '/' . $name . '.ready' ) && microtime( true ) < $deadline ) {
				usleep( 1000 );
			}
			self::assertFileExists( $directory . '/' . $name . '.ready' );
		}
		file_put_contents( $directory . '/go', 'go' );
		foreach ( $workers as $worker ) {
			self::assertSame( 0, proc_close( $worker ) );
		}
		$results = array();
		foreach ( array( 'a', 'b' ) as $name ) {
			$results[] = json_decode( (string) file_get_contents( $directory . '/' . $name ), true )['status'];
		}
		sort( $results );
		self::assertSame( array( 'expired', 'pending' ), $results );
		clean_post_cache( $id );
		self::assertCount( 1, self::mail_jobs_after( $before ) );
		self::assertSame( '', get_post_meta( $id, ConversationMail::PENDING, true ) );
	}

	/** Native fixture return shape.
	 *
	 * @return array{int,string} Synthetic native post and its valid credential.
	 */
	private function source(): array {
		$id = wp_insert_post(
			array(
				'post_type'   => Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => 'Synthetic 568 confirmation',
			)
		);
		self::assertGreaterThan( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		update_post_meta(
			$id,
			Thread::MESSAGES,
			array(
				array(
					'role'    => 'user',
					'content' => 'Synthetic exact conversation',
				),
				array(
					'role'    => 'assistant',
					'content' => 'Synthetic answer, no provider.',
				),
			)
		);
		$secret = bin2hex( random_bytes( 32 ) );
		update_post_meta(
			$id,
			ConversationMail::PENDING,
			array(
				'hash'    => hash( 'sha256', $secret ),
				'to'      => self::TESTER,
				'locale'  => 'en',
				'expires' => time() + DAY_IN_SECONDS,
			)
		);
		return array( $id, $id . '.' . $secret );
	}

	/** Native limiter stays separate from the persistent-job assertion. */
	private function mailer(): ConversationMail {
		return new ConversationMail( new Conversations(), new Thread(), null, new RateLimit( 'synthetic568confirmation' . self::tag(), 100, DAY_IN_SECONDS ) );
	}

	/** Native fixture input.
	 *
	 * @param int $count Existing content-free ordinary occupancy.
	 */
	private function seed( int $count ): void {
		IntakeStore::edit(
			static function ( array &$state ) use ( $count ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 0; $i < $count; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
	}
}

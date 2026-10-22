<?php
/**
 * Tests for the outbox: send now, queue, retry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Producer;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Tests\Fixtures\BudgetMemory;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Error;
use WP_Mock;

/**
 * Tests for Outbox, with the real queue and throttle on an in-memory WordPress.
 *
 * @covers \Linker\Commerce\Mail\Outbox
 */
final class OutboxTest extends TestCase {

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * Post meta by post id and key.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private array $meta = array();

	/**
	 * Post status by post id.
	 *
	 * @var array<int, string>
	 */
	private array $posts = array();

	/**
	 * Scheduled attempts: [time, args].
	 *
	 * @var list<array{0: int, 1: array<int, int>}>
	 */
	private array $scheduled = array();

	/**
	 * Results of the next wp_mail() calls, in order.
	 *
	 * @var list<bool>
	 */
	private array $results = array();

	/**
	 * Messages wp_mail() delivered.
	 *
	 * @var list<array<int|string, mixed>>
	 */
	private array $delivered = array();

	/**
	 * Calls of wp_mail().
	 *
	 * @var int
	 */
	private int $calls = 0;

	/**
	 * The info lines the logger was given (one per delivery).
	 *
	 * @var list<string>
	 */
	private array $sent_lines = array();

	/**
	 * The outbox under test, set up by outbox().
	 *
	 * @var Outbox
	 */
	private Outbox $outbox;

	/**
	 * An in-memory WordPress for options, posts, the scheduler and wp_mail().
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'clean_post_cache', array( 'return' => null ) );
		$GLOBALS['wpdb']         = Mockery::mock( \wpdb::class );
		$GLOBALS['wpdb']->prefix = 'wp_';
		$GLOBALS['wpdb']->allows( 'prepare' )->andReturn( 'lock' );
		$GLOBALS['wpdb']->allows( 'get_var' )->andReturn( '1' );
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->options[ $name ] ?? $default_value ) );
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => function ( string $name, $value ): bool {
					$this->options[ $name ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'isolated-native-producer-fixture' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( string $text ): string => strip_tags( $text ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => function (): int {
					$id                 = count( $this->posts ) + 100;
					$this->posts[ $id ] = 'private';
					return $id;
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->meta[ $id ][ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => fn ( int $id, string $key ) => $this->meta[ $id ][ $key ] ?? '' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => fn ( int $id ) => isset( $this->posts[ $id ] ) ? JobStore::POST_TYPE : false ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => function ( array $post ): int {
					$this->posts[ $post['ID'] ] = $post['post_status'];
					return $post['ID'];
				},
			)
		);
		WP_Mock::userFunction(
			'wp_delete_post',
			array(
				'return' => function ( int $id ): bool {
					unset( $this->posts[ $id ], $this->meta[ $id ] );
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'as_schedule_single_action',
			array(
				'return' => function ( int $time, string $hook, array $args ): int {
					$this->scheduled[] = array( $time, $args );
					return count( $this->scheduled );
				},
			)
		);
		$this->filter_returns( 'wp_mail_from', 'sales@de-linker.com' );
		$this->filter_returns( 'wp_mail_from_name', 'Linker' );
		$this->filter_returns( 'wp_mail_content_type', 'text/html' );
		$this->filter_returns( 'wp_mail_charset', 'UTF-8' );
		WP_Mock::userFunction( 'network_home_url', array( 'return' => 'https://de-linker.com' ) );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( string $url, int $part ) => parse_url( $url, $part ) ) );
		WP_Mock::userFunction( 'get_bloginfo', array( 'return' => 'UTF-8' ) );
		// Test mode reads the switch through WordPress's own address rule.
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => str_contains( $email, '@' ) ? trim( $email ) : '' ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): string|false => 1 === preg_match( '/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/', $email ) ? $email : false ) );

		$this->outbox = new Outbox( new JobStore(), new Throttle( new BudgetMemory( $this->options ) ) );
		WP_Mock::userFunction(
			'wp_mail',
			array(
				'return' => function ( ...$args ): bool {
					++$this->calls;
					// The outbox's own call passes through its pre_wp_mail filter untouched.
					$this->assertTrue( null === $this->outbox->intercept( null, array() ) );
					$sent = array_shift( $this->results ) ?? true;
					if ( $sent ) {
						$this->delivered[] = $args;
					} else {
						$this->outbox->remember_error( new WP_Error( 'wp_mail_failed', 'Could not instantiate mail function.' ) );
					}
					return $sent;
				},
			)
		);
	}

	/**
	 * A wp_mail() call as WooCommerce makes it.
	 *
	 * @return array<string, mixed>
	 */
	private static function call(): array {
		return array(
			'to'          => 'sales@de-linker.com',
			'subject'     => 'Operational notification #20',
			'message'     => '<p>Operational notification</p>',
			'headers'     => "Content-Type: text/html\r\nBcc: a@example.test, b@example.test, c@example.test\r\n",
			'attachments' => array(),
		);
	}

	/**
	 * This component test uses an actual ordinary Woo producer context. Public
	 * inquiries are proved separately through the native bound Queue fixture.
	 */
	private function native_notification(): ?bool {
		$email     = new \WC_Email();
		$email->id = 'linker_digest';
		$send      = ( new Producer() )->woocommerce( fn () => $this->outbox->intercept( null, self::call() ), $email );
		return $send();
	}

	/** A public unclassified call has no transaction witness or send allowance. */
	public function test_unclassified_content_does_not_borrow_the_native_producer(): void {
		$this->logger( 0, 0 );
		$this->assertTrue( $this->outbox->intercept( null, self::call() ) );
		$this->assertSame( 0, $this->calls );
		$this->assertArrayNotHasKey( OptionBudgetLedger::OPTION, $this->options );
		$this->assertCount( 1, $this->posts );
	}

	/**
	 * A logger that expects the given numbers of warnings and errors.
	 *
	 * @param int $warnings Warnings.
	 * @param int $errors   Errors.
	 */
	private function logger( int $warnings, int $errors ): void {
		$logger = Mockery::mock();
		$logger->expects( 'warning' )->times( $warnings );
		$logger->expects( 'error' )->times( $errors );
		$logger->allows( 'info' )->andReturnUsing(
			function ( string $line ): void {
				$this->sent_lines[] = $line;
			}
		);
		WP_Mock::userFunction( 'wc_get_logger', array( 'return' => $logger ) );
	}

	/**
	 * A message goes out at once, once, recipients and blind copies together; nothing is queued.
	 */
	public function test_sends_at_once(): void {
		$this->logger( 0, 0 );

		$this->assertTrue( $this->native_notification() );

		$this->assertSame( 1, $this->calls );
		$this->assertSame( array( 'sales@de-linker.com' ), $this->delivered[0][0] );
		$this->assertContains( 'Bcc: a@example.test, b@example.test, c@example.test', $this->delivered[0][3] );
		$this->assertSame( array(), $this->posts );
		$this->assertCount( 1, $this->options[ OptionBudgetLedger::OPTION ]['entries'] );
		$this->assertSame(
			array( 'Email "' . self::call()['subject'] . '" sent to sales@de-linker.com, bcc a@example.test, b@example.test, c@example.test.' ),
			$this->sent_lines,
			'Every delivery leaves one line in the mail log, whichever PHP sent it.'
		);
	}

	/**
	 * Another filter's answer and the outbox's own call pass through.
	 */
	public function test_passes_through(): void {
		$this->assertFalse( $this->outbox->intercept( false, self::call() ) );
		$this->assertSame( 0, $this->calls );
	}

	/**
	 * When wp_mail() fails three times, then succeeds, the message is delivered exactly once, after
	 * retries 1, 5 and 30 minutes apart (docs/specs/11-commerce.md, acceptance "重试队列测试").
	 */
	public function test_three_failures_then_one_delivery(): void {
		$this->logger( 3, 0 );
		$this->results = array( false, false, false, true );
		$start         = time();

		$this->assertTrue( $this->native_notification() );
		$job = (int) array_key_first( $this->posts );
		for ( $retry = 1; $retry <= 3; ++$retry ) {
			$this->outbox->retry( $job );
		}

		$this->assertSame( 4, $this->calls );
		$this->assertCount( 1, $this->delivered );
		$this->assertSame( array( array( $job ), array( $job ), array( $job ) ), array_column( $this->scheduled, 1 ) );
		foreach ( array( 60, 300, 1800 ) as $i => $delay ) {
			$this->assertEqualsWithDelta( $start + $delay, $this->scheduled[ $i ][0], 2 );
		}
		$this->assertSame( array(), $this->posts, 'The delivered message leaves the queue.' );
	}

	/**
	 * After the last retry (24 hours after the 12-hour one) the message is kept as failed and logged.
	 */
	public function test_gives_up_after_the_last_retry(): void {
		$this->logger( 7, 1 );
		$this->results = array_fill( 0, 8, false );

		$this->native_notification();
		$job = (int) array_key_first( $this->posts );
		for ( $retry = 1; $retry <= 7; ++$retry ) {
			$this->outbox->retry( $job );
		}

		$this->assertSame( 8, $this->calls );
		$this->assertSame( array( 60, 300, 1800, 7200, 21600, 43200, 86400 ), Outbox::RETRY_DELAYS );
		$this->assertCount( 7, $this->scheduled );
		$this->assertSame( JobStore::FAILED_STATUS, $this->posts[ $job ] );
		$this->assertSame( 8, $this->meta[ $job ]['_linker_mail_attempts'] );
		$this->assertSame( 'Could not instantiate mail function.', $this->meta[ $job ]['_linker_mail_error'] );
	}

	/**
	 * Over the minute limit, a message waits in the queue for its slot instead of being sent.
	 */
	public function test_waits_for_the_quota(): void {
		$this->logger( 0, 0 );
		$now = time();
		unset( $this->options[ OptionBudgetLedger::OPTION ] );
		$this->options[ Throttle::OPTION ] = array_fill( 0, Throttle::PER_MINUTE, $now - 10 );

		$this->assertTrue( $this->native_notification() );

		$this->assertSame( 0, $this->calls );
		$this->assertCount( 1, $this->posts );
		$this->assertEqualsWithDelta( $now + 50, $this->scheduled[0][0], 2 );
	}

	/**
	 * Test mode rewrites the message on the way out alone: the send reaches the
	 * one test address with no copies, and a message that has to wait is queued
	 * with the recipients it came in with — the routing data the test
	 * discipline asserts on (AGENTS.md §5).
	 */
	public function test_test_mode_rewrites_at_send_time_only(): void {
		$this->logger( 0, 0 );
		$this->options[ TestMode::OPTION ] = TestMode::DEFAULT_TO;

		$this->assertTrue( $this->native_notification() );
		$this->assertSame( array( TestMode::DEFAULT_TO ), $this->delivered[0][0], 'The one recipient is the test address.' );
		$headers = (array) $this->delivered[0][3];
		$this->assertNotContains( 'Bcc: a@example.test, b@example.test, c@example.test', $headers, 'No blind copy reaches the mailer.' );
		$this->assertContains( 'Content-Type: text/html; charset=UTF-8', $headers, 'Everything else about the message stays.' );

		$now = time();
		unset( $this->options[ OptionBudgetLedger::OPTION ] );
		$this->options[ Throttle::OPTION ] = array_fill( 0, Throttle::PER_MINUTE, $now - 10 );
		$this->assertTrue( $this->native_notification() );

		$job    = (int) array_key_first( $this->posts );
		$queued = json_decode( (string) $this->meta[ $job ]['_linker_mail_message'], true );
		$this->assertSame( array( 'sales@de-linker.com' ), $queued['to'], 'The queue keeps the recipients the message came with.' );
		$this->assertContains( 'Bcc: a@example.test, b@example.test, c@example.test', $queued['headers'] );
	}

	/**
	 * A job that no longer exists is not attempted.
	 */
	public function test_retry_of_a_missing_job(): void {
		$this->outbox->retry( 999 );
		$this->assertSame( 0, $this->calls );
	}
}

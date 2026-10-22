<?php
/**
 * Native one-record asynchronous wake-up, capability isolation and wall-clock timing.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\AsyncRunner;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Outbox;
use WC_Order;

/**
 * Independent HTTP and DB consumers on a real local WordPress instance.
 *
 * @coversNothing
 */
final class AssessmentAsyncTest extends IntegrationTestCase {
	/**
	 * Captured native dispatch, without a second HTTP consumer in in-process tests.
	 *
	 * @var list<array{url: string, args: array<string, mixed>}>
	 */
	private array $dispatches = array();

	/** Restore configuration and capture only the new native loopback. */
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( Queue::ENABLED, Queue::HEARTBEAT, 'linker_genie_url' ) as $name ) {
			$old = get_option( $name );
			$this->later(
				static function () use ( $name, $old ): void {
					false === $old ? delete_option( $name ) : update_option( $name, $old );
				}
			);
		}
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		update_option( 'linker_genie_url', 'http://127.0.0.1:9' );
		add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
		$this->later(
			static function (): void {
				remove_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
			}
		);
		$http = function ( $pre, $args, $url ) {
			if ( str_contains( $url, 'action=' . AsyncRunner::ACTION ) ) {
				$this->dispatches[] = array(
					'url'  => $url,
					'args' => $args,
				);
				return array(
					'response' => array( 'code' => 200 ),
					'body'     => '',
				);
			}
			return $pre;
		};
		add_filter( 'pre_http_request', $http, 10, 3 );
		$this->later(
			static function () use ( $http ): void {
				remove_filter( 'pre_http_request', $http, 10 );
			}
		);
	}

	/** Fresh native order with a real absolute deadline, without triggering customer mail. */
	private function inquiry(): WC_Order {
		$order = wc_create_order();
		$this->assertInstanceOf( WC_Order::class, $order );
		$order->set_billing_email( self::TESTER );
		Queue::prepare( $order );
		$order->save();
		$this->retain( $order );
		return $order;
	}

	/**
	 * Remove the durable work and native record after the test.
	 *
	 * @param WC_Order $order Local record.
	 */
	private function retain( WC_Order $order ): void {
		$this->later(
			static function () use ( $order ): void {
				foreach ( array( Queue::PROCESS, Queue::EXPIRE ) as $hook ) {
					as_unschedule_all_actions( $hook, array( $order->get_id() ), Outbox::GROUP );
				}
				$order->delete( true );
			}
		);
	}

	/** One capability is persisted before dispatch, without cookies, content or service credentials. */
	public function test_native_dispatch_is_bounded_private_and_one_per_record(): void {
		$order = $this->inquiry();
		$this->assertTrue( Queue::defer( $order ) );
		$this->assertTrue( Queue::defer( $order ) );
		$this->assertCount( 1, $this->dispatches );
		$request = $this->dispatches[0];
		$this->assertSame( admin_url( 'admin-ajax.php' ) . '?action=' . AsyncRunner::ACTION, $request['url'] );
		$args = $request['args'];
		$this->assertFalse( $args['blocking'] );
		$this->assertSame( 0.01, $args['timeout'] );
		$this->assertSame( 0, $args['redirection'] );
		$this->assertTrue( $args['sslverify'] );
		$this->assertSame( array(), $args['cookies'] );
		$this->assertSame( array( 'inquiry', 'token' ), array_keys( $args['body'] ) );
		$this->assertSame( $order->get_id(), $args['body']['inquiry'] );
		$this->assertMatchesRegularExpression( '/\A[a-f0-9]{64}\z/D', $args['body']['token'] );
		$order->read_meta_data( true );
		$wake = $order->get_meta( AsyncRunner::META );
		$this->assertSame( hash( 'sha256', $args['body']['token'] ), $wake['hash'] );
		$this->assertSame( Queue::data( $order )['deadline'], $wake['expires'] );
		$this->assertStringNotContainsString( $args['body']['token'], (string) wp_json_encode( $wake ) );
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::PROCESS, array( $order->get_id() ), Outbox::GROUP ) );
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::EXPIRE, array( $order->get_id() ), Outbox::GROUP ) );
	}

	/** Missing, forged, cross-record, replayed, expired and held requests do no provider work. */
	public function test_one_use_capability_rejects_every_invalid_scope_and_preserves_hold(): void {
		$order = $this->inquiry();
		$other = $this->inquiry();
		Queue::defer( $order );
		$token  = $this->dispatches[0]['args']['body']['token'];
		$runner = new AsyncRunner();
		$this->assertFalse( $runner->run( $order->get_id(), '' ) );
		$this->assertFalse( $runner->run( $order->get_id(), str_repeat( 'a', 64 ) ) );
		$this->assertFalse( $runner->run( $other->get_id(), $token ) );
		$this->assertFalse( $runner->run( PHP_INT_MAX, $token ) );
		$count    = 0;
		$provider = static function ( $pre, $args, $url ) use ( &$count ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				++$count;
				return array(
					'response' => array( 'code' => 200 ),
					'body'     => wp_json_encode( Result::unknown( 'provider_budget_quota' ) ),
				);
			}
			return $pre;
		};
		add_filter( 'pre_http_request', $provider, 10, 3 );
		$this->later(
			static function () use ( $provider ): void {
				remove_filter( 'pre_http_request', $provider, 10 );
			}
		);
		$this->assertTrue( $runner->run( $order->get_id(), $token ) );
		$this->assertFalse( $runner->run( $order->get_id(), $token ) );
		$this->assertSame( 1, $count );
		$order->read_meta_data( true );
		$this->assertSame( 'provider_budget_quota', Queue::data( $order )['initial_result']['reason'] );
		$this->assertGreaterThan( 0, Queue::data( $order )['notification_job'] );
		Queue::defer( $other );
		$second = $this->dispatches[1]['args']['body']['token'];
		$other->update_meta_data( NotificationHold::META, array( 'reason' => 'synthetic' ) );
		$other->save_meta_data();
		$this->assertFalse( $runner->run( $other->get_id(), $second ) );
		( new Queue() )->process( $other->get_id() );
		$this->assertSame( 1, $count );
		$this->assertSame( 0, Queue::data( $other )['notification_job'] );
		$other->delete_meta_data( NotificationHold::META );
		$data             = Queue::data( $other );
		$data['deadline'] = microtime( true ) - 1;
		StructuredMeta::update( $other, Queue::META, $data );
		$other->save_meta_data();
		$this->assertFalse( $runner->run( $other->get_id(), $second ) );
		( new Queue() )->recover();
		$other->read_meta_data( true );
		$this->assertSame( 'deadline', Queue::data( $other )['initial_result']['reason'] );
		$this->assertGreaterThan( 0, Queue::data( $other )['notification_job'] );
		$this->assertSame( 1, $count );
	}

	/** Two actual connections cannot replay one wake-up; a busy dedicated worker does not wait. */
	public function test_real_db_connections_claim_once_and_busy_worker_retains_recovery(): void {
		$order = $this->inquiry();
		Queue::defer( $order );
		$token   = $this->dispatches[0]['args']['body']['token'];
		$barrier = tempnam( sys_get_temp_dir(), 'linker-543-' );
		$this->assertIsString( $barrier );
		$this->later(
			static function () use ( $barrier ): void {
				unlink( $barrier );
			}
		);
		$first = $this->worker( $order->get_id(), $token, $barrier );
		$until = microtime( true ) + 6;
		while ( '' === file_get_contents( $barrier ) && microtime( true ) < $until ) {
			usleep( 10000 ); }
		$this->assertSame( "called\n", file_get_contents( $barrier ) );
		$second = $this->worker( $order->get_id(), $token, $barrier );
		$this->assertSame( 'refused', $this->close_worker( $second ) );
		$this->assertSame( 'claimed', $this->close_worker( $first ) );
		$this->assertSame( "called\n", file_get_contents( $barrier ) );
		$order->read_meta_data( true );
		$this->assertGreaterThan( 0, Queue::data( $order )['notification_job'] );
		$other = $this->inquiry();
		Queue::defer( $other );
		$token = $this->dispatches[1]['args']['body']['token'];
		file_put_contents( $barrier, '' );
		$busy  = $this->worker( $other->get_id(), $token, $barrier, 'busy' );
		$until = microtime( true ) + 6;
		while ( '' === file_get_contents( $barrier ) && microtime( true ) < $until ) {
			usleep( 10000 ); }
		$this->assertSame( 'busy', file_get_contents( $barrier ) );
		$start = microtime( true );
		$this->assertTrue( ( new AsyncRunner() )->run( $other->get_id(), $token ) );
		$this->assertLessThan( 1, microtime( true ) - $start );
		$other->read_meta_data( true );
		$this->assertSame( 'busy', $other->get_meta( AsyncRunner::META )['status'] );
		$this->assertSame( 0, Queue::data( $other )['notification_job'] );
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::EXPIRE, array( $other->get_id() ), Outbox::GROUP ) );
		$this->assertSame( '', $this->close_worker( $busy ) );
	}

	/**
	 * Launch a real independent PHP/database connection.
	 *
	 * @param int    $id Local inquiry.
	 * @param string $token Local one-use capability.
	 * @param string $barrier Local synchronization file.
	 * @param string $mode Run or hold dedicated worker.
	 * @return array{resource, array<int, resource>} Child and pipes.
	 */
	private function worker( int $id, string $token, string $barrier, string $mode = 'run' ): array {
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Real connection race, not a mocked lock.
		$process = proc_open(
			array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/assessment_async_worker.php', (string) $id, $token, $barrier, $mode ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		$this->assertIsResource( $process );
		fclose( $pipes[0] );
		unset( $pipes[0] );
		return array( $process, $pipes );
	}

	/**
	 * Join one native worker.
	 *
	 * @param array{resource, array<int, resource>} $worker Child and pipes.
	 */
	private function close_worker( array $worker ): string {
		[ $process, $pipes ] = $worker;
		$out                 = stream_get_contents( $pipes[1] );
		$error               = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		$this->assertSame( 0, proc_close( $process ), $error );
		return $out;
	}

	/**
	 * Reload after a separate HTTP/database connection may have committed.
	 *
	 * @param WC_Order $order Local record.
	 * @return array<string, mixed> Current persisted assessment.
	 */
	private function fresh_data( WC_Order $order ): array {
		$order->read_meta_data( true );
		return Queue::data( $order );
	}

	/**
	 * Install a guarded fixture only into this local WordPress process's instance.
	 */
	private function http_fixture(): string {
		$path = WPMU_PLUGIN_DIR . '/999-linker-assessment-http-fixture.php';
		$this->assertFileDoesNotExist( $path );
		$secret = bin2hex( random_bytes( 24 ) );
		$source = dirname( __DIR__, 2 ) . '/fixtures/assessment_http.php';
		// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- PHP literal for an ephemeral local fixture, not debug output.
		file_put_contents( $path, '<?php define("LINKER_ASSESSMENT_HTTP_FIXTURE", ' . var_export( $secret, true ) . '); require ' . var_export( $source, true ) . ';' );
		$this->later(
			static function () use ( $path ): void {
				unlink( $path );
			}
		);
		return $secret;
	}

	/** Real admin-ajax rejects forged, missing and replayed capabilities before work. */
	public function test_real_http_authorization_and_replay(): void {
		$this->http_fixture();
		$order = $this->inquiry();
		$other = $this->inquiry();
		Queue::defer( $order );
		$token = $this->dispatches[0]['args']['body']['token'];
		$url   = admin_url( 'admin-ajax.php' );
		foreach ( array(
			array(),
			array(
				'inquiry' => $order->get_id(),
				'token'   => str_repeat( '0', 64 ),
			),
			array(
				'inquiry' => $other->get_id(),
				'token'   => $token,
			),
			array(
				'inquiry' => array( 'bad' ),
				'token'   => $token,
			),
			array(
				'inquiry' => $order->get_id(),
				'token'   => array( $token ),
			),
		) as $body ) {
			$response = wp_remote_post( $url, array( 'body' => array_merge( array( 'action' => AsyncRunner::ACTION ), $body ) ) );
			$this->assertSame( 403, wp_remote_retrieve_response_code( $response ) );
			$order->read_meta_data( true );
			$this->assertSame( 0, Queue::data( $order )['notification_job'] );
		}
		$response = wp_remote_post(
			$url,
			array(
				'body' => array(
					'action'  => AsyncRunner::ACTION,
					'inquiry' => $order->get_id(),
					'token'   => $token,
				),
			)
		);
		$this->assertSame( 202, wp_remote_retrieve_response_code( $response ) );
		$this->assertSame( '', wp_remote_retrieve_body( $response ) );
		$until = microtime( true ) + 4;
		do {
			$order->read_meta_data( true );
			$data = $this->fresh_data( $order );
			usleep( 10000 );
		} while ( 0 === (int) $data['notification_job'] && microtime( true ) < $until );
		$this->assertGreaterThan( 0, $data['notification_job'] );
		$this->assertSame( 'service_unavailable', $data['initial_result']['reason'] );
		$response = wp_remote_post(
			$url,
			array(
				'body' => array(
					'action'  => AsyncRunner::ACTION,
					'inquiry' => $order->get_id(),
					'token'   => $token,
				),
			)
		);
		$this->assertSame( 403, wp_remote_retrieve_response_code( $response ) );
		$order->read_meta_data( true );
		$this->assertSame( $data['notification_job'], Queue::data( $order )['notification_job'] );
	}

	/** A refused loopback leaves the original durable expiry and ordinary unknown notice. */
	public function test_failed_loopback_keeps_original_durable_recovery(): void {
		$order    = $this->inquiry();
		$deadline = Queue::data( $order )['deadline'];
		$fail     = static function ( $pre, $args, $url ) {
			return str_contains( $url, 'action=' . AsyncRunner::ACTION ) ? new \WP_Error( 'fixture_loopback_failure' ) : $pre;
		};
		add_filter( 'pre_http_request', $fail, 20, 3 );
		try {
			Queue::defer( $order );
		} finally {
			remove_filter( 'pre_http_request', $fail, 20 ); }
		$order->read_meta_data( true );
		$this->assertSame( 'failed', $order->get_meta( AsyncRunner::META )['dispatch'] );
		$this->assertSame( $deadline, Queue::data( $order )['deadline'] );
		$this->assertSame( 'yes', $order->get_meta( Queue::PENDING ) );
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::EXPIRE, array( $order->get_id() ), Outbox::GROUP ) );
		$data             = $this->fresh_data( $order );
		$data['deadline'] = microtime( true ) - 1;
		StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
		( new Queue() )->expire( $order->get_id() );
		$order->read_meta_data( true );
		$this->assertSame( 'deadline', Queue::data( $order )['initial_result']['reason'] );
		$this->assertGreaterThan( 0, Queue::data( $order )['notification_job'] );
	}

	/**
	 * Closing the customer's TCP connection preserves the already saved work.
	 *
	 * @throws \RuntimeException The fixture requires an actual local HTTP URL.
	 */
	public function test_disconnected_http_client_still_finishes_saved_assessment(): void {
		$secret = $this->http_fixture();
		$tag    = strtolower( wp_generate_password( 12, false ) );
		$key    = 'linker_assessment_fixture_' . $tag;
		$record = 'linker_assessment_fixture_order_' . $tag;
		$this->later(
			static function () use ( $key, $record ): void {
				delete_option( $key );
				delete_option( $record );
			}
		);
		$url = wp_parse_url( admin_url( 'admin-ajax.php' ) );
		if ( ! is_array( $url ) || ! isset( $url['scheme'], $url['host'], $url['port'], $url['path'] ) ) {
			throw new \RuntimeException( 'Local HTTP fixture needs a complete loopback URL.' );
		}
		$this->assertSame( 'http', $url['scheme'] );
		$this->assertContains( $url['host'], array( '127.0.0.1', 'localhost' ) );
		$body   = http_build_query(
			array(
				'action'  => 'linker_assessment_fixture',
				'fixture' => $secret,
				'tag'     => $tag,
				'delay'   => 2,
			)
		);
		$socket = stream_socket_client( 'tcp://' . $url['host'] . ':' . $url['port'], $error, $message, 5 );
		$this->assertIsResource( $socket, $message ?? '' );
		$request = 'POST ' . $url['path'] . " HTTP/1.1\r\nHost: " . $url['host'] . ':' . $url['port'] . "\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: " . strlen( $body ) . "\r\nConnection: close\r\n\r\n" . $body;
		$this->assertSame( strlen( $request ), fwrite( $socket, $request ) );
		$until = microtime( true ) + 8;
		do {
			wp_cache_delete( $record, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			$id = (int) get_option( $record, 0 );
			usleep( 10000 );
		} while ( 0 === $id && microtime( true ) < $until );
		// Disconnect only after durable acceptance, without waiting for any response.
		fclose( $socket );
		$order = wc_get_order( $id );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->retain( $order );
		do {
			$order->read_meta_data( true );
			$data = $this->fresh_data( $order );
			usleep( 20000 );
		} while ( 0 === (int) $data['notification_job'] && microtime( true ) < $until );
		$this->assertSame( 'normal', $data['initial_result']['label'] );
		$this->assertGreaterThan( 0, $data['notification_job'] );
		$this->assertLessThan( $data['deadline'], $data['completed_at'] );
	}

	/** Real HTTP responses precede the end of actual 2/8-second background PHP work. */
	public function test_real_http_submit_does_not_wait_for_two_or_eight_second_classification(): void {
		$secret = $this->http_fixture();
		foreach ( array( 2, 8 ) as $delay ) {
			$tag = strtolower( wp_generate_password( 12, false ) );
			$key = 'linker_assessment_fixture_' . $tag;
			$this->later(
				static function () use ( $key, $tag ): void {
					delete_option( $key );
					delete_option( 'linker_assessment_fixture_order_' . $tag );
				}
			);
			$start    = microtime( true );
			$response = wp_remote_post(
				admin_url( 'admin-ajax.php?action=linker_assessment_fixture' ),
				array(
					'timeout' => 15,
					'body'    => array(
						'fixture' => $secret,
						'tag'     => $tag,
						'delay'   => $delay,
					),
				)
			);
			$received = microtime( true );
			$this->assertFalse( is_wp_error( $response ), is_wp_error( $response ) ? $response->get_error_message() : '' );
			$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
			$body = json_decode( wp_remote_retrieve_body( $response ), true );
			$this->assertIsArray( $body, wp_remote_retrieve_body( $response ) );
			$order = wc_get_order( (int) $body['id'] );
			$this->assertInstanceOf( WC_Order::class, $order );
			$this->retain( $order );
			$until = microtime( true ) + 12;
			do {
				wp_cache_delete( $key, 'options' );
				$event = get_option( $key );
				usleep( 20000 );
			} while ( ( ! is_array( $event ) || ! isset( $event['completed_at'] ) ) && microtime( true ) < $until );
			$this->assertIsArray( $event );
			$this->assertArrayHasKey( 'completed_at', $event );
			$this->assertLessThan( $event['completed_at'], $received );
			$this->assertLessThan( $delay, $body['responding_at'] - $body['defer_at'] );
			$this->assertGreaterThanOrEqual( $delay, $event['completed_at'] - $event['started_at'] );
			$this->assertNotSame( getmypid(), $event['pid'] );
			do {
				$order->read_meta_data( true );
				$data = $this->fresh_data( $order );
				usleep( 10000 );
			} while ( 0 === (int) $data['notification_job'] && microtime( true ) < $until );
			fwrite(
				STDOUT,
				(string) wp_json_encode(
					array(
						'simulated_seconds' => $delay,
						'client_seconds'    => $received - $start,
						'defer_seconds'     => $body['responding_at'] - $body['defer_at'],
						'queue_seconds'     => $data['result']['queue_seconds'] ?? null,
						'elapsed'           => $data['elapsed'] ?? null,
					)
				) . PHP_EOL
			);
			$this->assertLessThan( $data['deadline'], $event['started_at'] );
			$this->assertSame( 'normal', $data['initial_result']['label'] );
			$this->assertSame( (float) $delay, $data['initial_result']['seconds'] );
			$this->assertGreaterThan( 0, $data['notification_job'] );
			$this->assertLessThan( Queue::WAIT_SECONDS, $data['result']['queue_seconds'] );
		}
	}
}

<?php
/**
 * Real Woo inquiry, asynchronous label and durable notification chain.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Assessment\Admin;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Mail\JobStore;
use WC_Order;

/**
 * The real inquiry and Outbox lifecycle.
 *
 * @coversNothing
 */
final class InquiryAssessmentTest extends IntegrationTestCase {
	/** Enable only this test's feature and restore all touched configuration. */
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( Queue::ENABLED, Queue::HEARTBEAT, 'linker_genie_url' ) as $name ) {
			$value = get_option( $name );
			$this->later(
				static function () use ( $name, $value ): void {
					false === $value ? delete_option( $name ) : update_option( $name, $value );
				}
			);
		}
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		update_option( 'linker_genie_url', 'http://127.0.0.1:9212' );
		add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
		$this->later(
			static function (): void {
				remove_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
			}
		);
	}

	/**
	 * A received inquiry, restored along with its scheduled task arguments.
	 *
	 * @param array<string, string> $fields Synthetic submission overrides.
	 */
	private function inquiry( array $fields = array() ): WC_Order {
		$details = Submission::from_post(
			array_merge(
				array(
					'name'    => 'Synthetic Alex',
					'email'   => self::TESTER,
					'company' => 'Example Solar',
					'message' => 'Please contact us about project equipment.',
					'consent' => '1',
					'lang'    => 'en',
				),
				$fields
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$id    = $order->get_id();
		$this->later(
			static function () use ( $id ): void {
				as_unschedule_all_actions( Queue::PROCESS, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP );
				as_unschedule_all_actions( Queue::EXPIRE, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP );
				$record = wc_get_order( $id );
				if ( $record instanceof WC_Order ) {
					$record->delete( true );
				}
			}
		);
		return $order;
	}

	/** Fraud outside the message field remains in the frozen provider input. */
	public function test_fraud_in_name_is_sent_with_gibberish_body(): void {
		$name  = 'Вам перевод 195753 руб. забрать тут https://reward.example.invalid/test';
		$order = $this->inquiry(
			array(
				'name'    => $name,
				'message' => 'THRT332399MTGJNF KSDJFKSDJF',
			)
		);
		// Subsequent edits cannot replace the accepted evidence.
		$order->set_billing_first_name( 'Later edit' );
		$order->save();
		$seen  = false;
		$fetch = static function ( $pre, $args, $url ) use ( $name, &$seen ) {
			if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
				return $pre;
			}
			$seen = true;
			$body = json_decode( $args['body'], true );
			self::assertSame( $name, $body['state']['submission']['billing']['first_name'] );
			self::assertSame( 'THRT332399MTGJNF KSDJFKSDJF', $body['state']['submission']['message'] );
			self::assertSame( 'not_present', $body['state']['context']['status'] );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode( self::result( 'suspected_spam', 'fraud_or_phishing' ) ),
			);
		};
		add_filter( 'pre_http_request', $fetch, 10, 3 );
		$this->later(
			static function () use ( $fetch ): void {
				remove_filter( 'pre_http_request', $fetch, 10 );
			}
		);
		( new Queue() )->process( $order->get_id() );
		$this->assertTrue( $seen );
		$order->read_meta_data( true );
		$this->assertSame( 'suspected_spam', Queue::data( $order )['initial_result']['label'] );
	}

	/**
	 * Model-shaped service output; no real model or email call is made.
	 *
	 * @param string $label Raw label.
	 * @param string $basis Fixed basis.
	 * @return array<string, mixed>
	 */
	private static function result( string $label = 'normal', string $basis = 'business_request' ): array {
		return array(
			'label'   => $label,
			'basis'   => $basis,
			'reason'  => 'classified',
			'model'   => 'typesafe/jev-1.13-20260917',
			'rubric'  => Result::RUBRIC,
			'raw'     => array(
				'classification' => array(
					'type'   => 'choice',
					'choice' => $label,
				),
				'basis'          => array(
					'type'   => 'choice',
					'choice' => $basis,
				),
			),
			'seconds' => 0.1,
		);
	}

	/** Submission persists and returns without any service call or team mail. */
	public function test_submit_never_waits_for_the_model_and_receipt_is_not_replayed(): void {
		$calls = 0;
		$fetch = static function ( $pre, $args, $url ) use ( &$calls ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				++$calls;
				return new \WP_Error( 'deliberately_slow_provider' );
			}
			return $pre;
		};
		add_filter( 'pre_http_request', $fetch, 10, 3 );
		$this->later(
			static function () use ( $fetch ): void {
				remove_filter( 'pre_http_request', $fetch, 10 );
			}
		);
		$marker = self::newest_mail_job();
		$order  = $this->inquiry();
		$this->assertSame( 0, $calls, 'The customer submission cannot invoke the classifier.' );
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertCount( 1, self::mail_jobs_after( $marker ), 'Only the customer receipt exists before background work.' );
		$data = Queue::data( $order );
		$this->assertEqualsWithDelta( Queue::WAIT_SECONDS, $data['deadline'] - $data['accepted_at'], .001 );
		( new Queue() )->process( $order->get_id() );
		$this->assertSame( 1, $calls );
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertSame( 'uncertain', $data['initial_result']['label'] );
		$this->assertSame( 'service_unavailable', $data['initial_result']['reason'] );
		$this->assertGreaterThanOrEqual( $data['accepted_at'], $data['result']['started_at'] );
		$this->assertGreaterThanOrEqual( 0, $data['result']['queue_seconds'] );
		$this->assertCount( 2, self::mail_jobs_after( $marker ) );
		( new Queue() )->process( $order->get_id() );
		( new Queue() )->expire( $order->get_id() );
		$this->assertSame( 1, $calls );
		$this->assertCount( 2, self::mail_jobs_after( $marker ), 'Retries cannot generate a second team message or receipt.' );
	}

	/**
	 * All labels notify; a conflict cannot be displayed as a spam conclusion.
	 *
	 * @dataProvider observations
	 * @param string $label Service label.
	 * @param string $basis Fixed basis.
	 * @param string $expected Safe stored label.
	 */
	public function test_every_observation_is_notified_once( string $label, string $basis, string $expected ): void {
		$fetch = static function ( $pre, $args, $url ) use ( $label, $basis ) {
			if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
				return $pre;
			}
			$body = json_decode( $args['body'], true );
			self::assertLessThanOrEqual( 10, $args['timeout'] );
			self::assertLessThanOrEqual( 10, $body['remaining_seconds'] );
			self::assertSame( 'Synthetic Alex', $body['state']['submission']['billing']['first_name'] );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode( self::result( $label, $basis ) ),
			);
		};
		add_filter( 'pre_http_request', $fetch, 10, 3 );
		$this->later(
			static function () use ( $fetch ): void {
				remove_filter( 'pre_http_request', $fetch, 10 );
			}
		);
		$order = $this->inquiry();
		$queue = new Queue();
		$queue->process( $order->get_id() );
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertSame( $expected, $data['initial_result']['label'] );
		$this->assertGreaterThan( 0, $data['notification_job'] );
		$job = ( new JobStore() )->load( $data['notification_job'] );
		$this->assertNotNull( $job );
		$this->assertSame( array( 'sales@sunriverinverter.com' ), $job['message']->to );
		$this->assertStringContainsString( Result::label( $expected ), $job['message']->body );
		$this->assertStringContainsString( 'Please contact us about project equipment.', $job['message']->body );
		$queue->finish( $order->get_id(), Result::validate( self::result( 'suspected_spam', 'fraud_or_phishing' ) ) );
		$order->read_meta_data( true );
		$this->assertSame( $data['notification_job'], Queue::data( $order )['notification_job'] );
		$after = ( new JobStore() )->load( $data['notification_job'] );
		$this->assertNotNull( $after );
		$this->assertSame( $job['message']->body, $after['message']->body );
	}

	/**
	 * Labels and a real observed contradiction.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public static function observations(): array {
		return array(
			'normal'        => array( 'normal', 'business_request', 'normal' ),
			'spam'          => array( 'suspected_spam', 'fraud_or_phishing', 'suspected_spam' ),
			'uncertain'     => array( 'uncertain', 'insufficient_context', 'uncertain' ),
			'contradiction' => array( 'normal', 'unsolicited_bulk_promotion', 'uncertain' ),
		);
	}

	/** A late-starting task spends no fresh model budget, including zero traffic recovery. */
	public function test_expired_task_is_released_by_independent_recovery_and_late_results_do_not_resend(): void {
		$order               = $this->inquiry();
		$data                = Queue::data( $order );
		$data['accepted_at'] = microtime( true ) - 20;
		$data['deadline']    = microtime( true ) - 10;
		$order->update_meta_data( Queue::META, $data );
		$order->save_meta_data();
		$queue = new Queue();
		$queue->recover();
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertSame( 'deadline', $data['initial_result']['reason'] );
		$job = $data['notification_job'];
		$queue->finish( $order->get_id(), Result::validate( self::result() ) );
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertSame( $job, $data['notification_job'] );
		$this->assertSame( 'deadline', $data['initial_result']['reason'] );
		$this->assertSame( 'normal', $data['late_result']['label'] );
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( '', $order->get_meta( Admin::OVERRIDE ) );
	}

	/** No recovery heartbeat must use normal notification without any model call. */
	public function test_missing_recovery_does_not_hold_the_notification(): void {
		delete_option( Queue::HEARTBEAT );
		$order = $this->inquiry();
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertSame( 'recovery_unavailable', $data['initial_result']['reason'] );
		$this->assertGreaterThan( 0, $data['notification_job'] );
		$this->assertNotNull( ( new JobStore() )->load( $data['notification_job'] ) );
	}

	/** A partially persisted Outbox job must roll back and remain recoverable. */
	public function test_failed_mail_meta_write_stays_pending_until_recovery(): void {
		$order  = $this->inquiry();
		$marker = self::newest_mail_job();
		$deny   = static function ( $check, $id, $key ) {
			return '_linker_mail_message' === $key ? false : $check;
		};
		add_filter( 'add_post_metadata', $deny, 10, 3 );
		add_filter( 'update_post_metadata', $deny, 10, 3 );
		try {
			( new Queue() )->finish( $order->get_id(), self::result() );
		} finally {
			remove_filter( 'add_post_metadata', $deny, 10 );
			remove_filter( 'update_post_metadata', $deny, 10 );
		}
		$order->read_meta_data( true );
		$this->assertSame( 0, Queue::data( $order )['notification_job'] );
		$this->assertSame( 'yes', $order->get_meta( Queue::PENDING ) );
		$this->assertSame( array(), self::mail_jobs_after( $marker ), 'A partial job is rolled back.' );
		$data             = Queue::data( $order );
		$data['deadline'] = microtime( true ) - 1;
		$order->update_meta_data( Queue::META, $data );
		$order->save_meta_data();
		( new Queue() )->recover();
		$order->read_meta_data( true );
		$this->assertGreaterThan( 0, Queue::data( $order )['notification_job'] );
		$this->assertCount( 1, self::mail_jobs_after( $marker ) );
	}

	/** Snapshot the owned retained transcript/readings and never another account's. */
	public function test_owned_full_context_is_frozen_and_foreign_context_is_unavailable(): void {
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		$id = wp_insert_post(
			array(
				'post_type'   => \Linker\Tools\Genie\Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_author' => $customer->get_id(),
				'post_title'  => 'Synthetic project',
			)
		);
		$this->assertGreaterThan( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		update_post_meta(
			$id,
			\Linker\Tools\Genie\Thread::MESSAGES,
			array(
				array(
					'role'    => 'user',
					'content' => 'Please check the complete project file.',
				),
			)
		);
		update_post_meta(
			$id,
			\Linker\Tools\Genie\Thread::READINGS,
			array(
				array(
					'id'   => 'synthetic-file',
					'text' => str_repeat( 'Engineering requirement. ', 1000 ),
				),
			)
		);
		$order    = $this->inquiry();
		$snapshot = \Linker\Commerce\Inquiry\Assessment\Snapshot::make( $order, array( 'conversation' => $id ) );
		$this->assertSame( 'available', $snapshot['context']['status'] );
		$this->assertSame( 'Please check the complete project file.', $snapshot['context']['conversation'][0]['content'] );
		$this->assertSame( str_repeat( 'Engineering requirement. ', 1000 ), $snapshot['context']['attachments'][0]['text'] );
		$this->assertNotEmpty( $snapshot['account']['registration'] );
		// Account ownership alone does not make an old conversation relevant.
		$unlinked = ( new \Linker\Tools\Genie\InquiryAssessmentContext() )->read( array(), array(), false );
		$this->assertSame( 'not_present', $unlinked['status'] );
		$this->as_user( 0 );
		$foreign = \Linker\Commerce\Inquiry\Assessment\Snapshot::make( $order, array( 'conversation' => $id ) );
		$this->assertSame( 'unavailable', $foreign['context']['status'] );
		$this->assertSame( array(), $foreign['context']['conversation'] );
	}

	/** A dead connection releases its lock; two connections generate only one job. */
	public function test_real_worker_crash_and_concurrent_release_recover_one_logical_message(): void {
		$order   = $this->inquiry();
		$barrier = tempnam( sys_get_temp_dir(), 'linker-511-' );
		$this->assertIsString( $barrier );
		$this->later(
			static function () use ( $barrier ): void {
				if ( file_exists( $barrier ) ) {
					unlink( $barrier );
				} }
		);
		$fixture = dirname( __DIR__, 2 ) . '/fixtures/inquiry_assessment_worker.php';
		$start   = static function ( string $mode ) use ( $fixture, $order, $barrier ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- The fixture needs two independent local PHP/DB connections.
			$process = proc_open(
				// Match the integration suite's memory budget when loading real Woo mailers.
				array( PHP_BINARY, '-d', 'memory_limit=2048M', $fixture, (string) $order->get_id(), $barrier, $mode ),
				array(
					0 => array( 'pipe', 'r' ),
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes
			);
			self::assertIsResource( $process );
			fclose( $pipes[0] );
			unset( $pipes[0] );
			return array( $process, $pipes );
		};
		/**
		 * Close a local worker and assert its exit.
		 *
		 * @param array{resource, array<int, resource>} $worker Worker and pipes.
		 */
		$close = static function ( array $worker ): void {
			[ $process, $pipes ] = $worker;
			$output              = stream_get_contents( $pipes[1] ) . stream_get_contents( $pipes[2] );
			fclose( $pipes[1] );
			fclose( $pipes[2] );
			self::assertSame( 0, proc_close( $process ), $output );
		};
		$close( $start( 'crash' ) );
		$this->assertSame( 'locked', file_get_contents( $barrier ) );
		file_put_contents( $barrier, '' );
		$first = $start( 'hold' );
		$until = microtime( true ) + 5;
		while ( '' === file_get_contents( $barrier ) && microtime( true ) < $until ) {
			usleep( 10000 );
		}
		$this->assertSame( 'locked', file_get_contents( $barrier ) );
		$second = $start( 'finish' );
		$close( $second );
		$close( $first );
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		$this->assertGreaterThan( 0, $data['notification_job'] );
		$job = $data['notification_job'];
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::FINISH, array( $order->get_id(), self::result() ), \Linker\Commerce\Mail\Outbox::GROUP ), 'A competing connection must persist its retry.' );
		( new Queue() )->finish( $order->get_id(), self::result() );
		$order->read_meta_data( true );
		$this->assertSame( $job, Queue::data( $order )['notification_job'] );
		as_unschedule_all_actions( Queue::FINISH, array( $order->get_id(), self::result() ), \Linker\Commerce\Mail\Outbox::GROUP );
	}
}

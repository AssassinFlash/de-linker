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
use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\SendAuthorization;
use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Mail\JobStore;
use WC_Order;

/**
 * The real inquiry and Outbox lifecycle.
 *
 * @coversNothing
 */
final class InquiryAssessmentTest extends IntegrationTestCase {
	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;
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
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
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
		$this->assertInstanceOf( WC_Order::class, $order );
		$id = $order->get_id();
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

	/** A long queue wait is recovered without consuming the actual model window. */
	public function test_native_minute_recovery_event_releases_without_a_visitor(): void {
		$order               = $this->inquiry();
		$data                = Queue::data( $order );
		$data['accepted_at'] = microtime( true ) - 300;
		$data['deadline']    = $data['accepted_at'] + Queue::WAIT_SECONDS;
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
		$budget   = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		$schedule = \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::class;
		$this->assertTrue( wp_schedule_event( time(), $schedule::INTERVAL, $schedule::HOOK ) );
		$this->later(
			static function () use ( $schedule ): void {
				wp_clear_scheduled_hook( $schedule::HOOK );
			}
		);
		$event = wp_get_scheduled_event( $schedule::HOOK );
		$this->assertIsObject( $event );
		$this->assertSame( 60, $event->interval );
		$this->assertSame( $schedule::HOOK, $event->hook );
		do_action_ref_array( $schedule::HOOK, $event->args ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Fixed registered native minute recovery hook.
		$this->assertLessThan( 2, microtime( true ) - (float) get_option( Queue::HEARTBEAT ) );
		NormalMailAuthorizationFixture::consume( Queue::PROCESS, $order->get_id() );
		$order->read_meta_data( true );
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		$this->assertSame( 'normal', $state['status'] );
		$this->assertSame( 'normal', $state['verdict']['decision'] );
		$this->assertCount( 2, $state['jobs'] );
		$this->assertSame( $data['accepted_at'], Queue::data( $order )['accepted_at'] );
		$this->assertGreaterThan( 9.0, $this->authorization->requests[0]['remaining_seconds'] );
		$this->assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
	}

	/** Product inquiry evidence exists at Woo's first native order save. */
	public function test_product_inquiry_has_evidence_before_first_native_save(): void {
		$this->as_user( 0 );
		WC()->cart->empty_cart();
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic first save',
				'email'   => self::TESTER,
				'message' => 'First native save evidence',
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$first = null;
		$watch = static function ( $order ) use ( &$first ): void {
			if ( $order instanceof WC_Order && 0 === $order->get_id() && self::TESTER === $order->get_billing_email() ) {
				$first = array(
					'data'    => Queue::data( $order ),
					'pending' => $order->get_meta( Queue::PENDING ),
					'source'  => $order->get_meta( '_linker_inquiry_source' ),
				);
			}
		};
		add_action( 'woocommerce_before_order_object_save', $watch, 100 );
		try {
			$order = ( new Sender() )->request( $details, array(), false );
		} finally {
			remove_action( 'woocommerce_before_order_object_save', $watch, 100 );
		}
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertIsArray( $first );
		$this->assertSame( 'yes', $first['pending'] );
		$this->assertSame( 'proforma', $first['source'] );
		$this->assertSame( 'First native save evidence', $first['data']['snapshot']['submission']['message'] );
		$this->assertSame( Queue::data( $order )['accepted_at'], $first['data']['accepted_at'] );
	}

	/** Actual service budget refusals retain their diagnostic with no content notification. */
	public function test_provider_budget_failures_survive_client_and_notice(): void {
		foreach ( array( 'quota', 'unavailable', 'configuration' ) as $reason ) {
			$order             = $this->inquiry();
			$result            = \Linker\Commerce\Inquiry\Assessment\SendVerdict::unknown( 'provider_budget_' . $reason );
			$result['seconds'] = 0.025;
			$fetch             = static function ( $pre, $args, $url ) use ( $result ) {
				return str_ends_with( $url, '/inquiries/assess' ) ? array(
					'response' => array( 'code' => 200 ),
					'body'     => wp_json_encode( $result + array( 'binding' => json_decode( $args['body'], true )['binding'] ) ),
				) : $pre;
			};
			add_filter( 'pre_http_request', $fetch, 10, 3 );
			try {
				( new Queue() )->process( $order->get_id() );
			} finally {
				remove_filter( 'pre_http_request', $fetch, 10 );
			}
			$order->read_meta_data( true );
			$data = Queue::data( $order );
			$this->assertSame( 'uncertain', $data['initial_result']['label'] );
			$this->assertSame( 'provider_budget_' . $reason, $data['initial_result']['reason'] );
			$state = AuthorizationStore::read( $order->get_id() );
			$this->assertIsArray( $state );
			$this->assertSame( 'pending', $state['status'] );
			$this->assertSame( array(), $state['jobs'] );
			$this->assertSame( 'inquiry-received', $order->get_status() );
		}
		$this->assertSame( 'invalid_response', Result::validate( Result::unknown( 'provider_budget_untrusted_text' ) )['reason'] );
	}

	/** Fraud outside the message field remains in the frozen provider input. */
	public function test_fraud_in_name_is_scanned_and_quarantined_with_gibberish_body(): void {
		$name  = 'Вам перевод 195753 руб. забрать тут https://reward.example.invalid/test';
		$order = $this->inquiry(
			array(
				'name'    => $name,
				'message' => 'THRT332399MTGJNF KSDJFKSDJF',
			)
		);
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
				'body'     => wp_json_encode( self::result( 'suspected_spam', 'fraud_or_phishing', $body['binding'] ) ),
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
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		$this->assertSame( 'quarantined', $state['status'] );
		$this->assertSame( array(), $state['jobs'] );
		$order->set_billing_first_name( 'Later edit' );
		$order->save();
		$this->assertSame( $name, Queue::data( $order )['snapshot']['submission']['billing']['first_name'] );
	}

	/**
	 * Model-shaped service output; no real model or email call is made.
	 *
	 * @param string              $label Raw label.
	 * @param string              $basis Fixed basis.
	 * @param array<string,mixed> $binding Actual service request binding.
	 * @return array<string, mixed>
	 */
	private static function result( string $label = 'normal', string $basis = 'business_request', array $binding = array() ): array {
		$decision = match ( $label ) {
			'normal' => 'normal', 'suspected_spam' => 'malicious', default => 'unknown' };
		return NormalMailAuthorizationFixture::verdict( $binding, $decision, $basis, 'unknown' === $decision ? 'insufficient_context' : 'classified' );
	}

	/** Submission persists and returns without any service call or team mail. */
	public function test_submit_never_waits_for_the_model_and_receipt_is_not_replayed(): void {
		$calls = 0;
		$fetch = static function ( $pre, $args, $url ) use ( &$calls ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				++$calls;
				return new \WP_Error( 'deliberately_slow_provider' ); }
			return $pre;
		};
		add_filter( 'pre_http_request', $fetch, 10, 3 );
		$this->later(
			static function () use ( $fetch ): void {
				remove_filter( 'pre_http_request', $fetch, 10 );
			}
		);
		$marker = self::newest_mail_job();
		$budget = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		$order  = $this->inquiry();
		$this->assertSame( 0, $calls );
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( array(), self::mail_jobs_after( $marker ), 'Neither content mail may precede classification.' );
		$data = Queue::data( $order );
		$this->assertEqualsWithDelta( Queue::WAIT_SECONDS, $data['deadline'] - $data['accepted_at'], .001 );
		( new Queue() )->process( $order->get_id() );
		$this->assertSame( 1, $calls );
		$order->read_meta_data( true );
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		$this->assertSame( 'pending', $state['status'] );
		$this->assertSame( 'service_unavailable', $state['verdict']['reason'] );
		$this->assertGreaterThan( time(), $state['next_at'] );
		( new Queue() )->process( $order->get_id() );
		( new Queue() )->expire( $order->get_id() );
		$this->assertSame( 1, $calls );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$this->assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
	}

	/**
	 * Only typed normal permits notify; malicious and unknown retain the saved source.
	 *
	 * @dataProvider observations
	 * @param string $label Service label.
	 * @param string $basis Fixed basis.
	 * @param string $expected Safe stored label.
	 */
	public function test_only_normal_decisions_notify_once( string $label, string $basis, string $expected ): void {
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
				'body'     => wp_json_encode( self::result( $label, $basis, $body['binding'] ) ),
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
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		if ( 'normal' !== $expected ) {
			$this->assertSame( array(), $state['jobs'] );
			$this->assertSame( 'suspected_spam' === $expected ? 'quarantined' : 'pending', $state['status'] );
			$queue->finish( $order->get_id(), self::result() );
			$after = AuthorizationStore::read( $order->get_id() );
			$this->assertIsArray( $after );
			$this->assertSame( array(), $after['jobs'] );
			return;
		}
		$this->assertCount( 2, $state['jobs'] );
		$job = ( new JobStore() )->load( $state['jobs']['team']['id'] );
		$this->assertNotNull( $job );
		$this->assertSame( array( 'sales@sunriverinverter.com' ), $job['message']->to );
		$this->assertStringContainsString( Result::label( $expected ), $job['message']->body );
		$this->assertStringContainsString( 'Please contact us about project equipment.', $job['message']->body );
		$queue->finish( $order->get_id(), self::result( 'suspected_spam', 'fraud_or_phishing' ) );
		$after = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $after );
		$this->assertSame( $state['jobs'], $after['jobs'] );
		$stored = ( new JobStore() )->load( $state['jobs']['team']['id'] );
		$this->assertNotNull( $stored );
		$this->assertSame( $job['message']->body, $stored['message']->body );
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

	/** Queue delay preserves a fresh model window; old unbound results cannot send again. */
	public function test_queued_task_gets_a_fresh_window_and_late_results_do_not_resend(): void {
		$order               = $this->inquiry();
		$data                = Queue::data( $order );
		$data['accepted_at'] = microtime( true ) - 20;
		$data['deadline']    = microtime( true ) - 10;
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
		$queue = new Queue();
		$queue->recover();
		$queue->process( $order->get_id() );
		$order->read_meta_data( true );
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		$this->assertSame( 'normal', $state['verdict']['decision'] );
		$this->assertSame( 'normal', $state['status'] );
		$this->assertCount( 2, $state['jobs'] );
		$this->assertCount( 1, $this->authorization->requests );
		$this->assertGreaterThan( 9.0, $this->authorization->requests[0]['remaining_seconds'] );
		$queue->finish( $order->get_id(), self::result() );
		$this->assertSame( $state, AuthorizationStore::read( $order->get_id() ) );
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( '', $order->get_meta( Admin::OVERRIDE ) );
	}

	/** A missing heartbeat cannot grant permission; an actual normal task may still authorize. */
	public function test_missing_recovery_does_not_hold_the_notification(): void {
		delete_option( Queue::HEARTBEAT );
		$marker = self::newest_mail_job();
		$order  = $this->inquiry();
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$pending = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $pending );
		$this->assertSame( 'pending', $pending['status'] );
		$state = $this->authorization->process( $order );
		$this->assertCount( 2, $state['jobs'] );
		$this->assertNotNull( ( new JobStore() )->load( $state['jobs']['team']['id'] ) );
	}

	/** A partially persisted Outbox job must roll back and remain recoverable. */
	public function test_failed_mail_meta_write_stays_pending_until_recovery(): void {
		$order  = $this->inquiry();
		$marker = self::newest_mail_job();
		$hits   = 0;
		$deny   = static function ( $check, $id, $key ) use ( &$hits ) {
			if ( '_linker_mail_message' === $key ) {
				++$hits;
				return false;
			} return $check;
		};
		add_filter( 'add_post_metadata', $deny, 10, 3 );
		add_filter( 'update_post_metadata', $deny, 10, 3 );
		try {
			( new Queue() )->process( $order->get_id() ); } finally {
			remove_filter( 'add_post_metadata', $deny, 10 );
			remove_filter( 'update_post_metadata', $deny, 10 ); }
			$this->assertGreaterThan( 0, $hits, 'The native partial-write fault must actually hit.' );
			$state = AuthorizationStore::read( $order->get_id() );
			$this->assertIsArray( $state );
			$this->assertSame( 'approved', $state['status'] );
			$this->assertSame( array(), $state['jobs'] );
			$this->assertSame( array(), self::mail_jobs_after( $marker ), 'A partial job is rolled back.' );
			AuthorizationStore::edit(
				$order->get_id(),
				static function ( array &$state ): void {
					$state['next_at'] = time() - 1;
				}
			);
		( new Queue() )->recover();
		$after = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $after );
		$this->assertSame( 'normal', $after['status'] );
		$this->assertCount( 2, $after['jobs'] );
		$this->assertCount( 2, self::mail_jobs_after( $marker ) );
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
		$state = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $state );
		$this->assertSame( 'normal', $state['status'] );
		$this->assertSame( 1, $state['attempts'] );
		$this->assertCount( 2, $state['jobs'] );
		$this->assertGreaterThan( 0, $state['jobs']['team']['id'] );
		$this->assertTrue( (bool) as_has_scheduled_action( Queue::PROCESS, array( $order->get_id() ), \Linker\Commerce\Mail\Outbox::GROUP ), 'The original durable task survives the competing worker.' );
		( new Queue() )->finish( $order->get_id(), self::result() );
		$after = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $after );
		$this->assertSame( $state['jobs'], $after['jobs'] );
	}
}

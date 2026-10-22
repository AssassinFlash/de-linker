<?php
/**
 * A local typed service reply, followed by the actual native queued consumers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use ActionScheduler_QueueRunner;
use ActionScheduler_Store;
use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\ConversationAuthorization;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Mail\Outbox;
use RuntimeException;
use WC_Order;

/** No permission method is mocked and no source is relabelled as a transaction. */
final class NormalMailAuthorizationFixture {
	/** Actual native service requests.
	 *
	 * @var list<array<string,mixed>>
	 */
	public array $requests = array();
	/** Only this fixture's processed sources.
	 *
	 * @var list<int>
	 */
	private array $orders = array();
	/** Only this fixture's processed conversation jobs.
	 *
	 * @var list<int>
	 */
	private array $conversations = array();
	/** Source indices created only by this test.
	 *
	 * @var list<string>
	 */
	private array $conversation_sources = array();

	/**
	 * Install this test's synthetic service, not a production credential/config.
	 *
	 * @param callable(callable():void):void $later Native test cleanup registrar.
	 */
	public static function install( callable $later ): self {
		require_once __DIR__ . '/AssessmentFixtureEnvironment.php';
		AssessmentFixtureEnvironment::configure();
		$self  = new self();
		$saved = array();
		foreach ( array( Queue::ENABLED, Queue::HEARTBEAT, 'linker_genie_url' ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		update_option( 'linker_genie_url', 'http://127.0.0.1:9' );
		$provider = static function ( $pre, $args, $url ) use ( $self ) {
			if ( 'http://127.0.0.1:9/inquiries/assess' !== $url ) {
				return $pre;
			}
			$request = json_decode( $args['body'], true );
			if ( ! is_array( $request ) || ! is_array( $request['binding'] ?? null ) || ! is_array( $request['state'] ?? null ) ) {
				throw new RuntimeException( 'A normal fixture requires the actual complete bound service request.' );
			}
			$self->requests[] = $request;
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode( self::verdict( $request['binding'] ) ),
			);
		};
		$no_wake  = static fn (): bool => false;
		$created  = static function ( int $id ) use ( $self ): void {
			$self->orders[] = $id;
		};
		add_filter( 'pre_http_request', $provider, 9, 3 );
		add_filter( 'action_scheduler_allow_async_request_runner', $no_wake );
		add_action( 'woocommerce_new_order', $created );
		$later(
			static function () use ( $self, $provider, $no_wake, $created, $saved ): void {
				remove_filter( 'pre_http_request', $provider, 9 );
				remove_filter( 'action_scheduler_allow_async_request_runner', $no_wake );
				remove_action( 'woocommerce_new_order', $created );
				foreach ( $self->orders as $id ) {
					delete_option( AuthorizationStore::PREFIX . $id );
					foreach ( array( Queue::PROCESS, Queue::EXPIRE ) as $hook ) {
						as_unschedule_all_actions( $hook, array( $id ), Outbox::GROUP );
					}
				}
				foreach ( $self->conversations as $job ) {
					delete_option( AuthorizationStore::PREFIX . 'conversation-' . $job );
					as_unschedule_all_actions( ConversationAuthorization::PROCESS, array( $job ), Outbox::GROUP );
				}
				foreach ( $self->conversation_sources as $source ) {
					delete_option( AuthorizationStore::PREFIX . $source );
				}
				foreach ( $saved as $name => $old ) {
					false === $old ? delete_option( $name ) : update_option( $name, $old, false );
				}
			}
		);
		return $self;
	}

	/**
	 * Synthetic typed service evidence; never an allows() return or native permit.
	 *
	 * @param array<string,mixed> $binding Actual parsed service request binding.
	 * @param string              $decision Explicit fixture outcome.
	 * @param string              $basis Explicit fixture basis.
	 * @param string              $reason Fixed diagnostic.
	 * @return array<string,mixed> Complete versioned service wire.
	 */
	public static function verdict( array $binding, string $decision = 'normal', string $basis = 'business_request', string $reason = 'classified' ): array {
		$classification              = array_fill_keys( array( 'normal', 'malicious', 'unknown' ), 0 );
		$classification[ $decision ] = 1;
		$bases                       = array_fill_keys( array( 'business_request', 'service_or_complaint', 'reporting_abuse', 'fraud_or_phishing', 'unsolicited_bulk_promotion', 'meaningless_abuse', 'insufficient_context' ), 0 );
		$bases[ $basis ]             = 1;
		return array(
			'binding'  => $binding,
			'decision' => $decision,
			'basis'    => $basis,
			'reason'   => $reason,
			'model'    => 'typesafe/jev-1.13',
			'rubric'   => 'inquiry-mail-v1',
			'seconds'  => 0.1,
			'raw'      => array(
				'primary'    => array(
					'model'   => 'typesafe/jev-1.13',
					'answers' => array(
						'classification' => array(
							'type'          => 'choice',
							'choice'        => $decision,
							'confidence'    => null,
							'probabilities' => $classification,
						),
						'basis'          => array(
							'type'          => 'choice',
							'choice'        => $basis,
							'confidence'    => null,
							'probabilities' => $bases,
						),
					),
				),
				'escalation' => null,
			),
		);
	}

	/** Explicitly drive only newly created, actually deferred sources of this test. */
	public function drain(): void {
		foreach ( array_unique( $this->orders ) as $id ) {
			$state = AuthorizationStore::read( $id );
			if ( is_array( $state ) && 'pending' === ( $state['status'] ?? '' ) ) {
				$order = wc_get_order( $id );
				if ( $order instanceof WC_Order ) {
					$this->process( $order );
				}
			}
		}
	}

	/**
	 * Consume the actual scheduled classifier operation and optionally its sends.
	 *
	 * @param WC_Order $order Saved native source.
	 * @param bool     $deliver Drive mail consumers after the durable permit.
	 * @return array<string,mixed> Real persisted authorization readback.
	 * @throws RuntimeException Missing native normal permit.
	 */
	public function process( WC_Order $order, bool $deliver = false ): array {
		$id             = $order->get_id();
		$this->orders[] = $id;
		self::consume( Queue::PROCESS, $id );
		$state = AuthorizationStore::read( $id );
		if ( ! is_array( $state ) || 'normal' !== ( $state['status'] ?? '' ) ) {
			throw new RuntimeException( 'The native source did not obtain a durable normal permit.' );
		}
		if ( $deliver ) {
			foreach ( $state['jobs'] as $entry ) {
				self::consume( Outbox::HOOK, $entry['id'] );
			}
		}
		return $state;
	}

	/**
	 * Consume the separate native conversation task, never borrow an inquiry grant.
	 *
	 * @param int $job Original native conversation job.
	 * @return array<string,mixed> Persisted source permit.
	 * @throws RuntimeException Missing native normal permit.
	 */
	public function conversation( int $job ): array {
		$this->conversations[] = $job;
		$raw                   = get_post_meta( $job, ConversationAuthorization::SOURCE, true );
		$source                = is_string( $raw ) ? json_decode( $raw, true ) : null;
		if ( is_array( $source ) ) {
			$this->conversation_sources[] = 'conversation-source-' . \Linker\Commerce\Inquiry\Assessment\SendAuthorization::hash( $source );
		}
		self::consume( ConversationAuthorization::PROCESS, $job );
		$state = AuthorizationStore::read( 'conversation-' . $job );
		if ( ! is_array( $state ) || 'normal' !== ( $state['status'] ?? '' ) ) {
			throw new RuntimeException( 'The native conversation did not obtain a durable normal permit.' );
		}
		return $state;
	}

	/**
	 * Execute only this exact source's actual pending Action Scheduler task.
	 *
	 * @param string $hook Native fixed hook.
	 * @param int    $id Native source/job ID.
	 * @throws RuntimeException Missing or duplicate native consumer.
	 */
	public static function consume( string $hook, int $id ): void {
		$actions = as_get_scheduled_actions(
			array(
				'hook'     => $hook,
				'args'     => array( $id ),
				'group'    => Outbox::GROUP,
				'status'   => ActionScheduler_Store::STATUS_PENDING,
				'per_page' => 2,
			),
			'ids'
		);
		if ( 1 !== count( $actions ) ) {
			$all      = as_get_scheduled_actions(
				array(
					'hook'     => $hook,
					'args'     => array( $id ),
					'group'    => Outbox::GROUP,
					'per_page' => 100,
				),
				'ids'
			);
			$statuses = array();
			foreach ( $all as $action ) {
				$statuses[] = \ActionScheduler_Store::instance()->get_status( (string) $action );
			}
			throw new RuntimeException( 'Expected one actual pending native consumer; existing action states: ' . implode( ',', $statuses ) );
		}
		ActionScheduler_QueueRunner::instance()->process_action( (int) $actions[0], 'bound normal mail fixture' );
	}
}

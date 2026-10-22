<?php
/**
 * Durable observation and one logical team notification per inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;

/** Woo stores evidence; Action Scheduler runs it; Outbox owns delivery. */
final class Queue {
	public const ENABLED   = 'linker_inquiry_assessment_enabled';
	public const META      = '_linker_inquiry_assessment';
	public const PENDING   = '_linker_inquiry_assessment_pending';
	public const PROCESS   = 'linker_inquiry_assessment_process';
	public const EXPIRE    = 'linker_inquiry_assessment_expire';
	public const FINISH    = 'linker_inquiry_assessment_finish';
	public const HEARTBEAT = 'linker_inquiry_assessment_recovery';
	// Owner confirmed 2026-10-22, issue 511: queue delay consumes this budget.
	public const WAIT_SECONDS = 10;
	// Recovery is a real once-per-minute CLI cron, not traffic-driven WP-Cron.
	// Two missed minute ticks make readiness fail open for new submissions.
	public const RECOVERY_STALE = 120;

	/** Feature stays dormant until the deployment runbook enables it. */
	public static function enabled(): bool {
		return 'yes' === get_option( self::ENABLED, 'no' );
	}

	/**
	 * Add an immutable snapshot to the inquiry's ordinary save; no network I/O.
	 *
	 * @param WC_Order             $order Inquiry before received status.
	 * @param array<string, mixed> $context Trusted current source link.
	 */
	public static function prepare( WC_Order $order, array $context = array() ): void {
		if ( ! self::enabled() || $order->get_meta( Reviews::ERASED ) || is_array( $order->get_meta( self::META ) ) ) {
			return;
		}
		$now      = microtime( true );
		$snapshot = Snapshot::make( $order, $context );
		// Staff decision provenance stays local; the provider snapshot is unchanged.
		try {
			StructuredMeta::update( $order, CustomerEvidence::META, CustomerEvidence::capture( $order, $snapshot, $now ) );
		} catch ( \Throwable $error ) {
			// A local advisory record cannot prevent the normal inquiry path.
			$order->update_meta_data(
				CustomerEvidence::META,
				array(
					'captured_at' => $now,
					'status'      => 'unavailable',
				)
			);
		}
		StructuredMeta::update(
			$order,
			self::META,
			array(
				'accepted_at'      => $now,
				'deadline'         => $now + self::WAIT_SECONDS,
				'snapshot'         => $snapshot,
				'result'           => Result::unknown( 'pending' ),
				'notification_job' => 0,
			)
		);
		$order->update_meta_data( self::PENDING, 'yes' );
	}

	/**
	 * Intercept only the team listener; customer receipts/status stay independent.
	 *
	 * @param WC_Order $order Received inquiry.
	 */
	public static function defer( WC_Order $order ): bool {
		if ( NotificationHold::held( $order ) ) {
			return true;
		}
		if ( ! self::enabled() ) {
			return false;
		}
		self::prepare( $order );
		$order->save_meta_data();
		$order->read_meta_data( true );
		$unavailable = ! Client::configured() ? 'service_unavailable' : ( microtime( true ) - (float) get_option( self::HEARTBEAT, 0 ) > self::RECOVERY_STALE ? 'recovery_unavailable' : '' );
		if ( ! function_exists( 'as_enqueue_async_action' ) || '' !== $unavailable ) {
			// No independent recovery: preserve the existing immediate delivery path.
			// This performs no model I/O and adds no model wait to submission.
			$data                    = self::data( $order );
			$data['inline_delivery'] = true;
			$order->update_meta_data( self::META, $data );
			$order->save_meta_data();
			( new self() )->finish( $order->get_id(), Result::unknown( '' !== $unavailable ? $unavailable : 'scheduler_unavailable' ) );
			return true;
		}
		$data = self::data( $order );
		as_schedule_single_action( (int) ceil( (float) $data['deadline'] ), self::EXPIRE, array( $order->get_id() ), Outbox::GROUP, true );
		as_enqueue_async_action( self::PROCESS, array( $order->get_id() ), Outbox::GROUP, true );
		return true;
	}

	/**
	 * Fresh data, including after another worker committed a deadline result.
	 *
	 * @param WC_Order $order Record.
	 * @return array<string, mixed>
	 */
	public static function data( WC_Order $order ): array {
		$value = $order->get_meta( self::META );
		return is_array( $value ) ? $value : array();
	}

	/**
	 * Background only. A second worker cannot spend twice on the same job.
	 *
	 * @param int $id Inquiry id.
	 */
	public function process( int $id ): void {
		Lock::run(
			'process-' . $id,
			function () use ( $id ): void {
				Lock::run(
					'release-' . $id,
					function () use ( $id ): void {
						$order = wc_get_order( $id );
						if ( ! $order instanceof WC_Order ) {
							return;
						}
						$order->read_meta_data( true );
						$data = self::data( $order );
						if ( NotificationHold::held( $order ) || array() === $data || (int) ( $data['notification_job'] ?? 0 ) !== 0 ) {
							return;
						}
						$deadline = (float) $data['deadline'];
						$now      = microtime( true );
						$reason   = match ( true ) {
							$now >= $deadline => 'deadline',
							! self::enabled() => 'disabled',
							! Client::configured() => 'service_unavailable',
							$now - (float) get_option( self::HEARTBEAT, 0 ) > self::RECOVERY_STALE => 'recovery_unavailable',
							default => '',
						};
						$result                  = '' !== $reason ? Result::unknown( $reason ) : ( new Client() )->assess( (array) $data['snapshot'], $deadline );
						$result['started_at']    = $now;
						$result['queue_seconds'] = max( 0.0, $now - (float) $data['accepted_at'] );
						$this->finish( $id, $result );
					}
				);
			}
		);
	}

	/**
	 * Persist a result; late answers never rewrite the first notice or resend.
	 *
	 * @param int                  $id Inquiry id.
	 * @param array<string, mixed> $result Validated result.
	 */
	public function finish( int $id, array $result ): void {
		$done = Lock::run(
			'release-' . $id,
			function () use ( $id, $result ): void {
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					return;
				}
				$order->read_meta_data( true );
				$data = self::data( $order );
				if ( NotificationHold::held( $order ) || array() === $data ) {
					return;
				}
				$now                  = microtime( true );
				$data['result']       = $result;
				$data['completed_at'] = $now;
				$data['elapsed']      = max( 0.0, $now - (float) $data['accepted_at'] );
				if ( 0 === (int) $data['notification_job'] ) {
					$data['initial_result'] = $now >= (float) $data['deadline'] ? Result::unknown( 'deadline' ) : $result;
					$this->queue_notice( $order, $data );
				} else {
					$data['late_result'] = $result;
					$order->update_meta_data( self::META, $data );
					$order->save_meta_data();
					$this->dispatch( $order, $data );
				}
			}
		);
		if ( ! $done && function_exists( 'as_schedule_single_action' ) ) {
			$order = wc_get_order( $id );
			if ( $order instanceof WC_Order ) {
				$order->read_meta_data( true );
				if ( NotificationHold::held( $order ) ) {
					return;
				}
			}
			// Retry a small typed result next second after a release/deadline race;
			// do not call a model or renew the original classification deadline.
			as_schedule_single_action( time() + 1, self::FINISH, array( $id, $result ), Outbox::GROUP, true );
		}
	}

	/**
	 * Deadline/recovery path never calls a model.
	 *
	 * @param int $id Inquiry id.
	 */
	public function expire( int $id ): void {
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$order->read_meta_data( true );
		$data = self::data( $order );
		if ( NotificationHold::held( $order ) || array() === $data ) {
			return;
		}
		if ( 0 !== (int) $data['notification_job'] ) {
			Lock::run(
				'release-' . $id,
				function () use ( $order ): void {
					$order->read_meta_data( true );
					$this->dispatch( $order, self::data( $order ) );
				}
			);
			return;
		}
		if ( microtime( true ) >= (float) $data['deadline'] ) {
			$this->finish( $id, Result::unknown( 'deadline' ) );
		}
	}

	/**
	 * One atomic logical message handoff to the existing persistent Outbox.
	 *
	 * @param WC_Order             $order Locked inquiry.
	 * @param array<string, mixed> $data Committed assessment candidate.
	 * @throws \RuntimeException Caught and rolled back locally when Outbox storage fails.
	 */
	private function queue_notice( WC_Order $order, array $data ): void {
		$emails = WC()->mailer()->get_emails();
		$email  = $emails[ NewInquiryEmail::class ] ?? null;
		if ( ! $email instanceof NewInquiryEmail ) {
			return;
		}
		wc_transaction_query( 'start' );
		try {
			$order->update_meta_data( self::META, $data );
			$message = $email->capture( $order );
			$job     = null === $message ? -1 : ( new JobStore() )->create( $message, $order->get_id() );
			if ( 0 === $job ) {
				throw new \RuntimeException( 'assessment_outbox_write_failed' );
			}
			$stored = $job > 0 ? ( new JobStore() )->load( $job ) : null;
			if ( $job > 0 && ( null === $stored || $stored['message']->to_array() !== $message->to_array() ) ) {
				throw new \RuntimeException( 'assessment_outbox_readback_failed' );
			}
			$data['notification_job'] = $job;
			$order->update_meta_data( self::META, $data );
			$order->save_meta_data();
			$order->read_meta_data( true );
			if ( self::data( $order ) !== $data ) {
				throw new \RuntimeException( 'assessment_ledger_readback_failed' );
			}
			wc_transaction_query( 'commit' );
		} catch ( \Throwable $error ) {
			wc_transaction_query( 'rollback' );
			$order->read_meta_data( true );
			wc_get_logger()->error( 'Inquiry assessment notification could not be queued.', array( 'source' => 'linker-inquiry-assessment' ) );
			return;
		}
		$this->dispatch( $order, $data );
	}

	/**
	 * A crash after commit leaves PENDING=yes, so the CLI recovery schedules it.
	 *
	 * @param WC_Order             $order Record.
	 * @param array<string, mixed> $data Stored ledger.
	 */
	private function dispatch( WC_Order $order, array $data ): void {
		if ( NotificationHold::held( $order ) ) {
			return;
		}
		$job = (int) $data['notification_job'];
		if ( $job > 0 && null !== ( new JobStore() )->load( $job ) && JobStore::FAILED_STATUS !== get_post_status( $job ) ) {
			if ( function_exists( 'as_has_scheduled_action' ) && as_has_scheduled_action( Outbox::HOOK, array( $job ), Outbox::GROUP ) ) {
				return;
			}
			if ( ! empty( $data['inline_delivery'] ) ) {
				/** This action is documented in Mail\Module::register(). */
				do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Outbox::HOOK is linker_commerce_mail_attempt.
				return;
			}
			$scheduled = as_enqueue_async_action( Outbox::HOOK, array( $job ), Outbox::GROUP, true );
			if ( 0 === $scheduled && ! as_has_scheduled_action( Outbox::HOOK, array( $job ), Outbox::GROUP ) ) {
				return;
			}
			// Keep recovery visibility until delivery succeeds or exhausts retries.
			return;
		}
		$order->update_meta_data( self::PENDING, 'no' );
		$order->save_meta_data();
	}

	/**
	 * External once-per-minute CLI tick; works with zero visitor traffic.
	 *
	 * @return int Number of pending inquiries examined.
	 */
	public function recover(): int {
		update_option( self::HEARTBEAT, microtime( true ), false );
		// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- Native Woo pending-only recovery query; supports classic and HPOS storage.
		$orders = wc_get_orders(
			array(
				'limit'      => -1,
				'meta_query' => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- Native Woo pending-only recovery; this meta is cleared after handoff.
					array(
						'key'   => self::PENDING,
						'value' => 'yes',
					),
				),
			)
		);
		$count  = 0;
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			$this->expire( $order->get_id() );
			++$count;
		}
		return $count;
	}

	/** Register background handlers without doing any work in a submit. */
	public function register(): void {
		( new RecoverySchedule() )->register();
		add_action( self::PROCESS, array( $this, 'process' ) );
		add_action( self::EXPIRE, array( $this, 'expire' ) );
		add_action( self::FINISH, array( $this, 'finish' ), 10, 2 );
		( new Admin() )->register();
		( new EvidencePrivacy() )->register();
	}
}

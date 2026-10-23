<?php
/** Restore only an original consumer which failed before an Outbox attempt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

use Linker\Commerce\Inquiry\Assessment\Lock;

/** No transport, message creation, authorization or quota reservation occurs here. */
final class PreTransportRecovery {
	public const META = '_linker_mail_pre_transport_recovery';

	/**
	 * Use the same native queue as the original Outbox.
	 *
	 * @param JobStore $jobs Original immutable jobs.
	 */
	public function __construct( private readonly JobStore $jobs ) {}

	/**
	 * Action Scheduler retains the typed cause when it wraps a callback error.
	 *
	 * @param int        $action_id Failed native action.
	 * @param \Exception $error Native exception, never an HTTP/browser field.
	 */
	public function failed( int $action_id, \Exception $error ): void {
		$cause = $error;
		while ( ! $cause instanceof PreTransportFailure && null !== $cause->getPrevious() ) {
			$cause = $cause->getPrevious();
		}
		if ( ! $cause instanceof PreTransportFailure ) {
			return;
		}
		try {
			ConnectionFence::run(
				function () use ( $action_id ): void {
					$action = \ActionScheduler::store()->fetch_action( $action_id );
					if ( $action instanceof \ActionScheduler_NullAction ) {
						throw new \RuntimeException( 'mail_pre_transport_action_unavailable' );
					}
					$args = $action->get_args();
					if ( Outbox::HOOK !== $action->get_hook() || Outbox::GROUP !== $action->get_group() || array_keys( $args ) !== array( 0 ) || ! is_int( $args[0] ) || $args[0] < 1 || 'failed' !== \ActionScheduler::store()->get_status( $action_id ) ) {
						return;
					}
					$this->edit(
						$args[0],
						static function ( int $job ): void {
							// Commit the phase before a separate scheduling transaction.
						},
						$action_id
					);
					$this->resume( $args[0] );
				}
			);
		} catch ( \Throwable $failure ) {
			self::diagnostic();
		}
	}

	/** The existing independent minute heartbeat repairs only a stored unscheduled phase. */
	public function recover(): void {
		try {
			$jobs = ConnectionFence::run(
				static fn (): array => get_posts(
					array(
						'post_type'   => JobStore::POST_TYPE,
						'post_status' => 'private',
						'meta_key'    => self::META, // phpcs:ignore WordPress.DB.SlowDBQuery -- Only the native bounded recovery phase, never body/history or held jobs.
						'fields'      => 'ids',
						// Every possible live job is bounded by the existing shared envelope.
						'numberposts' => array_sum( array_column( Capacity::LIMITS, 'count' ) ),
					)
				)
			);
			foreach ( $jobs as $job ) {
				$this->resume( (int) $job );
			}
		} catch ( \Throwable $failure ) {
			self::diagnostic();
		}
	}

	/**
	 * Claim one exact job with short native locks; never carry a fence into transport.
	 *
	 * @param int      $job Original job.
	 * @param callable $work Read-back and scheduling only.
	 * @param int      $failed_action Optional newly failed pre-transport source.
	 * @throws \RuntimeException Unconfirmed native phase or scheduler write.
	 */
	private function edit( int $job, callable $work, int $failed_action = 0 ): void {
		$taken = Lock::run(
			'mail-read-recovery-' . $job,
			function () use ( $job, $work, $failed_action ): void {
				NativeTransaction::run(
					function () use ( $job, $work, $failed_action ): void {
						global $wpdb;
						// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact original committed job, same native NOWAIT boundary as its scheduler.
						$row = $wpdb->get_var( $wpdb->prepare( 'SELECT ID FROM %i WHERE ID=%d FOR UPDATE NOWAIT', $wpdb->posts, $job ) );
						clean_post_cache( $job );
						if ( (int) $row !== $job || 'private' !== get_post_status( $job ) || $this->jobs->held( $job ) || null === $this->jobs->load( $job ) || NativeAttempt::unresolved( $job ) ) {
							return;
						}
						if ( $failed_action > 0 ) {
							$previous = get_post_meta( $job, self::META, true );
							if ( '' !== $previous ) {
								if ( ! is_array( $previous ) || ! is_int( $previous['action'] ?? null ) || ! is_int( $previous['count'] ?? null ) || $previous['count'] < 1 || $previous['count'] > count( Outbox::RETRY_DELAYS ) + 1 || ! is_int( $previous['scheduled'] ?? null ) ) {
									throw new \RuntimeException( 'mail_pre_transport_phase_invalid' );
								}
								// Native AS IDs increase. Duplicate/older callbacks cannot
								// resurrect a phase; a later known-safe consumer may advance it.
								if ( $previous['action'] >= $failed_action ) {
									return;
								}
							}
							$count = '' === $previous ? 1 : $previous['count'] + 1;
							$state = array(
								'action'    => $failed_action,
								'count'     => min( $count, count( Outbox::RETRY_DELAYS ) + 1 ),
								'due'       => $count <= count( Outbox::RETRY_DELAYS ) ? time() + Outbox::RETRY_DELAYS[ $count - 1 ] : 0,
								'scheduled' => 0,
							);
							self::save( $job, $state );
							if ( 0 === $state['due'] ) {
								self::diagnostic();
							}
						}
						$work( $job );
					}
				);
			},
			0,
			true
		);
		if ( ! $taken ) {
			throw new \RuntimeException( 'mail_pre_transport_recovery_busy' );
		}
	}

	/**
	 * A confirmed successor consumes this phase; later SMTP/ACK errors cannot reuse it.
	 *
	 * @param int $job Original job.
	 */
	private function resume( int $job ): void {
		try {
			$this->edit(
				$job,
				function ( int $id ): void {
					$state = get_post_meta( $id, self::META, true );
					if ( ! is_array( $state ) || ! is_int( $state['count'] ?? null ) || $state['count'] < 1 || $state['count'] > count( Outbox::RETRY_DELAYS ) || ! is_int( $state['due'] ?? null ) || $state['due'] < 1 || 0 !== ( $state['scheduled'] ?? null ) ) {
						return;
					}
					// An existing running consumer may already be in SMTP. Reuse
					// its identity rather than arming another attempt behind it.
					$pending = array_merge( self::actions( $id, 'in-progress' ), self::actions( $id, 'pending' ) );
					if ( array() === $pending ) {
						$this->jobs->reschedule( $id, max( time() + 1, $state['due'] ) );
						$pending = self::actions( $id, 'pending' );
					}
					if ( 1 !== count( $pending ) ) {
						throw new \RuntimeException( 'mail_pre_transport_successor_unconfirmed' );
					}
					$state['scheduled'] = (int) $pending[0];
					self::save( $id, $state );
				}
			);
		} catch ( \Throwable $failure ) {
			self::diagnostic();
		}
	}

	/**
	 * Read only this original job's current native consumers.
	 *
	 * @param int    $job Original job.
	 * @param string $status Native pending or in-progress state.
	 * @return array<mixed> Native action IDs; two exposes a duplicate instead of hiding it.
	 */
	private static function actions( int $job, string $status ): array {
		return as_get_scheduled_actions(
			array(
				'hook'     => Outbox::HOOK,
				'args'     => array( $job ),
				'group'    => Outbox::GROUP,
				'status'   => $status,
				'per_page' => 2,
			),
			'ids'
		);
	}

	/**
	 * Verify the server phase before the native transaction may commit.
	 *
	 * @param int               $job Original job.
	 * @param array<string,int> $state Fixed bounded phase, no content or recipients.
	 * @throws \RuntimeException The phase is not durably readable.
	 */
	private static function save( int $job, array $state ): void {
		update_post_meta( $job, self::META, $state );
		wp_cache_delete( $job, 'post_meta' );
		if ( get_post_meta( $job, self::META, true ) !== $state ) {
			throw new \RuntimeException( 'mail_pre_transport_phase_unconfirmed' );
		}
	}

	/** Fixed diagnostic, never raw native errors or the frozen message. */
	private static function diagnostic(): void {
		CapacityHealth::failed();
		wc_get_logger()->warning( 'Original notification retained; pre-transport recovery could not be confirmed.', array( 'source' => Outbox::LOG_SOURCE ) );
	}
}

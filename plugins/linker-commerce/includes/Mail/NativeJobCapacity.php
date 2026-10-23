<?php
/**
 * The production queue's sole durable resource boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/** Server pre-reservations and all actual jobs share the same Capacity store. */
final class NativeJobCapacity implements JobCapacity {
	/**
	 * Admit one complete native write.
	 *
	 * @param Message  $message Frozen notification.
	 * @param callable $write Native write/readback.
	 * @phpstan-param callable():int $write
	 */
	public function create( Message $message, callable $write ): int {
		return Capacity::create(
			$message,
			static function () use ( $write ): int {
				$id = $write();
				// An original held job stays charged but cannot arm transport recovery.
				if ( $id > 0 && ! NotificationHold::job_held( $id ) ) {
					if ( ! as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) ) {
						as_schedule_single_action( time() + 1, Outbox::HOOK, array( $id ), Outbox::GROUP, true );
					}
					if ( ! as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) ) {
						throw new \RuntimeException( 'notification_recovery_not_persisted' );
					}
				}
				return $id;
			}
		);
	}

	/**
	 * Promote the same native job under the shared mutex.
	 *
	 * @param int      $id Original job.
	 * @param callable $write Native priority update/readback.
	 */
	public function promote( int $id, callable $write ): void {
		Capacity::promote( $id, $write );
	}

	/**
	 * Release only verified deletion.
	 *
	 * @param int $id Original job.
	 */
	public function deleted( int $id ): void {
		Capacity::deleted( $id );
		clean_post_cache( $id );
		if ( null === get_post( $id ) ) {
			as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
		}
	}

	/**
	 * Rescheduling cannot lose the old pending action if the replacement fails.
	 *
	 * @param int $id Original job.
	 * @param int $time Next attempt time.
	 * @throws \RuntimeException The original job's successor cannot be confirmed.
	 */
	public function reschedule( int $id, int $time ): void {
		$taken = \Linker\Commerce\Inquiry\Assessment\Lock::run(
			'mail-schedule-' . $id,
			static function () use ( $id, $time ): void {
				NativeTransaction::run(
					static function () use ( $id, $time ): void {
						global $wpdb;
						// An uncommitted outer owner cannot make this short scheduler
						// wait on its action rows. Lock the exact original job first.
						// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Original native job row, immediately bounded by NOWAIT.
						$row = $wpdb->get_var( $wpdb->prepare( 'SELECT ID FROM %i WHERE ID=%d FOR UPDATE NOWAIT', $wpdb->posts, $id ) );
						if ( (int) $row !== $id ) {
							throw new \RuntimeException( 'notification_retry_source_missing' );
						}
						as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
						// Native unique=true includes the currently running predecessor,
						// so it cannot schedule its retry. This original-job lock plus
						// transaction admits exactly one pending successor instead.
						$action  = as_schedule_single_action( $time, Outbox::HOOK, array( $id ), Outbox::GROUP, false );
						$pending = as_get_scheduled_actions(
							array(
								'hook'     => Outbox::HOOK,
								'args'     => array( $id ),
								'group'    => Outbox::GROUP,
								'status'   => 'pending',
								'per_page' => 2,
							),
							'ids'
						);
						if ( $action < 1 || 1 !== count( $pending ) || (int) $pending[0] !== $action ) {
							throw new \RuntimeException( 'notification_retry_not_persisted' );
						}
					}
				);
			}
		);
		if ( ! $taken ) {
			throw new \RuntimeException( 'notification_retry_busy' );
		}
	}

	/** Read actual native transaction state without committing the caller. */
	public function transaction_active(): bool {
		return Capacity::transaction_active();
	}
}

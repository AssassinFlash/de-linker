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
				if ( $id > 0 ) {
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

	/** Read actual native transaction state without committing the caller. */
	public function transaction_active(): bool {
		return Capacity::transaction_active();
	}
}

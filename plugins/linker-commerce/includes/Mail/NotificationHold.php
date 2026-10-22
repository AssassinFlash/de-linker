<?php
/**
 * Server-side notification hold, compatible with preserved incident metadata.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Inquiry\Assessment\Queue;
use WC_Order;
use WP_Error;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;

/**
 * A hold preserves the original inquiry and message; labels never create one.
 */
final class NotificationHold {

	public const META     = '_linker_incident_hold';
	public const RELEASED = '_linker_incident_released';
	public const EVENT    = '_linker_notification_release';

	/**
	 * Existing server-side order or job hold; malformed nonempty markers fail safe.
	 *
	 * @param WC_Order $order Fresh native inquiry.
	 */
	public static function held( WC_Order $order ): bool {
		$job = (int) ( Queue::data( $order )['notification_job'] ?? 0 );
		if ( $job > 0 ) {
			// Refresh the job after another DB connection changed a hold under the mutex.
			wp_cache_delete( $job, 'post_meta' );
		}
		return (bool) $order->get_meta( self::META ) || 'held' === $order->get_meta( Queue::PENDING ) || ( $job > 0 && (bool) get_post_meta( $job, self::META, true ) );
	}

	/**
	 * A legacy job stores its inquiry reference inside the incident marker.
	 *
	 * @param int $job Original persistent mail job.
	 */
	public static function inquiry( int $job ): int {
		wp_cache_delete( $job, 'post_meta' );
		$hold = get_post_meta( $job, self::META, true );
		$id   = (int) get_post_meta( $job, JobStore::INQUIRY_META, true );
		return $id > 0 ? $id : ( is_array( $hold ) ? (int) ( $hold['order'] ?? 0 ) : 0 );
	}

	/**
	 * Whether the persistent job or its source inquiry is held.
	 *
	 * @param int $job Original notification job.
	 */
	public static function job_held( int $job ): bool {
		wp_cache_delete( $job, 'post_meta' );
		$hold = get_post_meta( $job, self::META, true );
		if ( $hold ) {
			return true;
		}
		$order_id = self::inquiry( $job );
		$order    = $order_id > 0 ? wc_get_order( $order_id ) : false;
		if ( $order instanceof WC_Order ) {
			$order->read_meta_data( true );
			return self::held( $order );
		}
		return false;
	}
	/**
	 * Bind the staff control to this precise server-side hold and original job.
	 *
	 * @param WC_Order $order Fresh native inquiry.
	 */
	public static function reference( WC_Order $order ): string {
		$job = (int) ( Queue::data( $order )['notification_job'] ?? 0 );
		return hash( 'sha256', (string) wp_json_encode( array( $order->get_id(), $job, $order->get_meta( self::META ), get_post_meta( $job, self::META, true ), $order->get_meta( Queue::PENDING ), \Linker\Commerce\Inquiry\Assessment\SendAuthorization::reference( $order ) ) ) );
	}

	/**
	 * Restore one retained message. The HTTP controller also verifies its nonce.
	 *
	 * @phpstan-impure
	 *
	 * @param int    $id Native inquiry ID.
	 * @param string $reference Hold shown to the staff member.
	 * @return array<string, mixed>|WP_Error Persisted release audit or explicit error.
	 */
	public static function release( int $id, string $reference ): array|WP_Error {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return new WP_Error( 'forbidden', __( 'You cannot release this notification.', 'linker-commerce' ) );
		}
		$result = new WP_Error( 'notification_busy', __( 'This notification is being processed. Reload the inquiry before trying again.', 'linker-commerce' ) );
		Lock::run(
			'release-' . $id,
			static function () use ( $id, $reference, &$result ): void {
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					$result = new WP_Error( 'invalid_inquiry', __( 'This inquiry is unavailable.', 'linker-commerce' ) );
					return;
				}
				$order->read_meta_data( true );
				$previous = $order->get_meta( self::RELEASED );
				if ( is_array( $previous ) && is_string( $previous['reference'] ?? null ) && hash_equals( $previous['reference'], $reference ) ) {
					$result = $previous;
					return;
				}
				if ( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::managed( $id ) ) {
					$result = \Linker\Commerce\Inquiry\Assessment\SendAuthorization::release( $order, $reference );
					return; }
				if ( $order->get_meta( \Linker\Commerce\Protection\Intake::META ) && 0 === (int) ( Queue::data( $order )['notification_job'] ?? 0 ) ) {
					$result = \Linker\Commerce\Protection\IntakeRelease::run( $order, $reference );
					return;
				}
				$job    = (int) ( Queue::data( $order )['notification_job'] ?? 0 );
				$stored = ( new JobStore() )->load( $job );
				if ( ! self::held( $order ) || ! hash_equals( self::reference( $order ), $reference ) || null === $stored || 'private' !== get_post_status( $job ) || ! $stored['message']->is_internal() || ( self::inquiry( $job ) > 0 && self::inquiry( $job ) !== $id ) ) {
						$result = new WP_Error( 'notification_changed', __( 'This notification has changed. Reload the inquiry before trying again.', 'linker-commerce' ) );
						return;
				}
				$running = as_get_scheduled_actions(
					array(
						'hook'     => Outbox::HOOK,
						'args'     => array( $job ),
						'group'    => Outbox::GROUP,
						'status'   => 'in-progress',
						'per_page' => 1,
					),
					'ids'
				);
				if ( $running ) {
					return;
				}
				$note = 0;
				wc_transaction_query( 'start' );
				try {
					$event = array(
						'at'                => time(),
						'user'              => get_current_user_id(),
						'job'               => $job,
						'reference'         => $reference,
						'previous_hold'     => $order->get_meta( self::META ),
						'previous_job_hold' => get_post_meta( $job, self::META, true ),
					);
					$note  = $order->add_order_note( __( 'Notification released by staff.', 'linker-commerce' ), 0, true );
					if ( $note <= 0 || ! add_comment_meta( $note, self::EVENT, wp_slash( $event ), true ) || get_comment_meta( $note, self::EVENT, true ) !== $event ) {
								throw new \RuntimeException( 'notification_release_audit_failed' );
					}
					// Cancel any stale pending attempt before restoring one future attempt.
					as_unschedule_all_actions( Outbox::HOOK, array( $job ), Outbox::GROUP );
					$slot   = max( time() + 2, ( new Throttle() )->next_message_slot( time(), $stored['message'], true ) );
					$action = as_schedule_single_action( $slot, Outbox::HOOK, array( $job ), Outbox::GROUP, true );
					if ( $action <= 0 ) {
						throw new \RuntimeException( 'notification_release_schedule_failed' );
					}
					$event['action'] = $action;
					$event['event']  = $note;
					update_post_meta( $job, JobStore::INQUIRY_META, $id );
					( new JobStore() )->promote( $job );
					delete_post_meta( $job, self::META );
					update_post_meta( $job, self::RELEASED, wp_slash( $event ) );
					$order->delete_meta_data( self::META );
					$order->update_meta_data( Queue::PENDING, 'yes' );
					StructuredMeta::update( $order, self::RELEASED, $event );
					$order->save_meta_data();
					$order->read_meta_data( true );
					$readback = ( new JobStore() )->load( $job );
					if ( self::held( $order ) || $order->get_meta( self::RELEASED ) !== $event || get_post_meta( $job, self::RELEASED, true ) !== $event || null === $readback || $readback['message']->to_array() !== $stored['message']->to_array() || $readback['attempts'] !== $stored['attempts'] ) {
						throw new \RuntimeException( 'notification_release_readback_failed' );
					}
					wc_transaction_query( 'commit' );
					$result = $event;
				} catch ( \Throwable $error ) {
					wc_transaction_query( 'rollback' );
					wp_cache_delete( $job, 'post_meta' );
					if ( $note > 0 ) {
						clean_comment_cache( $note );
						wp_cache_delete( $note, 'comment_meta' );
					}
					$order->read_meta_data( true );
					$result = new WP_Error( 'notification_release_failed', __( 'The notification could not be released. Reload the inquiry before trying again.', 'linker-commerce' ) );
				}
			}
		);
		return $result;
	}
}

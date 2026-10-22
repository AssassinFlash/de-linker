<?php
/**
 * Staff handoff of a native review record that has no original mail job.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use WC_Order;
use WP_Error;

/** Called only inside NotificationHold's capability-checked per-record mutex. */
final class IntakeRelease {
	/**
	 * Preserve exactly one internal notification and a staff audit, never a receipt.
	 *
	 * @param WC_Order $order Fresh held record.
	 * @param string   $reference Staff's record-bound reference.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function run( WC_Order $order, string $reference ): array|WP_Error {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $order, $reference ): array|WP_Error {
				// The caller's object predates this mutex and may predate native erasure.
				// Load a new native object and force its protected metadata from storage.
				$order = new WC_Order( $order->get_id() );
				$order->read_meta_data( true );
				$registered = false;
				foreach ( $state['entries'] as $id => $entry ) {
					if ( $id === $order->get_meta( BusinessRecord::REQUEST ) && in_array( (int) $entry['order'], array( 0, $order->get_id() ), true ) ) {
						if ( ! empty( $entry['erased'] ) ) {
							return self::failed();
						}
						$registered = true;
					}
				}
				$emails = WC()->mailer()->get_emails();
				$email  = $emails[ NewInquiryEmail::class ] ?? null;
				if ( ! $registered || ! $email instanceof NewInquiryEmail || ! $order->get_meta( Intake::META ) || ! NotificationHold::held( $order ) || ! hash_equals( NotificationHold::reference( $order ), $reference ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) ) {
					return self::failed();
				}
				$job  = 0;
				$note = 0;
				wc_transaction_query( 'start' );
				try {
					$now  = microtime( true );
					$data = array(
						'accepted_at'      => $now,
						'deadline'         => $now,
						'result'           => Result::unknown( 'staff_release' ),
						'initial_result'   => Result::unknown( 'staff_release' ),
						'completed_at'     => $now,
						'notification_job' => 0,
					);
					StructuredMeta::update( $order, Queue::META, $data );
					$message = $email->capture( $order );
					$job     = null === $message ? 0 : ( new JobStore() )->create( $message, $order->get_id() );
					if ( $job <= 0 || null === ( new JobStore() )->load( $job ) ) {
						throw new \RuntimeException( 'intake_notification_capture_failed' );
					}
					( new JobStore() )->promote( $job );
					$action = as_schedule_single_action( max( time() + 2, ( new Throttle() )->next_message_slot( time(), $message, true ) ), Outbox::HOOK, array( $job ), Outbox::GROUP, true );
					$event  = array(
						'at'            => time(),
						'user'          => get_current_user_id(),
						'job'           => $job,
						'reference'     => $reference,
						'previous_hold' => $order->get_meta( NotificationHold::META ),
						'action'        => $action,
					);
					$note   = $order->add_order_note( __( 'Review completed by staff; one internal notification queued.', 'linker-commerce' ), 0, true );
					if ( $action <= 0 || $note <= 0 || ! add_comment_meta( $note, NotificationHold::EVENT, wp_slash( $event ), true ) ) {
						throw new \RuntimeException( 'intake_notification_schedule_failed' );
					}
					$event['event']           = $note;
					$data['notification_job'] = $job;
					StructuredMeta::update( $order, Queue::META, $data );
					StructuredMeta::update( $order, NotificationHold::RELEASED, $event );
					$order->delete_meta_data( NotificationHold::META );
					$order->update_meta_data( Queue::PENDING, 'yes' );
					$order->save_meta_data();
					$order->read_meta_data( true );
					if ( NotificationHold::held( $order ) || Queue::data( $order ) !== $data || $order->get_meta( NotificationHold::RELEASED ) !== $event ) {
						throw new \RuntimeException( 'intake_notification_readback_failed' );
					}
					foreach ( $state['entries'] as $id => $entry ) {
						if ( $order->get_id() === (int) $entry['order'] || $id === $order->get_meta( BusinessRecord::REQUEST ) ) {
							unset( $state['entries'][ $id ] );
						}
					}
					IntakeStore::save( $state );
					wc_transaction_query( 'commit' );
					return $event;
				} catch ( \Throwable $error ) {
					wc_transaction_query( 'rollback' );
					wp_cache_delete( IntakeStore::OPTION, 'options' );
					wp_cache_delete( $job, 'post_meta' );
					wp_cache_delete( $job, 'posts' );
					if ( $note > 0 ) {
						clean_comment_cache( $note );
					}
					$order->read_meta_data( true );
					return self::failed();
				}
			}
		);
		return is_array( $result ) || $result instanceof WP_Error ? $result : self::failed();
	}

	/** Storage failure preserves the original review hold. */
	private static function failed(): WP_Error {
		return new WP_Error( 'notification_release_failed', __( 'The notification could not be released. Reload the inquiry before trying again.', 'linker-commerce' ) );
	}
}

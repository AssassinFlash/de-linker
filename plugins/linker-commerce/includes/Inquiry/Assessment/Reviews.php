<?php
/**
 * Revisioned staff review, using private Woo order notes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;
use WP_Error;

/** Raw model evidence and customer/account state are never written here. */
final class Reviews {

	public const META   = '_linker_customer_review';
	public const EVENT  = '_linker_customer_review_event';
	public const ERASED = '_linker_customer_evidence_erased';

	/**
	 * Current revision; legacy overrides are imported on the first change.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return array<string, mixed>
	 */
	public static function state( WC_Order $order ): array {
		$state = $order->get_meta( self::META );
		return is_array( $state ) ? $state : array( 'revision' => 0 );
	}

	/**
	 * Private structured events in chronological order.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return list<array<string, mixed>>
	 */
	public static function history( WC_Order $order ): array {
		$events = array();
		foreach ( wc_get_order_notes(
			array(
				'order_id' => $order->get_id(),
				'type'     => 'internal',
				'order'    => 'ASC',
			)
		) as $note ) {
			$event = get_comment_meta( $note->id, self::EVENT, true );
			if ( is_array( $event ) ) {
				$events[] = array_merge( $event, array( 'id' => $note->id ) );
			}
		}
		return $events;
	}

	/**
	 * Compare-and-append. Nonce verification belongs to the HTTP controller.
	 *
	 * @param int                  $id Inquiry id.
	 * @param int                  $revision Revision displayed in the form.
	 * @param string               $operation correct, withdraw or evidence.
	 * @param array<string, mixed> $input Sanitized form values.
	 * @return array<string, mixed>|WP_Error New current state or explicit failure.
	 */
	public static function save( int $id, int $revision, string $operation, array $input ): array|WP_Error {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return new WP_Error( 'forbidden', __( 'You cannot review this inquiry.', 'linker-commerce' ) );
		}
		if ( ! in_array( $operation, array( 'correct', 'withdraw', 'evidence' ), true ) || ( 'correct' === $operation && ! in_array( $input['label'] ?? '', array( 'normal', 'suspected_spam', 'uncertain' ), true ) ) ) {
			return new WP_Error( 'invalid_review', __( 'Please choose a valid assessment.', 'linker-commerce' ) );
		}
		if ( 'evidence' === $operation && ( '' === ( $input['note'] ?? '' ) || ! in_array( $input['source'] ?? '', array( 'company_website', 'official_registry', 'official_vat', 'other' ), true ) || ! \Linker\Commerce\Registration\Website::valid( (string) ( $input['url'] ?? '' ) ) || (int) ( $input['observed_at'] ?? 0 ) <= 0 ) ) {
			return new WP_Error( 'invalid_evidence', __( 'Enter the source, its URL, when you checked it and the relevant finding.', 'linker-commerce' ) );
		}
		$result = new WP_Error( 'review_busy', __( 'Another review is being saved. Reload this inquiry before trying again.', 'linker-commerce' ) );
		Lock::run(
			'review-' . $id,
			static function () use ( $id, $revision, $operation, $input, &$result ): void {
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					$result = new WP_Error( 'invalid_inquiry', __( 'This inquiry is unavailable.', 'linker-commerce' ) );
					return;
				}
				$order->read_meta_data( true );
				if ( $order->get_meta( self::ERASED ) || array() === Queue::data( $order ) ) {
					$result = new WP_Error( 'invalid_inquiry', __( 'This inquiry is unavailable.', 'linker-commerce' ) );
					return;
				}
				$state = self::state( $order );
				if ( (int) $state['revision'] !== $revision ) {
					$result = new WP_Error( 'review_stale', __( 'This review has changed. Reload the inquiry to see the latest revision; your change was not saved.', 'linker-commerce' ) );
					return;
				}
				$notes = array();
				wc_transaction_query( 'start' );
				try {
					$legacy = $order->get_meta( Admin::OVERRIDE );
					if ( 0 === $revision && is_array( $legacy ) ) {
						$notes[] = self::append(
							$order,
							array_merge(
								$legacy,
								array(
									'operation' => 'legacy',
									'revision'  => 0,
								)
							)
						);
					}
					$event = array(
						'operation' => $operation,
						'revision'  => $revision + 1,
						'label'     => 'correct' === $operation ? (string) $input['label'] : '',
						'note'      => (string) ( $input['note'] ?? '' ),
						'user'      => get_current_user_id(),
						'at'        => time(),
					);
					if ( 'evidence' === $operation ) {
						$event['source']      = $input['source'];
						$event['url']         = $input['url'];
						$event['observed_at'] = $input['observed_at'];
					}
					$note_id = self::append( $order, $event );
					$notes[] = $note_id;
					$state   = array(
						'revision' => $revision + 1,
						'event'    => $note_id,
					);
					$order->update_meta_data( self::META, $state );
					if ( 'correct' === $operation ) {
						StructuredMeta::update( $order, Admin::OVERRIDE, $event );
					} elseif ( 'withdraw' === $operation ) {
						$order->delete_meta_data( Admin::OVERRIDE );
					}
					$order->save_meta_data();
					$order->read_meta_data( true );
					if ( self::state( $order ) !== $state || ( 'correct' === $operation && $order->get_meta( Admin::OVERRIDE ) !== $event ) || ( 'withdraw' === $operation && $order->get_meta( Admin::OVERRIDE ) ) ) {
						throw new \RuntimeException( 'review_readback_failed' );
					}
					wc_transaction_query( 'commit' );
					$result = $state;
				} catch ( \Throwable $error ) {
					wc_transaction_query( 'rollback' );
					foreach ( $notes as $note_id ) {
						clean_comment_cache( $note_id );
						wp_cache_delete( $note_id, 'comment_meta' );
					}
					$order->read_meta_data( true );
					$result = new WP_Error( 'review_write_failed', __( 'The review could not be saved. Reload the inquiry before trying again.', 'linker-commerce' ) );
				}
			}
		);
		return $result;
	}

	/**
	 * A generic private note carries no customer text; structured data is protected.
	 *
	 * @param WC_Order             $order Inquiry.
	 * @param array<string, mixed> $event Immutable event candidate.
	 * @throws \RuntimeException Any partial write is rolled back by the caller.
	 */
	private static function append( WC_Order $order, array $event ): int {
		$id = $order->add_order_note( __( 'Staff review recorded.', 'linker-commerce' ), 0, true );
		if ( $id <= 0 || ! add_comment_meta( $id, self::EVENT, wp_slash( $event ), true ) || get_comment_meta( $id, self::EVENT, true ) !== $event ) {
			if ( $id > 0 ) {
				clean_comment_cache( $id );
				wp_cache_delete( $id, 'comment_meta' );
			}
			throw new \RuntimeException( 'review_event_write_failed' );
		}
		return $id;
	}
}

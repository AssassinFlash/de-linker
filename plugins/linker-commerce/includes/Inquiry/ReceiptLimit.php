<?php
/**
 * Delivery state and recipient protection of inquiry acknowledgements.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\Reviews;
use Linker\Commerce\Inquiry\Assessment\SendAuthorization;
use WC_Order;

/** Only receipts consume this allowance; inquiries and team notifications continue. */
final class ReceiptLimit {

	/** The saved reason a public-door receipt was omitted. */
	public const SKIPPED_META = '_linker_receipt_skipped';

	/** Read the delivery of this order's customer acknowledgement.
	 *
	 * @param WC_Order $order Saved native inquiry.
	 * @return 'sent'|'pending'|'omitted'
	 */
	public static function delivery_state( WC_Order $order ): string {
		$order->read_meta_data( true );
		$state = AuthorizationStore::read( $order->get_id() );
		$entry = is_array( $state ) ? ( $state['jobs']['receipt'] ?? array() ) : array();
		if ( ! empty( $entry['delivered_at'] ) ) {
			return 'sent';
		}
		$reason = $order->get_meta( self::SKIPPED_META );
		if ( $order->get_meta( Reviews::ERASED ) || ! in_array( $reason, array( '', 'assessment_pending', 'review_hold' ), true ) ) {
			return 'omitted';
		}
		if ( ! is_array( $state ) ) {
			return 'pending';
		}
		if ( $state && ! SendAuthorization::receipt_source( $order, $state ) ) {
			return 'omitted';
		}
		if ( isset( $entry['id'] ) && ( empty( $entry['fixed'] ) || 'private' !== get_post_status( $entry['id'] ) ) ) {
			return 'omitted';
		}
		return ! $state && \Linker\Commerce\Mail\NotificationHold::held( $order ) ? 'omitted' : 'pending';
	}

	/** Determine the allowance for the real destination of this native receipt.
	 *
	 * @param WC_Order $order Native recipient and order.
	 * @param bool     $spend Charge at dispatch, or check current availability at handoff.
	 */
	public static function reason( WC_Order $order, bool $spend ): string {
		return \Linker\Commerce\Protection\ReceiptBudget::reason( $order->get_billing_email(), $order->get_id(), 'inquiry', $spend );
	}
}

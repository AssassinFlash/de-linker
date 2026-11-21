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
use WP_User;

/** Only receipts consume this allowance; inquiries and team notifications continue. */
final class ReceiptLimit {

	/** The saved reason a public-door receipt was omitted. */
	public const SKIPPED_META = '_linker_receipt_skipped';

	/** The current account email has been confirmed by an existing mailbox flow. */
	private const MAILBOX_CONFIRMED = '_linker_receipt_mailbox_confirmed';

	/** Woo validated the reset link delivered to this customer's mailbox.
	 *
	 * @param WP_User $user Confirmed account.
	 */
	public static function confirmed_mailbox( WP_User $user ): void {
		update_user_meta( $user->ID, self::MAILBOX_CONFIRMED, 'yes' );
	}

	/**
	 * A change of account email clears confirmation for the previous mailbox.
	 *
	 * @param int     $id Account being updated.
	 * @param WP_User $previous Account before the update.
	 */
	public static function account_updated( int $id, WP_User $previous ): void {
		$current = get_userdata( $id );
		if ( $current && 0 !== strcasecmp( $previous->user_email, $current->user_email ) ) {
			delete_user_meta( $id, self::MAILBOX_CONFIRMED );
		}
	}

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
	 * @phpstan-impure
	 * @param WC_Order $order Native recipient and order.
	 * @param bool     $spend Charge at dispatch, or check current availability at handoff.
	 */
	public static function reason( WC_Order $order, bool $spend ): string {
		$owner = $order->get_customer_id();
		$email = $order->get_billing_email();
		if ( $owner > 0 && 'yes' === get_user_meta( $owner, self::MAILBOX_CONFIRMED, true ) ) {
			$user = get_userdata( $owner );
			if ( $user && 0 === strcasecmp( $user->user_email, $email ) ) {
				return '';
			}
		}
		return \Linker\Commerce\Protection\ReceiptBudget::reason( $email, $order->get_id(), 'inquiry', $spend );
	}
}

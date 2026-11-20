<?php
/**
 * Site-wide allowance for automated public-door customer receipts.
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

	/**
	 * PR #290 round 2: a tenth of Hostinger's shared 100/24h allowance
	 * (AGENTS.md §4; docs/research/2026-10-09/mail-root-cause.md §3, §9).
	 * Same small allocation as #235. This is a fixed UTC-day window, as in
	 * #235's RateLimit, not a claim to measure the host's rolling usage.
	 */
	public const DAILY_CAP = 10;

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
		if ( 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode() ) {
			return \Linker\Commerce\Protection\ReceiptBudget::reason( $order->get_billing_email(), $order->get_id(), 'inquiry', $spend );
		}
		$limit = new RateLimit( 'public_receipts', self::DAILY_CAP, DAY_IN_SECONDS );
		$used  = $limit->spent( '' );
		if ( null === $used ) {
			return 'unavailable';
		}
		if ( $used >= self::DAILY_CAP ) {
			return 'daily_cap';
		}
		if ( ! $spend || $limit->take( '' ) ) {
			return '';
		}
		return ( $limit->spent( '' ) ?? 0 ) >= self::DAILY_CAP ? 'daily_cap' : 'unavailable';
	}

	/** Reserve a receipt atomically, independently of the connection address. */
	public function take(): bool {
		return ( new RateLimit( 'public_receipts', self::DAILY_CAP, DAY_IN_SECONDS ) )->take( '' );
	}
}

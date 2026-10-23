<?php
/**
 * Inquiries that waited a day for their Proforma invoice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Protection\BusinessDisposition;
use WC_Order;

/**
 * Block of the received inquiries still without a Proforma invoice (docs/specs/74-daily-digest.md:
 * window start is the moment the inquiry was created, and the window is more
 * than 24 hours, compared in Unix seconds). A received inquiry is the team's
 * promise to reply within one business day, so a day-old one is the daily
 * work's first block.
 */
final class InquiriesAwaitingProforma implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'inquiries_awaiting_proforma';

	/**
	 * Age an inquiry must exceed to be listed: 24 hours in seconds.
	 */
	public const WINDOW = 24 * HOUR_IN_SECONDS;

	/**
	 * Sets up the block.
	 *
	 * @param int $now Unix time of the digest, for the tests; 0 reads the clock.
	 */
	public function __construct( private readonly int $now = 0 ) {}

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return self::ID;
	}

	/**
	 * Heading of the block.
	 */
	public function title(): string {
		return __( 'Inquiries waiting for a Proforma invoice', 'linker-commerce' );
	}

	/**
	 * The received inquiries older than the window, oldest first.
	 *
	 * The window is applied here, on the creation moment the order carries,
	 * not in the order query: WooCommerce's date filter works at calendar-day
	 * granularity, the spec's window is strict to the second
	 * (docs/specs/74-daily-digest.md).
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$orders  = wc_get_orders(
			array(
				'status'  => array( Statuses::RECEIVED ),
				'limit'   => -1,
				'orderby' => 'date',
				'order'   => 'ASC',
			)
		);
		$entries = array();
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			$created = $order->get_date_created();
			if ( null !== $created && $this->timestamp() - $created->getTimestamp() > self::WINDOW && ! $this->processed( $order ) ) {
				$entries[] = $this->entry( $order, $created->getTimestamp() );
			}
		}
		return $entries;
	}

	/**
	 * Only the authenticated native employee audit proves work was disposed.
	 * A marker is only a lookup hint; missing, corrupt or unreadable evidence
	 * leaves the inquiry visible, independently of any model classification.
	 *
	 * @param WC_Order $order Native inquiry candidate.
	 */
	private function processed( WC_Order $order ): bool {
		try {
			return (bool) $order->get_meta( BusinessDisposition::META ) && BusinessDisposition::processed( $order );
		} catch ( \Throwable $error ) {
			return false;
		}
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No inquiry is waiting for more than 24 hours.', 'linker-commerce' );
	}

	/**
	 * One inquiry as the digest lists it.
	 *
	 * @param WC_Order $order   Inquiry.
	 * @param int      $created Unix time of creation.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function entry( WC_Order $order, int $created ): array {
		return array(
			'label'     => sprintf(
				/* translators: 1: inquiry number, 2: customer's company. */
				__( 'Inquiry #%1$s – %2$s', 'linker-commerce' ),
				$order->get_order_number(),
				$order->get_billing_company()
			),
			'url'       => $order->get_edit_order_url(),
			'link_text' => __( 'Open the inquiry', 'linker-commerce' ),
			'detail'    => sprintf(
				/* translators: 1: date, 2: time, 3: age. */
				__( 'Received on %1$s at %2$s (%3$s)', 'linker-commerce' ),
				Format::date( $created ),
				Format::time( $created ),
				Format::age( $created, $this->timestamp() )
			),
		);
	}

	/**
	 * Unix time of the digest.
	 */
	private function timestamp(): int {
		return $this->now > 0 ? $this->now : time();
	}
}

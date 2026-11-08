<?php
/**
 * Quotations in preparation for more than three days.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Inquiry\Statuses;
use WC_Order;

/**
 * Block of the inquiries the team moved to "Quotation in preparation" more
 * than three days ago and that are still open (docs/specs/74-daily-digest.md:
 * window start is the moment the record was last touched — the quotation
 * itself is written and sent offline, so the record's own change moment is
 * the closest honest signal — and the window is more than 3 × 24 hours,
 * compared in Unix seconds, not three calendar days).
 */
final class QuotationsInProgress implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'quotations_in_progress';

	/**
	 * Age an open quotation must exceed to be listed: 3 days in seconds.
	 */
	public const WINDOW = 3 * DAY_IN_SECONDS;

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
		return __( 'Quotations in preparation for more than 3 days', 'linker-commerce' );
	}

	/**
	 * The open quotations older than the window, oldest first.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$orders  = wc_get_orders(
			array(
				'status'  => array( Statuses::QUOTATION ),
				'limit'   => -1,
				'orderby' => 'modified',
				'order'   => 'ASC',
			)
		);
		$entries = array();
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			$modified = $order->get_date_modified();
			if ( null !== $modified && $this->timestamp() - $modified->getTimestamp() > self::WINDOW ) {
				$entries[] = $this->entry( $order, $modified->getTimestamp() );
			}
		}
		return $entries;
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No quotation has been in preparation for more than 3 days.', 'linker-commerce' );
	}

	/**
	 * One inquiry as the digest lists it.
	 *
	 * @param WC_Order $order   Inquiry.
	 * @param int      $touched Unix time the record was last touched.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function entry( WC_Order $order, int $touched ): array {
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
				__( 'In quotation preparation since %1$s at %2$s (%3$s)', 'linker-commerce' ),
				Format::date( $touched ),
				Format::time( $touched ),
				Format::age( $touched, $this->timestamp() )
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

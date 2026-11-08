<?php
/**
 * Quotations in preparation for more than three days.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Quotation\Issuer;
use WC_Order;

/**
 * Block of the inquiries whose Quotation has been out for more than three
 * days without the inquiry closing (docs/specs/74-daily-digest.md: window
 * start is the moment the Quotation was issued — the meta the Issuer writes —
 * and the window is more than 3 × 24 hours, compared in Unix seconds, not
 * three calendar days). An inquiry in the issued status without the meta
 * stays out: nobody knows when its Quotation went out.
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
	 * The issued Quotations older than the window, oldest first.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$orders  = wc_get_orders(
			array(
				'status'  => array( Statuses::QUOTATION ),
				'limit'   => -1,
				'orderby' => 'date',
				'order'   => 'ASC',
			)
		);
		$entries = array();
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			$issued = (int) $order->get_meta( Issuer::ISSUED_META );
			if ( $issued > 0 && $this->timestamp() - $issued > self::WINDOW ) {
				$entries[] = $this->entry( $order, $issued );
			}
		}
		return $entries;
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No Quotation has waited more than 3 days for a reply.', 'linker-commerce' );
	}

	/**
	 * One inquiry as the digest lists it.
	 *
	 * @param WC_Order $order  Inquiry.
	 * @param int      $issued Unix time the Quotation was issued.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function entry( WC_Order $order, int $issued ): array {
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
				/* translators: 1: Quotation number, 2: date, 3: time, 4: age. */
				__( 'Quotation %1$s issued on %2$s at %3$s (%4$s)', 'linker-commerce' ),
				(string) $order->get_meta( Issuer::NUMBER_META ),
				Format::date( $issued ),
				Format::time( $issued ),
				Format::age( $issued, $this->timestamp() )
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

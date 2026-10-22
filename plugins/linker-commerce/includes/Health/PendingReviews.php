<?php
/** Saved pending-inquiry counts in the daily digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Health;

use Linker\Commerce\Digest\Block;

/** An operational aggregate, excluding confirmed campaigns and normal model uncertainty. */
final class PendingReviews implements Block {
	/**
	 * Share the read-only admission boundary.
	 *
	 * @param ReviewSummary $summary Pending queue reader.
	 */
	public function __construct( private readonly ReviewSummary $summary = new ReviewSummary() ) {}
	/** Stable digest block identity. */
	public function id(): string {
		return 'pending_inquiry_reviews'; }
	/** Staff heading. */
	public function title(): string {
		return __( 'Inquiries awaiting staff review', 'linker-commerce' ); }
	/**
	 * Count and oldest saved time; no submitted content enters the message.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$data = $this->summary->get();
		if ( is_wp_error( $data ) ) {
			return array(
				array(
					'label'     => __( 'Pending inquiry counts are unavailable.', 'linker-commerce' ),
					'url'       => '',
					'link_text' => '',
					'detail'    => '',
				),
			);
		}
		if ( 0 === $data['count'] ) {
			return array(); }
		return array(
			array(
				/* translators: %d: saved inquiries awaiting staff review. */
				'label'     => sprintf( __( '%d saved inquiries need staff review.', 'linker-commerce' ), $data['count'] ),
				'url'       => $data['url'],
				'link_text' => __( 'Review saved inquiries', 'linker-commerce' ),
				/* translators: %s: age of the oldest saved inquiry. */
				'detail'    => sprintf( __( 'Oldest inquiry: %s ago.', 'linker-commerce' ), human_time_diff( $data['oldest'], time() ) ),
			),
		);
	}
	/** Empty is reported only after a successful aggregate query. */
	public function empty_text(): string {
		return __( 'No saved inquiry is awaiting staff review.', 'linker-commerce' ); }
}

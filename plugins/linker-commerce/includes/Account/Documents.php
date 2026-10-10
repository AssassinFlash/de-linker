<?php
/**
 * All documents of an account.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Proforma\Issuer;
use WC_Order;

/**
 * The "Documents" page of the account: every Proforma invoice and design
 * report of the customer, newest first (docs/specs/11-commerce.md, journey step 6).
 */
final class Documents {

	/**
	 * Sets up the page.
	 *
	 * @param SavedSolutions $solutions    The saved solutions.
	 * @param string         $template_dir Directory of the plugin's templates.
	 */
	public function __construct(
		private readonly SavedSolutions $solutions,
		private readonly string $template_dir
	) {}

	/**
	 * The customer's documents.
	 *
	 * @param int $customer_id Customer.
	 * @return list<array{title: string, date: int, url: string}>
	 */
	public function for_customer( int $customer_id ): array {
		$documents = array();
		$orders    = wc_get_orders(
			array(
				'customer_id'  => $customer_id,
				'limit'        => -1,
				'meta_key'     => Issuer::NUMBER_META, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- one customer's inquiries.
				'meta_compare' => 'EXISTS',
			)
		);
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			if ( '' !== (string) $order->get_meta( Issuer::NUMBER_META ) ) {
				$documents[] = array(
					/* translators: 1: Proforma number, 2: inquiry number. */
					'title' => sprintf( __( 'Proforma invoice %1$s (inquiry #%2$s)', 'linker-commerce' ), $order->get_meta( Issuer::NUMBER_META ), $order->get_order_number() ),
					'date'  => (int) $order->get_meta( Issuer::ISSUED_META ),
					'url'   => DocumentDownload::proforma_url( $order ),
				);
			}
		}
		foreach ( $this->solutions->for_customer( $customer_id ) as $solution ) {
			if ( '' !== $this->solutions->report_path( $solution->ID ) ) {
				$documents[] = array(
					// The stored name: get_the_title() would put "Private:" in front of a private post's.
					/* translators: %s: name of the saved solution. */
					'title' => sprintf( __( 'Design report: %s', 'linker-commerce' ), $solution->post_title ),
					'date'  => (int) get_post_timestamp( $solution ),
					'url'   => DocumentDownload::report_url( $solution->ID ),
				);
			}
		}
		usort( $documents, static fn ( array $a, array $b ): int => $b['date'] <=> $a['date'] );
		return $documents;
	}

	/**
	 * Prints the page; runs on its endpoint.
	 */
	public function render(): void {
		wc_get_template( 'myaccount/linker-documents.php', array( 'documents' => $this->for_customer( get_current_user_id() ) ), '', $this->template_dir );
	}
}

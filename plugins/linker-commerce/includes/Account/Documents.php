<?php
/**
 * All documents of an account.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Inquiry\Statuses;
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
		foreach ( $this->proforma_inquiries( $customer_id ) as $order ) {
			if ( ! InquiryList::has_proforma( $order ) ) {
				continue;
			}
			$url = DocumentDownload::proforma_url( $order );
			// An empty href is still a download control (#425).
			if ( '' === $url ) {
				continue;
			}
			$documents[] = array(
				/* translators: 1: Proforma number, 2: inquiry number. */
				'title' => sprintf( __( 'Proforma invoice %1$s (inquiry #%2$s)', 'linker-commerce' ), InquiryList::proforma_number( $order ), $order->get_order_number() ),
				'date'  => self::issued_at( $order ),
				'url'   => $url,
				'kind'  => 'proforma',
			);
		}
		foreach ( $this->solutions->for_customer( $customer_id ) as $solution ) {
			if ( '' !== $this->solutions->report_path( $solution->ID ) ) {
				$documents[] = array(
					// The stored name: get_the_title() would put "Private:" in front of a private post's.
					/* translators: %s: name of the saved solution. */
					'title' => sprintf( __( 'Design report: %s', 'linker-commerce' ), $solution->post_title ),
					'date'  => (int) get_post_timestamp( $solution ),
					'url'   => DocumentDownload::report_url( $solution->ID ),
					'kind'  => 'report',
				);
			}
		}
		usort( $documents, static fn ( array $a, array $b ): int => $b['date'] <=> $a['date'] );
		return $documents;
	}

	/**
	 * The customer's inquiries that may have a Proforma: one that carries the
	 * number (including after Completed), and one whose status is "Proforma
	 * invoice issued". The two queries overlap; the inquiry id decides. A status
	 * without a stored number adds no row — has_proforma() drops it.
	 *
	 * @param int $customer_id Customer.
	 * @return list<WC_Order>
	 */
	private function proforma_inquiries( int $customer_id ): array {
		$found    = array();
		$numbered = wc_get_orders(
			array(
				'customer_id'  => $customer_id,
				'limit'        => -1,
				'meta_key'     => Issuer::NUMBER_META, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- one customer's inquiries.
				'meta_compare' => 'EXISTS',
			)
		);
		$issued   = wc_get_orders(
			array(
				'customer_id' => $customer_id,
				'status'      => array( Statuses::PROFORMA ),
				'limit'       => -1,
			)
		);
		foreach ( array_merge( is_array( $numbered ) ? $numbered : array(), is_array( $issued ) ? $issued : array() ) as $order ) {
			if ( InquiryList::has_proforma( $order ) ) {
				$found[ $order->get_id() ] = $order;
			}
		}
		return array_values( $found );
	}

	/**
	 * When the Proforma was issued, or the inquiry's own date when that moment was not stored.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private static function issued_at( WC_Order $order ): int {
		$issued = (int) $order->get_meta( Issuer::ISSUED_META );
		if ( $issued > 0 ) {
			return $issued;
		}
		$created = $order->get_date_created();
		return $created instanceof \DateTimeInterface ? $created->getTimestamp() : 0;
	}

	/**
	 * Prints the page; runs on its endpoint.
	 */
	public function render(): void {
		wc_get_template( 'myaccount/linker-documents.php', array( 'documents' => $this->for_customer( get_current_user_id() ) ), '', $this->template_dir );
	}
}

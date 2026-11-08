<?php
/**
 * All documents of an account.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

/**
 * The "Documents" page of the account: the design reports of the customer's
 * saved solutions, newest first (docs/specs/11-commerce.md, journey step 6).
 * Quotations are written and sent offline by the team (owner ruling
 * 2026-11-08); they are not documents of this site.
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
	 * Prints the page; runs on its endpoint.
	 */
	public function render(): void {
		wc_get_template( 'myaccount/linker-documents.php', array( 'documents' => $this->for_customer( get_current_user_id() ) ), '', $this->template_dir );
	}
}

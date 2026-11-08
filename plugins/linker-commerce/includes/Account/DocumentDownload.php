<?php
/**
 * Downloads of a customer's documents.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Presentation\AccountLinks;
use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Presentation\Tokens;

use Linker\Commerce\Proforma\Issuer;
use WC_Order;

/**
 * The only way to a design report: a link that works for the customer it
 * belongs to and for shop staff. A visitor who is not logged in, and a
 * customer who does not own the document, get 403 (docs/specs/11-commerce.md,
 * acceptance). The design report carries no amounts (quantity, item, model
 * and scope only), so a pending or restricted owner keeps its link and file.
 * Quotations are written and sent offline by the team (owner ruling
 * 2026-11-08); they are not documents of this site.
 */
final class DocumentDownload {

	/**
	 * Query variable of a download link.
	 */
	public const QUERY_VAR = 'linker-document';

	/**
	 * Sets up the downloads.
	 *
	 * @param SavedSolutions $solutions The saved solutions.
	 */
	public function __construct(
		private readonly SavedSolutions $solutions
	) {}

	/**
	 * Link to the design report of a saved solution.
	 *
	 * The engine design report has no net prices, so a pending or restricted
	 * owner is not refused here; serve() still refuses a guest and a customer
	 * who does not own the solution.
	 *
	 * @param int $solution_id Solution.
	 */
	public static function report_url( int $solution_id ): string {
		return add_query_arg(
			array(
				self::QUERY_VAR => 'report',
				'id'            => $solution_id,
			),
			PageUrls::home()
		);
	}

	/**
	 * Answers a download link; runs on template_redirect.
	 */
	public function serve(): void {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended -- a link from an email or the account; access is decided by the logged-in user, not by a nonce.
		$kind = isset( $_GET[ self::QUERY_VAR ] ) ? sanitize_key( wp_unslash( $_GET[ self::QUERY_VAR ] ) ) : '';
		$id   = isset( $_GET['id'] ) ? absint( $_GET['id'] ) : 0;
		// phpcs:enable
		if ( '' === $kind ) {
			return;
		}
		if ( ! defined( 'DONOTCACHEPAGE' ) ) {
			define( 'DONOTCACHEPAGE', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- the page-cache convention.
		}
		nocache_headers();

		[ $owner, $path, $name ] = $this->document( $kind, $id );
		if ( ! is_user_logged_in() || ( get_current_user_id() !== $owner && ! current_user_can( 'manage_woocommerce' ) ) || 0 === $owner ) {
			$this->deny();
		}
		if ( '' === $path ) {
			wp_die( esc_html__( 'This document is not available.', 'linker-commerce' ), esc_html__( 'Document', 'linker-commerce' ), array( 'response' => 404 ) );
		}
		header( 'Content-Type: application/pdf' );
		header( 'Content-Disposition: attachment; filename="' . sanitize_file_name( $name ) . '"' );
		header( 'Content-Length: ' . (string) filesize( $path ) );
		header( 'X-Content-Type-Options: nosniff' );
		readfile( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_readfile -- streams the PDF.
		exit;
	}

	/**
	 * Owner, file path and download name of a document.
	 *
	 * @param string $kind "report".
	 * @param int    $id   Solution id.
	 * @return array{0: int, 1: string, 2: string}
	 */
	private function document( string $kind, int $id ): array {
		if ( 'report' === $kind ) {
			return array( $this->solutions->owner( $id ), $this->solutions->report_path( $id ), 'design-report-' . $id . '.pdf' );
		}
		return array( 0, '', '' );
	}

	/**
	 * Refuses the download: 403, with the way to log in.
	 */
	private function deny(): void {
		wp_die(
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- All substitutions are escaped data or escaped LC fragments.
			strtr(
				Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/document-denied.html' ),
				array(
					'{{message}}'    => esc_html__( 'This document is available to the account it belongs to. Please log in with that account.', 'linker-commerce' ),
					'{{signin-url}}' => esc_url( wc_get_page_permalink( 'myaccount' ) ),
					'{{signin}}'     => esc_html__( 'Log in', 'linker-commerce' ),
					'{{create}}'     => AccountLinks::create(),
				)
			),
			esc_html__( 'Document', 'linker-commerce' ),
			array( 'response' => 403 )
		);
	}
}

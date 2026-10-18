<?php
/**
 * Downloads of a customer's documents.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Presentation\AccountLinks;
use Linker\Commerce\Presentation\Tokens;

use Linker\Commerce\Proforma\Issuer;
use WC_Order;

/**
 * The only way to a Proforma invoice or design report: a link that works for
 * the customer it belongs to and for shop staff, and answers 403 to everyone
 * else, including visitors who are not logged in (docs/specs/11-commerce.md,
 * acceptance). The PDF in the account is the copy a customer can trust for the
 * bank details (account-workspace.md §0.2).
 */
final class DocumentDownload {

	/**
	 * Query variable of a download link.
	 */
	public const QUERY_VAR = 'linker-document';

	/**
	 * Sets up the downloads.
	 *
	 * @param PrivateFiles   $proformas Where the Proforma invoices are kept.
	 * @param SavedSolutions $solutions The saved solutions.
	 */
	public function __construct(
		private readonly PrivateFiles $proformas,
		private readonly SavedSolutions $solutions
	) {}

	/**
	 * Link to the Proforma invoice of an inquiry.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function proforma_url( WC_Order $order ): string {
		return add_query_arg(
			array(
				self::QUERY_VAR => 'proforma',
				'id'            => $order->get_id(),
			),
			home_url( '/' )
		);
	}

	/**
	 * Link to the design report of a saved solution.
	 *
	 * @param int $solution_id Solution.
	 */
	public static function report_url( int $solution_id ): string {
		return add_query_arg(
			array(
				self::QUERY_VAR => 'report',
				'id'            => $solution_id,
			),
			home_url( '/' )
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
	 * @param string $kind "proforma" or "report".
	 * @param int    $id   Inquiry or solution id.
	 * @return array{0: int, 1: string, 2: string}
	 */
	private function document( string $kind, int $id ): array {
		if ( 'proforma' === $kind ) {
			$order = wc_get_order( $id );
			if ( $order instanceof WC_Order ) {
				return array(
					$order->get_customer_id(),
					$this->proformas->path( (string) $order->get_meta( Issuer::FILE_META ) ),
					$order->get_meta( Issuer::NUMBER_META ) . '.pdf',
				);
			}
		}
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

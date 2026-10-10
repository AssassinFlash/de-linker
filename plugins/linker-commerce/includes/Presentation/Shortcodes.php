<?php
/**
 * Shortcodes that feed LiveCanvas templates with B2B data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Proforma\Issuer;
use WC_Order;
use WC_Product;

/**
 * Price gating, the empty Proforma-request gate, inquiry status, PI download
 * and the account lists: each shortcode reads an existing #11 class.
 */
final class Shortcodes {

	/**
	 * Sets up the shortcodes.
	 *
	 * @param LoginGate      $gate      The empty Proforma-request page.
	 * @param SavedSolutions $solutions Saved solutions.
	 * @param Documents      $documents Proforma invoices and design reports.
	 */
	public function __construct(
		private readonly LoginGate $gate,
		private readonly SavedSolutions $solutions,
		private readonly Documents $documents
	) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_price', array( $this, 'price' ) );
		add_shortcode( 'linker_checkout', array( $this, 'checkout' ) );
		add_shortcode( 'linker_inquiry_status', array( $this, 'inquiry_status' ) );
		add_shortcode( 'linker_proforma', array( $this, 'proforma' ) );
		add_shortcode( 'linker_saved_solutions', array( $this, 'saved_solutions' ) );
		add_shortcode( 'linker_documents', array( $this, 'documents' ) );
	}

	/**
	 * The current product's gated price HTML.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function price( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		return '<div class="linker-price font-semibold text-[#0c7f73]">' . $product->get_price_html() . '</div>';
	}

	/**
	 * The Proforma request: login gate when the draft is empty, otherwise WooCommerce's checkout.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function checkout( $atts = array() ): string {
		unset( $atts );
		if ( $this->is_empty_request() ) {
			return $this->gate->html();
		}
		return do_shortcode( '[woocommerce_checkout]' );
	}

	/**
	 * The current inquiry's status.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function inquiry_status( $atts = array() ): string {
		unset( $atts );
		$order = $this->viewed_inquiry();
		if ( ! $order instanceof WC_Order ) {
			return '';
		}
		$status = $order->get_status();
		return sprintf(
			'<p class="linker-inquiry-status inline-flex min-h-8 items-center rounded-full bg-neutral-100 px-3 text-sm font-semibold" data-status="%1$s">%2$s</p>',
			esc_attr( $status ),
			esc_html( wc_get_order_status_name( $status ) )
		);
	}

	/**
	 * A download link for the current inquiry's Proforma invoice.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function proforma( $atts = array() ): string {
		unset( $atts );
		$order = $this->viewed_inquiry();
		if ( ! $order instanceof WC_Order ) {
			return '';
		}
		$number = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( '' === $number ) {
			return '';
		}
		return sprintf(
			'<a class="linker-proforma inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%1$s">%2$s</a>',
			esc_url( DocumentDownload::proforma_url( $order ) ),
			esc_html( $number )
		);
	}

	/**
	 * The customer's saved solutions, via the existing account template.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function saved_solutions( $atts = array() ): string {
		unset( $atts );
		ob_start();
		$this->solutions->render();
		return (string) ob_get_clean();
	}

	/**
	 * The customer's documents, via the existing account template.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function documents( $atts = array() ): string {
		unset( $atts );
		ob_start();
		$this->documents->render();
		return (string) ob_get_clean();
	}

	/**
	 * Whether this is an empty Proforma request (not a confirmation or pay page).
	 */
	private function is_empty_request(): bool {
		if ( is_wc_endpoint_url( 'order-received' ) || is_wc_endpoint_url( 'order-pay' ) ) {
			return false;
		}
		return WC()->cart->is_empty();
	}

	/**
	 * The inquiry on the account's view-order page, or null.
	 */
	private function viewed_inquiry(): ?WC_Order {
		if ( ! is_wc_endpoint_url( 'view-order' ) ) {
			return null;
		}
		global $wp;
		$order = wc_get_order( absint( $wp->query_vars['view-order'] ?? 0 ) );
		return $order instanceof WC_Order ? $order : null;
	}
}

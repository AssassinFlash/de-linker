<?php
/**
 * The customer's inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Products\Publication;

use Linker\Commerce\Proforma\Issuer;
use WC_Abstract_Order;
use WC_Order;
use WC_Order_Item;
use WC_Order_Item_Product;

/**
 * WooCommerce's order list and order page as the list of inquiries: number,
 * date, status, amount, the Proforma invoice to download, "Request again",
 * and on the inquiry page each product's datasheet (docs/specs/11-commerce.md,
 * journey step 6; account-workspace.md §5.1).
 */
final class InquiryList {

	/**
	 * Product meta with the URL of the product's datasheet, a file in the
	 * site's own media library (live catalogue data, docs/research/2026-10-09/
	 * account-workspace.md §0.3).
	 */
	public const DATASHEET_META = '_delinker_datasheet_url';

	/**
	 * Column headings of the list; replaces WooCommerce's.
	 *
	 * @return array<string, string>
	 */
	public function columns(): array {
		return array(
			'order-number'  => __( 'Inquiry', 'linker-commerce' ),
			'order-date'    => __( 'Date', 'linker-commerce' ),
			'order-status'  => __( 'Status', 'linker-commerce' ),
			'order-total'   => __( 'Amount', 'linker-commerce' ),
			'order-actions' => __( 'Actions', 'linker-commerce' ),
		);
	}

	/**
	 * The actions of one inquiry: view it, download its Proforma, request it again.
	 *
	 * @param array<string, array{url: string, name: string}> $actions WooCommerce's actions.
	 * @param WC_Order                                        $order   Inquiry.
	 * @return array<string, array{url: string, name: string}>
	 */
	public function actions( array $actions, WC_Order $order ): array {
		$ours = array(
			'view' => array(
				'url'  => $order->get_view_order_url(),
				'name' => __( 'View', 'linker-commerce' ),
			),
		);
		if ( self::has_proforma( $order ) ) {
			$url = DocumentDownload::proforma_url( $order );
			// An empty href is still a download control (#425).
			if ( '' !== $url ) {
				$ours['proforma'] = array(
					'url'  => $url,
					'name' => __( 'Proforma invoice (PDF)', 'linker-commerce' ),
				);
			}
		}
		/** This filter is documented in woocommerce/includes/wc-template-functions.php */
		$again = apply_filters( 'woocommerce_valid_order_statuses_for_order_again', array( 'completed' ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own filter, applied as woocommerce_order_again_button() applies it.
		// The inquiry page has WooCommerce's own "Request again" button under the table;
		// the confirmation of an inquiry just sent offers none.
		if ( $order->has_status( $again ) && ! is_wc_endpoint_url( 'view-order' ) && ! is_wc_endpoint_url( 'order-received' ) ) {
			$ours['request-again'] = array(
				'url'  => self::request_again_url( $order ),
				'name' => __( 'Request again', 'linker-commerce' ),
			);
		}
		return $ours;
	}

	/**
	 * Older Woo orders can carry a payment method, even though the customer
	 * inquiry workspace offers no payment flow. Keep the stored order and Woo's
	 * other totals intact; this affects only the native account detail render.
	 *
	 * @param array<string, array<string, string>> $totals Woo's total rows.
	 * @return array<string, array<string, string>>
	 */
	public function customer_totals( array $totals ): array {
		if ( doing_action( 'woocommerce_view_order' ) ) {
			unset( $totals['payment_method'] );
		}
		return $totals;
	}

	/**
	 * Woo calculates and formats the historical delivery charge in the current
	 * tax display mode. The old carrier or delivery method is not an offer for a
	 * new inquiry, so omit only its suffix in the account detail.
	 *
	 * @param string $via Woo's formatted method suffix.
	 */
	public function customer_shipping_via( string $via ): string {
		return doing_action( 'woocommerce_view_order' ) ? '' : $via;
	}

	/**
	 * For a zero-cost delivery Woo returns the method name instead of an amount.
	 * Show the recorded amount, with shipping tax only in inclusive mode.
	 *
	 * @param string            $value Woo's formatted shipping value.
	 * @param WC_Abstract_Order $order Woo's order or refund.
	 * @param string            $tax_display Woo's tax display mode.
	 */
	public function customer_shipping_value( string $value, WC_Abstract_Order $order, string $tax_display ): string {
		if ( ! $order instanceof WC_Order || ! doing_action( 'woocommerce_view_order' ) || 0.0 !== (float) $order->get_shipping_total() ) {
			return $value;
		}
		$tax      = (float) $order->get_shipping_tax();
		$excludes = 'excl' === $tax_display;
		$value    = wc_price( $excludes ? 0.0 : $tax, array( 'currency' => $order->get_currency() ) );
		// Match Woo's own tax labels when its stored and display modes differ.
		$stored_including_tax = $order->get_prices_include_tax();
		if ( $tax > 0.0 && ( ( $excludes && $stored_including_tax ) || ( ! $excludes && ! $stored_including_tax ) ) ) {
			$label = $excludes ? WC()->countries->ex_tax_or_vat() : WC()->countries->inc_tax_or_vat();
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Same native filter and markup used by WC_Order::get_shipping_to_display().
			$value .= apply_filters( 'woocommerce_order_shipping_to_display_tax_label', '&nbsp;<small class="tax_label">' . $label . '</small>', $order, $tax_display );
		}
		return $value;
	}

	/**
	 * Whether the inquiry has a Proforma the customer can open.
	 *
	 * The download is the stored document. A status word without a number has
	 * no PDF yet — the bank account or a price was missing — and is not shown
	 * as a download. Issuer writes the number when the document is built.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function has_proforma( WC_Order $order ): bool {
		return '' !== self::proforma_number( $order );
	}

	/**
	 * The Proforma number as the customer reads it, or '' when none was stored.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function proforma_number( WC_Order $order ): string {
		return (string) $order->get_meta( Issuer::NUMBER_META );
	}

	/**
	 * The product's datasheet under each line of the inquiry page; runs on
	 * woocommerce_order_item_meta_end.
	 *
	 * @param int           $item_id    Line id.
	 * @param WC_Order_Item $item       Line.
	 * @param WC_Order      $order      Inquiry.
	 * @param bool          $plain_text Whether the output is plain text (emails).
	 */
	public function datasheet_link( int $item_id, WC_Order_Item $item, WC_Order $order, bool $plain_text = false ): void {
		if ( $plain_text || ! $item instanceof WC_Order_Item_Product || ! is_wc_endpoint_url( 'view-order' ) || ! Publication::is_published( $item->get_product_id() ) ) {
			return;
		}
		$product_id = Publication::canonical_id( $item->get_product_id() );
		$legacy     = (string) get_post_meta( $product_id, self::DATASHEET_META, true );
		$documents  = Publication::product_library_read( $item->get_product_id(), $legacy )['documents'];
		if ( array() === $documents ) {
			return;
		}
		$url = '';
		foreach ( $documents as $document ) {
			if ( in_array( $product_id, $document['product_ids'], true ) && ( 'datasheet' === $document['type'] || in_array( $legacy, $document['aliases'], true ) ) ) {
				$url = (string) $document['url'];
				break;
			}
		}
		if ( '' === $url ) {
			return;
		}
		printf(
			'<br><a class="linker-datasheet" href="%1$s" target="_blank" rel="noopener">%2$s</a>',
			esc_url( $url ),
			esc_html__( 'Datasheet (PDF)', 'linker-commerce' )
		);
	}

	/**
	 * WooCommerce's "order again" link of an inquiry: its products into a new solution draft.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function request_again_url( WC_Order $order ): string {
		return wp_nonce_url( add_query_arg( 'order_again', $order->get_id(), wc_get_cart_url() ), 'woocommerce-order_again' );
	}
}

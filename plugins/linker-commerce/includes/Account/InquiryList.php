<?php
/**
 * The customer's inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Proforma\Issuer;
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
		if ( '' !== (string) $order->get_meta( Issuer::NUMBER_META ) ) {
			$ours['proforma'] = array(
				'url'  => DocumentDownload::proforma_url( $order ),
				'name' => __( 'Proforma invoice (PDF)', 'linker-commerce' ),
			);
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
	 * The product's datasheet under each line of the inquiry page; runs on
	 * woocommerce_order_item_meta_end.
	 *
	 * @param int           $item_id    Line id.
	 * @param WC_Order_Item $item       Line.
	 * @param WC_Order      $order      Inquiry.
	 * @param bool          $plain_text Whether the output is plain text (emails).
	 */
	public function datasheet_link( int $item_id, WC_Order_Item $item, WC_Order $order, bool $plain_text = false ): void {
		if ( $plain_text || ! $item instanceof WC_Order_Item_Product || ! is_wc_endpoint_url( 'view-order' ) ) {
			return;
		}
		$url = (string) get_post_meta( $item->get_product_id(), self::DATASHEET_META, true );
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

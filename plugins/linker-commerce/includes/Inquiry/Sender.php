<?php
/**
 * The shared entry for sending an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\PageUrls;

use Linker\Commerce\Contact\Submission;
use WC_Order;
use WP_Error;

/**
 * Uses Woo's order storage and status-triggered mail for both public doors.
 * Callers verify the request nonce and PublicGuard before calling request() or message().
 */
final class Sender {


	/**
	 * Sends validated details with the current solution draft.
	 * Products, prices and customer identity always come from Woo's session.
	 *
	 * @param Submission           $details Validated reply details and message.
	 * @param array<string, mixed> $billing Optional account billing edits; guests cannot supply them.
	 * @return WC_Order|WP_Error Received inquiry or validation failure.
	 */
	public function request( Submission $details, array $billing = array() ): WC_Order|WP_Error {
		if ( WC()->cart->is_empty() && '' === $details->message ) {
			return new WP_Error( 'linker_inquiry_empty', __( 'Please add a product or write a message.', 'linker-commerce' ) );
		}
		foreach ( array( WC()->cart->check_cart_item_validity(), WC()->cart->check_cart_item_stock() ) as $valid ) {
			if ( $valid instanceof WP_Error ) {
				return $valid;
			}
		}
		$data = array_merge(
			BillingFields::values( $billing ),
			array(
				'billing_first_name' => $details->name,
				'billing_last_name'  => '',
				'billing_email'      => $details->email,
				'billing_company'    => $details->company,
				'order_comments'     => $details->message,
				'payment_method'     => ProformaGateway::ID,
			)
		);
		WC()->cart->calculate_totals();
		$id = WC()->checkout()->create_order( $data );
		if ( $id instanceof WP_Error ) {
			return $id;
		}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			return new WP_Error( 'linker_inquiry_create', __( 'Please try sending your inquiry again.', 'linker-commerce' ) );
		}
		$this->receive( $order, $details, 'proforma' );
		WC()->cart->empty_cart();
		return $order;
	}

	/**
	 * Sends a contact message without reading or consuming the solution draft.
	 *
	 * @param Submission           $details Validated reply details and message.
	 * @param array<string, mixed> $meta    Record meta a door adds before the mail goes (Genie's hand-off, #243).
	 */
	public function message( Submission $details, array $meta = array() ): WC_Order {
		$order = new WC_Order();
		$order->set_customer_id( get_current_user_id() );
		$order->set_created_via( 'linker_contact' );
		$order->set_address(
			array(
				'first_name' => $details->name,
				'email'      => $details->email,
				'company'    => $details->company,
			),
			'billing'
		);
		$order->set_customer_note( $details->message );
		$order->set_payment_method( ProformaGateway::ID );
		foreach ( $meta as $key => $value ) {
			$order->update_meta_data( (string) $key, $value );
		}
		$this->receive( $order, $details, 'contact' );
		return $order;
	}

	/**
	 * One stored record and status-driven mail; the receipt alone has a daily cap.
	 *
	 * @param WC_Order   $order Native inquiry.
	 * @param Submission $details Validated reply details.
	 * @param string     $source proforma or contact.
	 */
	private function receive( WC_Order $order, Submission $details, string $source ): void {
		$order->set_payment_method_title( '' );
		$this->line_language( $order, $details->locale );
		$order->update_meta_data( OrderLocale::META, $details->locale );
		$order->update_meta_data( '_linker_inquiry_source', $source );
		$order->update_meta_data( '_linker_inquiry_topic', $details->intent );
		$order->update_meta_data( ReceiptLimit::SKIPPED_META, ( new ReceiptLimit() )->take() ? '' : 'daily_cap' );
		$order->save();
		// Woo loads transactional email listeners lazily. Load before the transition.
		WC()->mailer();
		$order->update_status( Statuses::RECEIVED );
	}

	/**
	 * Admin-post cannot use the storefront's name filter; retain the canonical
	 * product id and write its translated title before notifications render.
	 *
	 * @param WC_Order $order Created inquiry.
	 * @param string   $locale Validated form language.
	 */
	private function line_language( WC_Order $order, string $locale ): void {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return;
		}
		foreach ( $order->get_items() as $item ) {
			if ( ! $item instanceof \WC_Order_Item_Product ) {
				continue;
			}
			$twin = PageUrls::twin( $item->get_product_id(), $locale );
			$name = $twin > 0 ? get_post_field( 'post_title', $twin ) : '';
			if ( '' !== $name ) {
				$item->set_name( $name );
				$item->save();
			}
		}
	}
}

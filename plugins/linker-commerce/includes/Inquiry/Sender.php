<?php
/**
 * The shared entry for sending an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Registration\VatProfile;
use WC_Customer;
use WC_Order;
use WP_Error;

/**
 * Uses Woo's order storage and status-triggered mail for both public doors.
 * Callers verify the request nonce and PublicGuard before calling submit().
 */
final class Sender {


	/**
	 * Sends validated details, optionally with the current session's draft.
	 * No customer id, products, prices or totals are accepted from the browser.
	 *
	 * @param  Submission $details    Validated reply details and message.
	 * @param  bool       $with_draft Include and empty the current solution draft.
	 * @return WC_Order|WP_Error Received inquiry, or a creation error.
	 */
	public function submit( Submission $details, bool $with_draft = true ): WC_Order|WP_Error {
		if ( $with_draft && WC()->cart->is_empty() && '' === $details->message ) {
			return new WP_Error( 'linker_inquiry_empty', __( 'Please add a product or write a message.', 'linker-commerce' ) );
		}
		$data = array(
			'billing_first_name' => $details->name,
			'billing_last_name'  => '',
			'billing_email'      => $details->email,
			'billing_company'    => $details->company,
			'order_comments'     => $details->message,
			'payment_method'     => ProformaGateway::ID,
		);
		// Address and VAT are optional existing account data, never public requirements.
		$customer                     = new WC_Customer( get_current_user_id() );
		$vat                          = $customer->get_meta( VatProfile::VAT_META );
		$data[ VatProfile::VAT_META ] = get_current_user_id() > 0 && is_string( $vat ) ? $vat : '';
		foreach ( array( 'address_1', 'address_2', 'city', 'postcode', 'country', 'state', 'phone' ) as $field ) {
			$data[ 'billing_' . $field ] = get_current_user_id() > 0 ? $customer->{ 'get_billing_' . $field }() : '';
		}
		if ( $with_draft ) {
			foreach ( array( WC()->cart->check_cart_item_validity(), WC()->cart->check_cart_item_stock() ) as $valid ) {
				if ( $valid instanceof WP_Error ) {
					return $valid;
				}
			}
			WC()->cart->calculate_totals();
			$id = WC()->checkout()->create_order( $data );
			if ( is_wp_error( $id ) ) {
				return $id;
			}
			$order = wc_get_order( $id );
		} else {
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
		}
		if ( ! $order instanceof WC_Order ) {
			return new WP_Error( 'linker_inquiry_create', __( 'Please try sending your inquiry again.', 'linker-commerce' ) );
		}
		$order->set_payment_method_title( '' );
		$this->line_language( $order, $details->locale );
		$order->update_meta_data( OrderLocale::META, $details->locale );
		$order->update_meta_data( '_linker_inquiry_source', $with_draft ? 'proforma' : 'contact' );
		$order->update_meta_data( '_linker_inquiry_topic', $details->intent );
		$order->save();
		// Woo loads transactional email listeners lazily. Load before the transition.
		WC()->mailer();
		$order->update_status( Statuses::RECEIVED );
		if ( $with_draft ) {
			WC()->cart->empty_cart();
		}
		return $order;
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
			$twin = (int) pll_get_post( $item->get_product_id(), str_starts_with( $locale, 'de' ) ? 'de' : 'en' );
			$name = $twin > 0 ? get_post_field( 'post_title', $twin ) : '';
			if ( is_string( $name ) && '' !== $name ) {
				$item->set_name( $name );
				$item->save();
			}
		}
	}
}

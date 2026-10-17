<?php
/**
 * Optional registration from a guest receipt, backed by Woo's order key.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\PageUrls;

use WC_Order;

/**
 * The receipt key proves possession; matching an email alone grants no access.
 */
final class AccountLink {


	/**
	 * Adds the claim after Woo has validated and created the account.
	 */
	public function register(): void {
		add_action( 'woocommerce_created_customer', array( $this, 'claim' ), 20 );
	}

	/**
	 * One optional entry into the existing registration page, in the inquiry's language.
	 *
	 * @param WC_Order $order Guest inquiry.
	 */
	public static function url( WC_Order $order ): string {
		$id = (int) get_option( 'woocommerce_myaccount_page_id' );
		if ( function_exists( 'pll_get_post' ) ) {
			$twin = PageUrls::twin( $id, OrderLocale::of( $order ) );
			$id   = $twin > 0 ? $twin : $id;
		}
		$url = wc_get_endpoint_url( 'register', '', (string) get_permalink( $id ) );
		return add_query_arg(
			array(
				'linker_inquiry' => $order->get_id(),
				'linker_key'     => $order->get_order_key(),
			),
			$url
		);
	}

	/**
	 * The email prefilled only after the receipt key has been verified.
	 */
	public static function email(): string {
		$order = self::requested();
		return $order ? $order->get_billing_email() : '';
	}

	/**
	 * Attach only the inquiry whose receipt the new customer holds.
	 *
	 * @param int $user_id Woo-created customer.
	 */
	public function claim( int $user_id ): void {
		$order = self::requested();
		$user  = get_userdata( $user_id );
		if ( ! $order || ! $user || strtolower( $order->get_billing_email() ) !== strtolower( $user->user_email ) ) {
			return;
		}
		$order->set_customer_id( $user_id );
		$order->save();
	}

	/**
	 * Only Woo's guest record with its full secret key may be claimed.
	 */
	private static function requested(): ?WC_Order {
     // phpcs:disable WordPress.Security.NonceVerification.Recommended -- Woo's order key is the authorization; this read itself does not write.
		$id  = isset( $_GET['linker_inquiry'] ) && is_scalar( $_GET['linker_inquiry'] ) ? absint( $_GET['linker_inquiry'] ) : 0;
		$key = isset( $_GET['linker_key'] ) && is_string( $_GET['linker_key'] ) ? sanitize_text_field( wp_unslash( $_GET['linker_key'] ) ) : '';
     // phpcs:enable
		$order = $id > 0 ? wc_get_order( $id ) : false;
		return $order instanceof WC_Order && 0 === $order->get_customer_id() && '' !== $key && hash_equals( $order->get_order_key(), $key ) ? $order : null;
	}
}

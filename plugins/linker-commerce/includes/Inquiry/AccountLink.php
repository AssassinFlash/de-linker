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
use WP_User;

/**
 * The receipt key proves possession; matching an email alone grants no access.
 */
final class AccountLink {

	private const CLAIM = '_linker_receipt_claim';

	/**
	 * Adds the claim after Woo has validated and created the account.
	 */
	public function register(): void {
		add_action( 'woocommerce_created_customer', array( $this, 'claim' ), 20 );
		add_filter( 'woocommerce_login_redirect', array( $this, 'after_login' ), 20, 2 );
		add_filter( 'woocommerce_registration_redirect', array( $this, 'after_registration' ), 20 );
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
		return self::with_receipt( $url, $order );
	}

	/**
	 * Carry the native receipt between the account's login and registration forms.
	 *
	 * @param string $url Local account form URL.
	 */
	public static function continue_at( string $url ): string {
		$order = self::requested();
		return $order && '' !== $url ? self::with_receipt( $url, $order ) : $url;
	}

	/**
	 * Add Woo’s receipt credentials to the local account path.
	 *
	 * @param string   $url   Local account form URL.
	 * @param WC_Order $order Native receipt.
	 */
	private static function with_receipt( string $url, WC_Order $order ): string {
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
		return $order && 0 === $order->get_customer_id() ? $order->get_billing_email() : '';
	}

	/**
	 * Attach only the inquiry whose receipt the new customer holds.
	 *
	 * @param int $user_id Woo-created customer.
	 */
	public function claim( int $user_id ): void {
		$order = self::requested();
		if ( $order && 0 === $order->get_customer_id() ) {
			self::claim_guest_order( $order, $user_id );
		}
	}

	/**
	 * Follow the receipt after Woo has authenticated the existing account.
	 *
	 * @param string  $redirect Woo's normal destination.
	 * @param WP_User $user     Authenticated customer.
	 */
	public function after_login( string $redirect, WP_User $user ): string {
		return self::destination( $redirect, (int) $user->ID );
	}

	/**
	 * Follow the receipt after Woo signs in a newly registered customer.
	 *
	 * @param string $redirect Woo's normal destination.
	 */
	public function after_registration( string $redirect ): string {
		return self::destination( $redirect, get_current_user_id() );
	}

	/**
	 * Open the exact receipt inquiry for its customer. A signed-in visitor can also reopen the emailed link.
	 *
	 * @param string $redirect Woo's account destination.
	 * @param int    $user_id  Authenticated customer.
	 */
	public static function destination( string $redirect, int $user_id ): string {
		$order = self::requested();
		if ( ! $order || $user_id < 1 ) {
			return $redirect;
		}
		if ( 0 === $order->get_customer_id() ) {
			self::claim_guest_order( $order, $user_id );
		}
		return $order->get_customer_id() === $user_id ? $order->get_view_order_url() : $redirect;
	}

	/**
	 * Record the verified guest-to-account transfer on this order.
	 *
	 * @param WC_Order $order   Guest inquiry whose native order key was verified.
	 * @param int      $user_id Woo-created or authenticated customer.
	 */
	private static function claim_guest_order( WC_Order $order, int $user_id ): void {
		$user  = get_userdata( $user_id );
		$email = strtolower( $order->get_billing_email() );
		if ( ! $user || '' === $email || strtolower( $user->user_email ) !== $email ) {
			return;
		}
		$order->set_customer_id( $user_id );
		$order->update_meta_data( self::CLAIM, $user_id );
		$order->save();
	}

	/**
	 * Whether the current account still owns the inquiry claimed with its receipt at this address.
	 *
	 * @param WC_Order $order Saved inquiry.
	 */
	public static function claimed_by_customer( WC_Order $order ): bool {
		$owner = $order->get_customer_id();
		if ( $owner < 1 || $owner !== (int) $order->get_meta( self::CLAIM ) ) {
			return false;
		}
		$user = get_userdata( $owner );
		return $user && '' !== $order->get_billing_email() && 0 === strcasecmp( $order->get_billing_email(), $user->user_email );
	}

	/**
	 * Resolve only the Woo order identified by its complete receipt key.
	 */
	private static function requested(): ?WC_Order {
     // phpcs:disable WordPress.Security.NonceVerification.Recommended -- Woo's order key is the authorization; this read itself does not write.
		$id  = isset( $_GET['linker_inquiry'] ) && is_scalar( $_GET['linker_inquiry'] ) ? absint( $_GET['linker_inquiry'] ) : 0;
		$key = isset( $_GET['linker_key'] ) && is_string( $_GET['linker_key'] ) ? sanitize_text_field( wp_unslash( $_GET['linker_key'] ) ) : '';
     // phpcs:enable
		$order = $id > 0 ? wc_get_order( $id ) : false;
		return $order instanceof WC_Order && '' !== $key && hash_equals( $order->get_order_key(), $key ) ? $order : null;
	}
}

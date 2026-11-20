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

	private const CLAIM    = '_linker_receipt_claim';
	private const RECOVERY = 'linker_inquiry_after_reset';

	/**
	 * Adds the claim after Woo has validated and created the account.
	 */
	public function register(): void {
		add_action( 'woocommerce_created_customer', array( $this, 'claim' ), 20 );
		add_action( 'lostpassword_post', array( $this, 'remember_recovery' ) );
		add_filter( 'woocommerce_login_redirect', array( $this, 'after_login' ), 20, 2 );
		add_filter( 'woocommerce_registration_redirect', array( $this, 'after_registration' ), 20 );
	}

	/**
	 * One optional entry into the existing registration page, in the inquiry's language.
	 *
	 * @param WC_Order $order Guest inquiry.
	 */
	public static function url( WC_Order $order ): string {
		return self::with_receipt( wc_get_endpoint_url( 'register', '', self::account_url( $order ) ), $order );
	}

	/**
	 * The private email takes the recipient to the right native account form.
	 *
	 * @param WC_Order $order Issued inquiry.
	 */
	public static function quotation_url( WC_Order $order ): string {
		$account = self::account_url( $order );
		if ( $order->get_customer_id() > 0 ) {
			return add_query_arg( array( 'linker_quotation' => $order->get_id() ), $account );
		}
		if ( ! email_exists( $order->get_billing_email() ) ) {
			$account = wc_get_endpoint_url( 'register', '', $account );
		}
		return self::with_receipt( $account, $order );
	}

	/**
	 * Account page in the inquiry's recorded language.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private static function account_url( WC_Order $order ): string {
		$id   = (int) get_option( 'woocommerce_myaccount_page_id' );
		$twin = PageUrls::twin( $id, OrderLocale::of( $order ) );
		return (string) get_permalink( $twin > 0 ? $twin : $id );
	}

	/**
	 * Carry the native receipt between the account's login and registration forms.
	 *
	 * @param string $url Local account form URL.
	 */
	public static function continue_at( string $url ): string {
		$args = self::request_args();
		return $args && '' !== $url ? add_query_arg( $args, $url ) : $url;
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
		$args  = self::request_args();
		$order = isset( $args['linker_key'] ) ? self::order( $args ) : null;
		return $order && 0 === $order->get_customer_id() ? $order->get_billing_email() : '';
	}

	/**
	 * Attach only the inquiry whose receipt the new customer holds.
	 *
	 * @param int $user_id Woo-created customer.
	 */
	public function claim( int $user_id ): void {
		$args  = self::request_args();
		$order = isset( $args['linker_key'] ) ? self::order( $args ) : null;
		if ( $order && 0 === $order->get_customer_id() ) {
			self::claim_guest_order( $order, $user_id );
		}
	}

	/**
	 * Keep the target on the browser that submitted Woo's password recovery form.
	 * The reset email keeps its native URL.
	 */
	public function remember_recovery(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce validates the lost-password form before firing lostpassword_post.
		if ( ! isset( $_POST['wc_reset_password'] ) ) {
			return;
		}
		$args = self::request_args();
		if ( $args && self::order( $args ) ) {
			$session = WC()->session;
			$session->set( self::RECOVERY, $args );
			if ( $session instanceof \WC_Session_Handler ) {
				$session->set_customer_session_cookie( true );
			}
		}
	}

	/**
	 * Follow the receipt after Woo has authenticated the existing account.
	 *
	 * @param string  $redirect Woo's normal destination.
	 * @param WP_User $user     Authenticated customer.
	 */
	public function after_login( string $redirect, WP_User $user ): string {
		$args = self::request_args();
		WC()->initialize_session();
		$session = WC()->session;
		$saved   = $session->get( self::RECOVERY );
		if ( is_array( $saved ) ) {
			$session->__unset( self::RECOVERY );
			$args = $args ? $args : $saved;
		}
		return self::follow( $redirect, (int) $user->ID, $args, true );
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
	 * Open an inquiry already owned by this account. Navigation never transfers it.
	 *
	 * @param string $redirect Woo's account destination.
	 * @param int    $user_id  Authenticated customer.
	 */
	public static function destination( string $redirect, int $user_id ): string {
		return self::follow( $redirect, $user_id, self::request_args(), false );
	}

	/**
	 * A signed-in receipt holder can confirm transfer of a matching guest inquiry.
	 */
	public static function awaiting_confirmation(): ?WC_Order {
		$args  = self::request_args();
		$order = isset( $args['linker_key'] ) ? self::order( $args ) : null;
		if ( $order && 0 === $order->get_customer_id() && self::matches_email( $order, get_current_user_id() ) ) {
			return $order;
		}
		return null;
	}

	/**
	 * Resolve Woo's authenticated form submissions and read-only account links.
	 *
	 * @param string                                                              $redirect Woo destination without an owned inquiry.
	 * @param int                                                                 $user_id Authenticated customer.
	 * @param array{linker_inquiry?:int,linker_key?:string,linker_quotation?:int} $args Account link parameters.
	 * @param bool                                                                $claim Whether a native account submission authorizes transfer.
	 */
	private static function follow( string $redirect, int $user_id, array $args, bool $claim ): string {
		$order = self::order( $args );
		if ( ! $order || $user_id < 1 ) {
			return $redirect;
		}
		if ( $claim && isset( $args['linker_key'] ) && 0 === $order->get_customer_id() ) {
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
		if ( ! self::matches_email( $order, $user_id ) ) {
			return;
		}
		$order->set_customer_id( $user_id );
		$order->update_meta_data( self::CLAIM, (string) $user_id );
		$order->save();
	}

	/**
	 * Whether Woo's billing email matches this authenticated account.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param int      $user_id Customer.
	 */
	private static function matches_email( WC_Order $order, int $user_id ): bool {
		$user = get_userdata( $user_id );
		return $user && '' !== $order->get_billing_email() && 0 === strcasecmp( $order->get_billing_email(), $user->user_email );
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
		return self::matches_email( $order, $owner );
	}

	/**
	 * Account destinations accept a receipt or a quotation ID, never a redirect URL.
	 *
	 * @return array{linker_inquiry?:int,linker_key?:string,linker_quotation?:int} Site-local inquiry reference.
	 */
	public static function request_args(): array {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended -- Local navigation; possession and ownership are checked before use.
		if ( isset( $_GET['linker_inquiry'], $_GET['linker_key'] ) && is_scalar( $_GET['linker_inquiry'] ) && is_string( $_GET['linker_key'] ) ) {
			return array(
				'linker_inquiry' => absint( $_GET['linker_inquiry'] ),
				'linker_key'     => sanitize_text_field( wp_unslash( $_GET['linker_key'] ) ),
			);
		}
		return isset( $_GET['linker_quotation'] ) && is_scalar( $_GET['linker_quotation'] ) ? array( 'linker_quotation' => absint( $_GET['linker_quotation'] ) ) : array();
		// phpcs:enable
	}

	/**
	 * A bare quotation ID can locate an owned inquiry but cannot transfer it.
	 *
	 * @param array{linker_inquiry?:int,linker_key?:string,linker_quotation?:int} $args Parsed account link parameters.
	 */
	private static function order( array $args ): ?WC_Order {
		$id    = (int) ( $args['linker_inquiry'] ?? $args['linker_quotation'] ?? 0 );
		$order = $id > 0 ? wc_get_order( $id ) : false;
		if ( ! $order instanceof WC_Order ) {
			return null;
		}
		if ( isset( $args['linker_key'] ) && ( '' === $args['linker_key'] || ! hash_equals( $order->get_order_key(), $args['linker_key'] ) ) ) {
			return null;
		}
		return $order;
	}
}

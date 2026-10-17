<?php
/**
 * Browser adapter of the shared inquiry sender.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Mail\LocaleSwitch;
use WC_Order;
use WP_Error;

/**
 * Transport, public-request checks, and a redirect; Sender owns the write.
 */
final class Handler {


	public const ACTION = 'linker_inquiry';
	public const NONCE  = 'linker_inquiry_nonce';

	/**
	 * Both guests and account holders use this adapter.
	 */
	public function register(): void {
		add_action( 'admin_post_nopriv_' . self::ACTION, array( $this, 'handle' ) );
		add_action( 'admin_post_' . self::ACTION, array( $this, 'handle' ) );
	}

	/**
	 * Verifies before creating any inquiry or email.
	 *
	 * @param  array<string, mixed> $post Unslashed fields.
	 * @return WC_Order|WP_Error The received inquiry or validation failure.
	 */
	public function process( array $post ): WC_Order|WP_Error {
		$language = isset( $post['lang'] ) && is_string( $post['lang'] ) ? sanitize_key( $post['lang'] ) : null;
		$locale   = new LocaleSwitch();
		$locale->to( OrderLocale::current( $language ) );
		try {
			$guard = new PublicGuard();
			$nonce = $post[ self::NONCE ] ?? '';
			if ( is_string( $nonce ) && wp_verify_nonce( $nonce, self::ACTION ) && $guard->is_limited() ) {
				return new WP_Error( 'linker_inquiry_throttled', __( 'We received several messages from this connection. Please try again later or write to sales@de-linker.com.', 'linker-commerce' ) );
			}
			if ( ! is_string( $nonce ) || ! wp_verify_nonce( $nonce, self::ACTION ) || ! $guard->allows( $post ) ) {
				return new WP_Error( 'linker_inquiry_invalid', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
			}
			$details = Submission::from_post( $post, false );
			$result  = $details instanceof WP_Error ? $details : ( new Sender() )->request( $details, $post );
			if ( $result instanceof WC_Order ) {
				$guard->record();
			}
			return $result;
		} finally {
			$locale->back();
		}
	}

	/**
	 * Native form transport, retaining entries on a validation failure.
	 */
	public function handle(): void {
		wc_load_cart();
     // phpcs:ignore WordPress.Security.NonceVerification.Missing -- process() verifies before every write.
		$post   = wp_unslash( $_POST );
		$result = $this->process( $post );
		if ( $result instanceof WC_Order ) {
			WC()->session->set( 'linker_inquiry_fields', null );
			WC()->session->set( 'linker_inquiry_error', null );
			WC()->session->set( 'linker_inquiry_error_locale', null );
			wp_safe_redirect( $result->get_checkout_order_received_url() );
		} else {
			if ( WC()->session instanceof \WC_Session_Handler ) {
				WC()->session->set_customer_session_cookie( true );
			}
			$fields = array();
			foreach ( array( 'name', 'email', 'company', 'message' ) as $key ) {
				$fields[ $key ] = isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? sanitize_textarea_field( $post[ $key ] ) : '';
			}
			WC()->session->set( 'linker_inquiry_fields', $fields );
			$language = isset( $post['lang'] ) && is_string( $post['lang'] ) ? sanitize_key( $post['lang'] ) : null;
			WC()->session->set( 'linker_inquiry_error', $result->get_error_message() );
			WC()->session->set( 'linker_inquiry_error_locale', OrderLocale::current( $language ) );
			wp_safe_redirect( Checkout::request_url( OrderLocale::current( $language ) ) );
		}
		exit;
	}
}

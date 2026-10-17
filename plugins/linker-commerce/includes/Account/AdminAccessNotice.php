<?php
/**
 * Explains WooCommerce's protective admin redirect to signed-in customers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Presentation\Tokens;

/** Native protection decides access; LC owns the explanation's composition. */
final class AdminAccessNotice {

	/** Registers only an adapter on Woo's existing protection. */
	public function register(): void {
		add_filter( 'woocommerce_prevent_admin_access', array( $this, 'protect' ), PHP_INT_MAX );
		add_filter( 'wc_get_template', array( $this, 'template' ), 50, 2 );
		add_shortcode( 'linker_admin_access_field', array( $this, 'field' ) );
	}

	/**
	 * Keeps Woo's access decision and marks its next redirect, only when denied.
	 *
	 * @param bool $prevent Woo's final access decision.
	 */
	public function protect( bool $prevent ): bool {
		if ( $prevent ) {
			add_filter( 'wp_redirect', array( $this, 'destination' ) );
		}
		return $prevent;
	}

	/**
	 * Woo calls wp_safe_redirect immediately after the protection filter.
	 * Consume this adapter once, leaving every later redirect untouched.
	 *
	 * @param string $location Woo's account destination.
	 */
	public function destination( string $location ): string {
		remove_filter( 'wp_redirect', array( $this, 'destination' ) );
		$id = (int) get_option( 'woocommerce_myaccount_page_id' );
		if ( function_exists( 'pll_get_post' ) ) {
			// Polylang's front-end preference survives an admin request, where
			// pll_current_language() does not describe the last page visited.
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only, whitelisted language preference.
			$language = isset( $_COOKIE['pll_language'] ) && 'de' === $_COOKIE['pll_language'] ? 'de' : 'en';
			$twin     = (int) pll_get_post( $id, $language );
			$id       = $twin > 0 ? $twin : $id;
		}
		$account = get_permalink( $id );
		return add_query_arg( 'admin-access', 'staff', is_string( $account ) ? $account : $location );
	}

	/** Whether this is the signed-in customer's explanation, never a staff page. */
	public static function requested(): bool {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only page selection; no account or permission changes.
		return isset( $_GET['admin-access'] ) && 'staff' === $_GET['admin-access']
			&& is_account_page() && is_user_logged_in()
			&& ! current_user_can( 'edit_posts' )
			&& ! current_user_can( 'manage_woocommerce' )
			// phpcs:ignore WordPress.WP.Capabilities.Unknown -- WooCommerce WC_Admin::prevent_admin_access explicitly accepts this capability.
			&& ! current_user_can( 'view_admin_dashboard' );
	}

	/**
	 * Takes precedence over the pending-review card only on this explanation.
	 *
	 * @param string $path Located template.
	 * @param string $name Woo template name.
	 */
	public function template( string $path, string $name ): string {
		return 'myaccount/my-account.php' === $name && self::requested()
			? dirname( __DIR__, 2 ) . '/templates/myaccount/admin-access.php' : $path;
	}

	/** LC fragment; PHP supplies escaped data through the field tag below. */
	public static function output(): void {
		if ( self::requested() ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- repository LC markup; field() escapes every dynamic value.
			echo do_shortcode( Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/admin-access.html' ) );
		}
	}

	/**
	 * Scalar LC fields. Logout and staff login are WordPress's nonce-protected
	 * native URLs; no replacement authentication handler or redirect parameter.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function field( $atts = array() ): string {
		if ( ! self::requested() ) {
			return '';
		}
		switch ( $atts['key'] ?? '' ) {
			case 'title':
				return esc_html__( 'Linker staff only', 'linker-commerce' );
			case 'identity':
				/* translators: %s: email of the signed-in customer. */
				return esc_html( sprintf( __( 'You are signed in as %s (customer account).', 'linker-commerce' ), wp_get_current_user()->user_email ) );
			case 'explanation':
				return esc_html__( 'The admin area is for Linker staff only.', 'linker-commerce' );
			case 'staff-label':
				return esc_html__( 'Sign out and sign in as staff', 'linker-commerce' );
			case 'account-label':
				return esc_html__( 'Go to my account', 'linker-commerce' );
			case 'staff-url':
				return esc_url( wp_logout_url( wp_login_url( admin_url() ) ) );
			case 'account-url':
				return esc_url( wc_get_page_permalink( 'myaccount' ) );
		}
		return '';
	}
}

<?php
/**
 * Explains WooCommerce's protective admin redirect to signed-in customers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Presentation\Tokens;
use Linker\I18n\Languages;

/** Native protection decides access; LC owns the explanation's composition. */
final class AdminAccessNotice {

	/** Woo's own decision, attached to the existing WordPress login session. */
	private const DECISION_KEY = 'linker_admin_access_prevented';

	/** Registers only an adapter on Woo's existing protection. */
	public function register(): void {
		// Read Woo's final decision after other filters; never change it.
		add_filter( 'woocommerce_prevent_admin_access', array( $this, 'protect' ), PHP_INT_MAX );
		// PendingGate selects its card at 40; this explicit notice follows at 50.
		add_filter( 'wc_get_template', array( $this, 'template' ), 50, 2 );
		add_shortcode( 'linker_admin_access_field', array( $this, 'field' ) );
	}

	/**
	 * Keeps Woo's access decision and marks its next redirect, only when denied.
	 *
	 * @param bool $prevent Woo's final access decision.
	 */
	public function protect( bool $prevent ): bool {
		if ( is_user_logged_in() ) {
			$token    = wp_get_session_token();
			$sessions = \WP_Session_Tokens::get_instance( get_current_user_id() );
			$session  = $sessions->get( $token );
			if ( is_array( $session ) ) {
				$session[ self::DECISION_KEY ] = $prevent;
				$sessions->update( $token, $session );
			}
		}
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
		if ( defined( 'PLL_COOKIE' ) && class_exists( Languages::class ) && function_exists( 'pll_get_post' ) ) {
			// The admin request has no front-end language route; resolve the
			// configured Polylang cookie through the shared language helper.
			$languages = new Languages();
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only language preference validated by Languages::exists().
			$preferred = filter_var( wp_unslash( $_COOKIE[ PLL_COOKIE ] ?? '' ), FILTER_UNSAFE_RAW, FILTER_NULL_ON_FAILURE );
			$language  = is_string( $preferred ) ? sanitize_key( $preferred ) : '';
			$language  = $languages->exists( $language ) ? $language : Languages::SOURCE;
			$id        = $languages->post_translation( $id, $language ) ?? $id;
		}
		$account = get_permalink( $id );
		return add_query_arg( 'admin-access', 'staff', is_string( $account ) ? $account : $location );
	}

	/** Whether this signed-in session has Woo's recorded denial to explain. */
	public static function requested(): bool {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only page selection; no account or permission changes.
		return isset( $_GET['admin-access'] ) && 'staff' === $_GET['admin-access']
			&& is_account_page() && is_user_logged_in()
			&& true === ( \WP_Session_Tokens::get_instance( get_current_user_id() )->get( wp_get_session_token() )[ self::DECISION_KEY ] ?? null );
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

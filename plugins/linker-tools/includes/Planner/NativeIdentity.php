<?php
/**
 * Native WordPress/Woo ownership proof at the REST boundary.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WC_Session_Handler;
use WP_Error;
use WP_REST_Request;

/** See research/2026-10-23-planning-gateway/NATIVE-IDENTITY.md. */
final class NativeIdentity {

	/** Woo's native guest-nonce filter binds actions starting with woocommerce. */
	public const NONCE_ACTION = 'woocommerce_linker_planner_v1';

	/**
	 * Resolve only after WordPress REST authentication has run.
	 *
	 * @param WP_REST_Request $request Native request.
	 * @return Principal|WP_Error Verified native principal or explicit refusal.
	 */
	public function resolve( WP_REST_Request $request ): Principal|WP_Error {
		$user = get_current_user_id();
		if ( $user > 0 ) {
			$nonce = (string) $request->get_header( 'x-wp-nonce' );
			return '' !== wp_get_session_token() && false !== wp_verify_nonce( $nonce, 'wp_rest' )
				? new Principal( 'user', self::user_subject( $user ) )
				: Failure::make( 'session', 401 );
		}
		// Core deliberately downgrades cookie-auth requests without a REST nonce
		// to user zero. Never reinterpret that logged-in browser as a guest.
		if ( false !== wp_validate_auth_cookie( '', 'logged_in' ) ) {
			return Failure::make( 'rest_nonce', 403 );
		}
		$session = $this->session();
		if ( is_wp_error( $session ) ) {
			return $session;
		}
		$proof = $this->guest_cookie( $session );
		if ( null === $proof || $proof['id'] !== $session->get_customer_id() || $this->row_expiry( $proof['id'] ) <= time() ) {
			return Failure::make( 'guest_cookie', 401 );
		}
		if ( false === wp_verify_nonce( (string) $request->get_header( 'x-linker-planner-nonce' ), self::NONCE_ACTION ) ) {
			return Failure::make( 'guest_nonce', 403 );
		}
		return new Principal( 'guest', self::guest_subject( $proof['id'] ) );
	}

	/**
	 * Create a native session only on actual bootstrap interaction.
	 * A new cookie is never accepted as a presented ownership proof here.
	 *
	 * @param WP_REST_Request $request Native bootstrap request.
	 * @return array{principal:Principal,confirmed:bool,expires:int,query_scope:string,nonce:string}|WP_Error Native bootstrap context.
	 */
	public function bootstrap( WP_REST_Request $request ): array|WP_Error {
		if ( get_current_user_id() > 0 ) {
			$principal = $this->resolve( $request );
			if ( is_wp_error( $principal ) ) {
				return $principal;
			}
			// Core wp-login can finish before Woo has loaded its session. Let
			// Woo emit the native migration event for the presented guest now.
			$session = $this->session();
			if ( is_wp_error( $session ) ) {
				return $session;
			}
			$cookie = wp_parse_auth_cookie( '', 'logged_in' );
			return $this->context( $principal, true, is_array( $cookie ) ? (int) $cookie['expiration'] : 0, wp_get_session_token(), wp_create_nonce( 'wp_rest' ) );
		}
		if ( false !== wp_validate_auth_cookie( '', 'logged_in' ) ) {
			return Failure::make( 'rest_nonce', 403 );
		}
		$session = $this->session();
		if ( is_wp_error( $session ) ) {
			return $session;
		}
		$proof     = $this->guest_cookie( $session );
		$confirmed = null !== $proof && $proof['id'] === $session->get_customer_id() && $this->row_expiry( $proof['id'] ) > time();
		if ( ! $confirmed ) {
			// A row deleted by native logout/migration is not revived as an owner.
			// Use Woo's own reset: CartToken clones and stale numeric user IDs
			// cannot become a guest principal.
			$session->destroy_session();
			$session->set( 'linker_planner_seen', true );
			$session->set_customer_session_cookie( true );
			$session->save_data();
		}
		$id     = (string) $session->get_customer_id();
		$expiry = $this->row_expiry( $id );
		if ( ! self::guest_id( $id ) || $expiry <= time() || headers_sent() ) {
			return Failure::make( 'guest_persistence', 503 );
		}
		if ( $confirmed ) {
			$expiry = min( $expiry, $proof['expires'] );
		}
		return $this->context( new Principal( 'guest', self::guest_subject( $id ) ), $confirmed, $expiry, $id, wp_create_nonce( self::NONCE_ACTION ) );
	}

	/**
	 * Load the native Woo session exactly once.
	 *
	 * @return WC_Session_Handler|WP_Error Current native handler.
	 */
	public function session(): WC_Session_Handler|WP_Error {
		if ( ! function_exists( 'WC' ) ) {
			return Failure::make( 'woocommerce', 503 );
		}
		$woo = WC();
		$woo->initialize_session();
		return $woo->session instanceof WC_Session_Handler ? $woo->session : Failure::make( 'session_handler', 503 );
	}

	/**
	 * Native signature reader plus the expiry check Woo's reader omits.
	 * No row check here: the native login hook runs after deleting that row.
	 *
	 * @param WC_Session_Handler $session Native handler.
	 * @return array{id:string,expires:int}|null Verified presented cookie.
	 */
	public function guest_cookie( WC_Session_Handler $session ): ?array {
		$cookie = $session->get_session_cookie();
		if ( ! is_array( $cookie ) || count( $cookie ) !== 4 || ! is_string( $cookie[0] ) || ! self::guest_id( $cookie[0] ) || ! ctype_digit( (string) $cookie[1] ) || (int) $cookie[1] <= time() ) {
			return null;
		}
		return array(
			'id'      => $cookie[0],
			'expires' => (int) $cookie[1],
		);
	}

	/**
	 * Recognise the current native guest ID format.
	 *
	 * @param string $id ID produced by Woo 11.2's generate_customer_id.
	 */
	public static function guest_id( string $id ): bool {
		return 1 === preg_match( '/\At_[a-zA-Z0-9]{30}\z/', $id );
	}

	/**
	 * Derive a private subject from a verified native guest.
	 *
	 * @param string $id Verified native guest ID, never request JSON.
	 */
	public static function guest_subject( string $id ): string {
		return 'wp:' . get_current_blog_id() . ':guest:' . wp_hash( 'linker-planner-guest:v1|' . $id, 'auth', 'sha256' );
	}

	/**
	 * Account identity survives session and WordPress salt rotation.
	 * The engine workspace belongs to this site's deployment.
	 *
	 * @param int $user Verified native user ID.
	 */
	public static function user_subject( int $user ): string {
		return 'wp:' . get_current_blog_id() . ':user:' . $user;
	}

	/**
	 * Fresh row check, independent of Woo's session-data cache.
	 *
	 * @param string $id Native session key.
	 */
	private function row_expiry( string $id ): int {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- native ownership revocation must bypass the cached session data.
		return (int) $wpdb->get_var( $wpdb->prepare( 'SELECT session_expiry FROM %i WHERE session_key = %s', $wpdb->prefix . 'woocommerce_sessions', $id ) );
	}

	/**
	 * Build bootstrap metadata without exposing the native session token.
	 *
	 * @param Principal $principal Verified owner.
	 * @param bool      $confirmed Whether the native cookie was presented.
	 * @param int       $expires Native cookie/row expiry.
	 * @param string    $session Native session token, never returned.
	 * @param string    $nonce Native nonce.
	 * @return array{principal:Principal,confirmed:bool,expires:int,query_scope:string,nonce:string} Private gateway context.
	 */
	private function context( Principal $principal, bool $confirmed, int $expires, string $session, string $nonce ): array {
		return array(
			'principal'   => $principal,
			'confirmed'   => $confirmed,
			'expires'     => $expires,
			'query_scope' => wp_hash( 'linker-planner-query:v1|' . $principal->kind . '|' . $principal->subject . '|' . $session, 'nonce', 'sha256' ),
			'nonce'       => $nonce,
		);
	}
}

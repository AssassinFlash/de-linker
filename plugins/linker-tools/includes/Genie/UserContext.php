<?php
/**
 * The customer's identity, carried from the browser's turn to the service's
 * ability calls — and nowhere else.
 *
 * The service calls the read-only abilities anonymously; `linker/inquiry-status`
 * is the one that answers about *this* customer, and the service holds no
 * WordPress session (docs/specs/13-genie.md §B). The shell therefore mints a
 * short-lived, signed token for the signed-in customer, hands it to the
 * service with the turn, and the service sends it back on that one ability
 * call as `X-Linker-User-Context`; this class accepts it — on requests to
 * `/wp-abilities/` and no other route, and only while it is valid.
 *
 * The token is not a capability: it names a user for one request, expires two
 * minutes after it is minted, and grants nothing the ability itself does not
 * already allow (every ability here is read-only; the write actions are the
 * browser's own REST calls, which carry the customer's cookie).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Mints and accepts the user-context token.
 */
class UserContext {

	/**
	 * The header the service sends back.
	 */
	public const HEADER = 'X-Linker-User-Context';

	/**
	 * Seconds a token stays valid.
	 */
	public const TTL = 120;

	/**
	 * The route family the token is accepted on.
	 */
	public const ROUTE = '/wp-abilities/';

	/**
	 * Registers the authentication seam; runs during plugin registration.
	 */
	public function register(): void {
		add_filter( 'determine_current_user', array( $this, 'determine' ), 20 );
	}

	/**
	 * The signed-in customer's token, or '' for a guest.
	 */
	public function mint(): string {
		$user = (int) get_current_user_id();
		if ( $user < 1 ) {
			return '';
		}
		$expiry  = time() + self::TTL;
		$payload = $user . '|' . $expiry;
		return $payload . '|' . $this->sign( $payload );
	}

	/**
	 * The user a token names, 0 when it is missing, malformed, tampered with
	 * or expired.
	 *
	 * @param string $token The token.
	 */
	public function user_id( string $token ): int {
		$parts = explode( '|', $token );
		if ( 3 !== count( $parts ) ) {
			return 0;
		}
		list( $user, $expiry, $signature ) = $parts;
		if ( ! ctype_digit( $user ) || ! ctype_digit( $expiry ) ) {
			return 0;
		}
		if ( (int) $expiry < time() ) {
			return 0;
		}
		$expected = $this->sign( $user . '|' . $expiry );
		if ( ! hash_equals( $expected, $signature ) ) {
			return 0;
		}
		return (int) $user;
	}

	/**
	 * The current user for this request: the cookie's own, or the token's when
	 * the request is an ability call that carries one.
	 *
	 * @param int|false $user_id The user WordPress determined so far.
	 * @return int|false
	 */
	public function determine( $user_id ) {
		if ( $user_id || ! $this->is_ability_request() ) {
			return $user_id;
		}
		if ( ! isset( $_SERVER['HTTP_X_LINKER_USER_CONTEXT'] ) ) {
			return $user_id;
		}
		$token = sanitize_text_field( wp_unslash( (string) $_SERVER['HTTP_X_LINKER_USER_CONTEXT'] ) );
		$user  = $this->user_id( $token );
		return $user > 0 ? $user : $user_id;
	}

	/**
	 * Whether this request is one the token may authenticate.
	 */
	protected function is_ability_request(): bool {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the URI is only searched for the abilities route, never stored or echoed.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( (string) $_SERVER['REQUEST_URI'] ) : '';
		return str_contains( $uri, self::ROUTE );
	}

	/**
	 * The token's signature, over the site's own auth salt.
	 *
	 * @param string $payload `user|expiry`.
	 */
	protected function sign( string $payload ): string {
		return hash_hmac( 'sha256', self::HEADER . $payload, wp_salt( 'auth' ) );
	}
}

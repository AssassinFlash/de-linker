<?php
/**
 * The customer's identity, carried from the browser's turn to the service's
 * ability calls — and nowhere else.
 *
 * The service holds no WordPress session (docs/specs/13-genie.md §B). Some
 * abilities answer for *this* customer: `linker/inquiry-status` lists their
 * inquiries, `linker/read-solution` reads their own saved solution (#496), and
 * `linker/search-products` / `linker/get-product` carry the prices their account
 * sees (#242). The shell therefore mints a short-lived, signed token for the
 * signed-in customer, hands it to the service with the turn, and the service
 * sends it back on those calls as `X-Linker-User-Context`. This class signs the
 * request in as that customer only while WordPress dispatches one of those
 * abilities (`ABILITIES`, matched against the route WordPress parsed, never the
 * address text), and signs it out again after the answer, which it marks
 * `no-store, private`.
 *
 * The token is not a capability: it names a user, is valid for `TTL` seconds
 * after it is minted (nothing marks it used — the window is the whole of its
 * life), and grants nothing the ability itself does not already allow (every
 * ability here is read-only; the write actions are the browser's own REST
 * calls, which carry the customer's cookie).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_REST_Request;
use WP_REST_Response;

/**
 * Mints and accepts the user-context token.
 */
class UserContext {

	/**
	 * The header the service sends back.
	 */
	public const HEADER = 'X-Linker-User-Context';

	/**
	 * Seconds a token stays valid: twice the shell's 60 s turn timeout
	 * (Proxy::post, 'timeout' => 60.0). The token is minted when the turn is
	 * sent and must outlive the longest turn the shell waits for, the
	 * service's post-run price lookups included (their deadline keeps the turn
	 * under the same 60 s, services/genie prices.LOOKUP_DEADLINE); measured
	 * turns on g242 took 4–10 s (tests/e2e genie-prices.spec.ts, 2026-10-18).
	 */
	public const TTL = 120;

	/**
	 * The abilities whose answer depends on the customer: the only ones a
	 * token signs in (the service's abilities.USER_CONTEXT_ABILITIES).
	 */
	public const ABILITIES = array( 'linker/inquiry-status', 'linker/read-solution', 'linker/search-products', 'linker/get-product' );

	/**
	 * Whether this request was signed in by a token (and must be signed out
	 * again after the answer).
	 *
	 * @var bool
	 */
	private bool $entered = false;

	/**
	 * Registers the dispatch seam; runs during plugin registration.
	 */
	public function register(): void {
		add_filter( 'rest_pre_dispatch', array( $this, 'enter' ), 10, 3 );
		add_filter( 'rest_post_dispatch', array( $this, 'leave' ), 10, 3 );
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
	 * Signs the request in as the token's customer when WordPress dispatches
	 * one of `ABILITIES` as a read; runs on `rest_pre_dispatch`, before the
	 * ability's permission check and callback. A session WordPress already
	 * established (the cookie) always wins.
	 *
	 * @param mixed $result  The answer another filter already decided, or null.
	 * @param mixed $server  The REST server.
	 * @param mixed $request The request, its route parsed by WordPress.
	 * @return mixed
	 */
	public function enter( $result, $server, $request ) {
		unset( $server );
		if ( null !== $result || ! $request instanceof WP_REST_Request || ! $this->in_scope( $request ) || is_user_logged_in() ) {
			return $result;
		}
		$header = $request->get_header( 'x_linker_user_context' );
		$user   = is_string( $header ) ? $this->user_id( sanitize_text_field( wp_unslash( $header ) ) ) : 0;
		if ( $user > 0 ) {
			$this->entered = true;
			wp_set_current_user( $user );
		}
		return $result;
	}

	/**
	 * Signs the token's customer out again after the answer, and keeps that
	 * answer out of every cache; runs on `rest_post_dispatch`. WordPress
	 * decides its own no-cache headers before dispatch, when this request was
	 * still a guest's.
	 *
	 * @param mixed $response The answer.
	 * @param mixed $server   The REST server.
	 * @param mixed $request  The request.
	 * @return mixed
	 */
	public function leave( $response, $server, $request ) {
		unset( $server, $request );
		if ( ! $this->entered ) {
			return $response;
		}
		$this->entered = false;
		wp_set_current_user( 0 );
		if ( $response instanceof WP_REST_Response ) {
			$response->header( 'Cache-Control', 'no-store, private' );
		}
		return $response;
	}

	/**
	 * Whether WordPress is dispatching a read of one of `ABILITIES`.
	 *
	 * @param WP_REST_Request $request The request.
	 *
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 */
	private function in_scope( WP_REST_Request $request ): bool {
		if ( 'GET' !== $request->get_method() ) {
			return false;
		}
		if ( 1 !== preg_match( '#^/wp-abilities/v1/abilities/(.+)/run$#', (string) $request->get_route(), $match ) ) {
			return false;
		}
		return in_array( $match[1], self::ABILITIES, true );
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

<?php
/**
 * Pseudonymous buckets, distinct from native authentication and authorization.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** A browser cookie is not proof of a person; account/site/connection caps remain. */
final class Identity {
	public const COOKIE = 'linker_public_browser';

	/**
	 * Only hashes are exposed to policy, never the raw browser credential.
	 *
	 * @param string $browser Pseudonymous browser hash.
	 * @param string $account Pseudonymous account hash, empty for guests.
	 */
	public function __construct( public readonly string $browser, public readonly string $account ) {}

	/**
	 * Create a minimal one-day HttpOnly cookie only on actual protected interaction.
	 * Cookie lifetime follows the daily allowance in #508, not a tracking purpose.
	 *
	 * @return self|WP_Error Server identity or explicit cookie/header failure.
	 */
	public static function current(): self|WP_Error {
		if ( ! self::ensure_browser_cookie() ) {
			return new WP_Error( 'linker_admission_cookie', 'Public admission could not start.' );
		}
		$key  = (string) $_COOKIE[ self::COOKIE ]; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- ensure_browser_cookie has validated the exact hexadecimal value.
		$user = get_current_user_id();
		return new self(
			hash_hmac( 'sha256', 'public-browser|' . $key, wp_salt( 'auth' ) ),
			self::account( $user )
		);
	}

	/** Establish the same anonymous owner on the displayed form and on its submission. */
	public static function ensure_browser_cookie(): bool {
		$key = isset( $_COOKIE[ self::COOKIE ] ) && is_string( $_COOKIE[ self::COOKIE ] ) ? $_COOKIE[ self::COOKIE ] : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Must match the complete fixed-format cookie below.
		if ( 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $key ) ) {
			if ( headers_sent() ) {
				return false;
			}
			$key = bin2hex( random_bytes( 16 ) );
			if ( ! setcookie(
				self::COOKIE,
				$key,
				array(
					'expires'  => time() + DAY_IN_SECONDS,
					'path'     => '/',
					'secure'   => is_ssl(),
					'httponly' => true,
					'samesite' => 'Lax',
				)
			) ) {
				return false;
			}
			$_COOKIE[ self::COOKIE ] = $key;
		}
		return true;
	}

	/**
	 * Account buckets can be resolved by native verified-email privacy callbacks.
	 *
	 * @param int $id Native account id.
	 */
	public static function account( int $id ): string {
		return $id > 0 ? hash_hmac( 'sha256', 'public-account|' . $id, wp_salt( 'auth' ) ) : '';
	}

	/**
	 * Recipient normalization is shared by mail budgets and privacy lookup.
	 *
	 * @param string $email Already validated destination address.
	 */
	public static function recipient( string $email ): string {
		return hash_hmac( 'sha256', 'public-recipient|' . strtolower( trim( $email ) ), wp_salt( 'auth' ) );
	}

	/** Proofs bind the current account context; the browser budget bucket survives login. */
	public function binding(): string {
		return hash_hmac( 'sha256', $this->browser . '|' . $this->account, wp_salt( 'nonce' ) );
	}

	/** Account privacy association does not impose another verification quota.
	 *
	 * @return string[] Private native privacy owner associations.
	 */
	public function owners(): array {
		return '' === $this->account ? array() : array( Allowance::owner_for( $this->account ) );
	}
}

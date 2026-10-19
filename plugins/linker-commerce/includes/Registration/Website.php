<?php
/**
 * The company website offered as a verification value at registration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * The site asks for a company website or a VAT ID because the owner verifies a
 * new account by hand (AGENTS.md §2, 2026-10-17). The website is the value that
 * works in every country (#224 dossier §6.4: an EU business website must name
 * its owner). It is stored as an absolute URL so the review card's link opens.
 */
final class Website {

	/**
	 * Customer meta holding the normalized address.
	 */
	public const META = 'linker_company_website';

	/**
	 * A written address as a stored URL; '' stays ''. A bare host gets https://.
	 *
	 * @param string $value The entered value.
	 */
	public static function normalize( string $value ): string {
		$value = trim( $value );
		if ( '' === $value ) {
			return '';
		}
		if ( ! preg_match( '#^[a-z][a-z0-9+.-]*://#i', $value ) ) {
			$value = 'https://' . $value;
		}
		return esc_url_raw( $value );
	}

	/**
	 * Whether the written value is an http(s) address with a dotted host and no
	 * credentials. The pattern follows the accepted prototype's own check
	 * (docs/prototypes/2026-10-17-registration/registration-prototype.js:257):
	 * optional scheme, no whitespace, a dot in the host and at least two
	 * characters after it. No DNS lookup: a registration must not depend on a
	 * host resolving at that moment.
	 *
	 * @param string $value The entered value.
	 */
	public static function valid( string $value ): bool {
		$url = self::normalize( $value );
		if ( '' === $url ) {
			return false;
		}
		$parts = wp_parse_url( $url );
		if ( ! is_array( $parts ) || ! isset( $parts['host'] ) || isset( $parts['user'] ) || isset( $parts['pass'] ) ) {
			return false;
		}
		$scheme = strtolower( (string) ( $parts['scheme'] ?? '' ) );
		$host   = (string) $parts['host'];
		if ( ! in_array( $scheme, array( 'http', 'https' ), true ) || ! str_contains( $host, '.' ) ) {
			return false;
		}
		return 1 === preg_match( '/\.[^\s.]{2,}$/', $host ) && ! preg_match( '/\s/', $url );
	}
}

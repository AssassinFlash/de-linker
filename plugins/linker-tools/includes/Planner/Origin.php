<?php
/**
 * Same-origin browser admission, independent of project ownership.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_REST_Request;

/** Native cookies and nonces are still required after this check. */
final class Origin {

	/**
	 * Check browser origin evidence against the configured site.
	 *
	 * @param WP_REST_Request $request Native REST request.
	 */
	public static function allows( WP_REST_Request $request ): bool {
		$site   = self::origin( home_url( '/' ) );
		$origin = (string) $request->get_header( 'origin' );
		$fetch  = (string) $request->get_header( 'sec-fetch-site' );
		if ( in_array( $fetch, array( 'cross-site', 'same-site' ), true ) || null === $site ) {
			return false;
		}
		if ( '' !== $origin ) {
			return self::origin( $origin ) === $site;
		}
		$referer = (string) $request->get_header( 'referer' );
		return '' !== $referer ? self::origin( $referer ) === $site : 'same-origin' === $fetch;
	}

	/**
	 * Parse a URL into its exact network origin.
	 *
	 * @param string $url Browser or native site URL.
	 * @return array{string,string,int}|null Scheme, host and effective port.
	 */
	private static function origin( string $url ): ?array {
		$value = wp_parse_url( $url );
		if ( ! is_array( $value ) || ! isset( $value['scheme'], $value['host'] ) || isset( $value['user'] ) || isset( $value['pass'] ) ) {
			return null;
		}
		$scheme = strtolower( $value['scheme'] );
		if ( ! in_array( $scheme, array( 'http', 'https' ), true ) ) {
			return null;
		}
		return array( $scheme, strtolower( $value['host'] ), $value['port'] ?? ( 'https' === $scheme ? 443 : 80 ) );
	}
}

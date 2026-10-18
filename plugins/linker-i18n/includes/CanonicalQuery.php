<?php
/**
 * The language canonical redirect keeps query values whole.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Polylang's canonical redirect removes the language segment from the whole
 * URL with a global pattern, the query string included: a same-site address
 * passed as a query value loses its /de/ and becomes a 404 when the team
 * opens the contact or inquiry source link
 * (docs/research/2026-10-17-i18n-audit/AUDIT.md, M8).
 *
 * This filter restores a query value that differs from the requested one by
 * exactly that removal. Other query changes WordPress made stay as they are;
 * external values are not this site's address and are not touched.
 */
final class CanonicalQuery {

	/**
	 * Restores the requested query values Polylang's canonical redirect
	 * corrupted; runs on pll_check_canonical_url.
	 *
	 * @param string|false $url      Redirect URL, false when Polylang redirects nowhere.
	 * @param mixed        $language The language Polylang detected (unused).
	 * @return string|false
	 */
	public function url( $url, $language = null ) {
		unset( $language );
		$requested = function_exists( 'pll_get_requested_url' ) ? pll_get_requested_url() : '';
		return $this->restore( $url, $requested );
	}

	/**
	 * Restores the requested query values from WordPress's canonical
	 * redirect; runs on redirect_canonical.
	 *
	 * @param string|false $redirect_url  Redirect URL.
	 * @param string       $requested_url The URL the visitor requested.
	 * @return string|false
	 */
	public function redirect( $redirect_url, $requested_url ) {
		return $this->restore( $redirect_url, $requested_url );
	}

	/**
	 * The redirect with the requested values restored.
	 *
	 * @param string|false $redirect  Redirect URL.
	 * @param string       $requested The requested URL.
	 * @return string|false
	 */
	public function restore( $redirect, string $requested ) {
		if ( ! is_string( $redirect ) || '' === $redirect || '' === $requested || $redirect === $requested ) {
			return $redirect;
		}
		$original_query = wp_parse_url( $requested, PHP_URL_QUERY );
		if ( ! is_string( $original_query ) || '' === $original_query ) {
			return $redirect;
		}
		parse_str( $original_query, $original );
		$redirect_query = wp_parse_url( $redirect, PHP_URL_QUERY );
		parse_str( is_string( $redirect_query ) ? $redirect_query : '', $redirected );

		$restored = $redirected;
		$changed  = false;
		foreach ( $redirected as $key => $value ) {
			$wanted = $original[ $key ] ?? null;
			if ( ! is_string( $wanted ) || ! is_string( $value ) || $wanted === $value ) {
				continue;
			}
			if ( $this->corrupted( $wanted, $value ) ) {
				$restored[ $key ] = $wanted;
				$changed          = true;
			}
		}
		if ( ! $changed ) {
			return $redirect;
		}
		$parts    = preg_split( '/(?=[?#])/', $redirect, 2 );
		$base     = is_array( $parts ) ? (string) $parts[0] : $redirect;
		$fragment = is_array( $parts ) && isset( $parts[1] ) && str_starts_with( $parts[1], '#' ) ? $parts[1] : '';
		return $base . '?' . http_build_query( $restored ) . $fragment;
	}

	/**
	 * Whether the redirect value is the requested one with the language
	 * segment removed — the corruption Polylang's global pattern makes in a
	 * same-site address.
	 *
	 * @param string $requested Value the visitor's URL carried.
	 * @param string $redirect  Value the redirect carries.
	 */
	private function corrupted( string $requested, string $redirect ): bool {
		$absolute = str_starts_with( $requested, '/' ) && ! str_starts_with( $requested, '//' );
		if ( ! $absolute ) {
			$host           = (string) wp_parse_url( home_url(), PHP_URL_HOST );
			$requested_host = (string) wp_parse_url( $requested, PHP_URL_HOST );
			if ( '' === $host || '' === $requested_host || strtolower( $host ) !== strtolower( $requested_host ) ) {
				return false;
			}
		}
		$stripped = str_replace( '/de/', '/', $requested );
		$stripped = (string) preg_replace( '#/de$#', '', $stripped );
		return $stripped === $redirect;
	}
}

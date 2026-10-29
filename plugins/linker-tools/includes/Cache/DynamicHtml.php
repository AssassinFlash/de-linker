<?php
/**
 * Keeps per-request HTML out of the public page cache.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Cache;

/**
 * Official no-cache controls for HTML that must not be shared.
 *
 * LiteSpeed Cache 7.9.2 reads DONOTCACHEPAGE when it emits
 * X-LiteSpeed-Cache-Control, after the template has rendered. The same
 * constant is the page-cache convention used by other caches.
 * litespeed_control_set_nocache is that plugin's public action. This class
 * does not write litespeed.conf.cache-exc; the host exclusion "?" remains
 * the server-side query rule, and the front-end request check below repeats
 * it so a query URL is not stored if that option is absent.
 *
 * The Genie dock on an ordinary page prints an anonymous wp_rest nonce and a
 * site HMAC mail stamp. That is not a public-cache exclusion: logged-out
 * wp_rest is user 0, and the stamp remains valid for its one-day life.
 */
final class DynamicHtml {

	/**
	 * Hooks the query-string check after LiteSpeed's default cacheable mark.
	 */
	public static function register(): void {
		add_action( 'wp', array( self::class, 'front_request' ), 6 );
	}

	/**
	 * A front-end HTML request with a query string is not a public cache entry.
	 *
	 * REST stays eligible for LiteSpeed's separate REST cache. Admin and AJAX
	 * are not this page cache.
	 */
	public static function front_request(): void {
		// Cache matching compares the raw URI. Sanitizing it would change the "?" rule.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- same bytes LiteSpeed compares.
		if ( ! is_string( $uri ) ) {
			$uri = '';
		}
		if ( self::blocks_public_cache( is_admin(), wp_doing_ajax(), self::rest_request(), $uri ) ) {
			self::forbid( 'query string' );
		}
	}

	/**
	 * Whether a front-end HTML request with this URI must stay out of the public cache.
	 *
	 * A query string matches the host cache-exc entry "?" (substring of the URI).
	 * Admin, AJAX and REST are left to their own controls. Dynamic tools and
	 * forms call forbid() from the shortcode that renders them.
	 *
	 * @param bool   $admin wp-admin request.
	 * @param bool   $ajax  admin-ajax request.
	 * @param bool   $rest  REST or JSON request.
	 * @param string $uri   Raw request URI.
	 */
	public static function blocks_public_cache( bool $admin, bool $ajax, bool $rest, string $uri ): bool {
		if ( $admin || $ajax || $rest ) {
			return false;
		}
		return str_contains( $uri, '?' );
	}

	/**
	 * Marks this request uncacheable. Safe to call more than once.
	 *
	 * @param string $reason Short reason for the LiteSpeed log.
	 */
	public static function forbid( string $reason ): void {
		if ( ! defined( 'DONOTCACHEPAGE' ) ) {
			define( 'DONOTCACHEPAGE', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- the page-cache convention.
		}
		if ( class_exists( '\LiteSpeed\Control' ) ) {
			do_action( 'litespeed_control_set_nocache', $reason ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache's public no-cache action.
		}
		if ( function_exists( 'nocache_headers' ) && ! headers_sent() ) {
			nocache_headers();
		}
	}

	/**
	 * REST must not inherit the HTML query exclusion.
	 */
	private static function rest_request(): bool {
		return ( defined( 'REST_REQUEST' ) && REST_REQUEST )
			|| ( function_exists( 'wp_is_json_request' ) && wp_is_json_request() );
	}
}

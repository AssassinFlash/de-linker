<?php
/**
 * Cache controls shared by published documents and their index.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/** LiteSpeed applies the current site's prefix to both its tags and its purges. */
final class DocumentCache {
	public const PUBLIC_CONTROL  = 'public, max-age=86400, stale-while-revalidate=3600';
	public const PRIVATE_CONTROL = 'no-store, private, max-age=0';

	/**
	 * Tag an authorized response before the web server stores it.
	 *
	 * @param string[] $tags Publication dependencies.
	 * @param int      $ttl Seconds to retain this response at the origin.
	 */
	public static function allow( array $tags, int $ttl ): void {
		do_action( 'litespeed_tag_add', $tags ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed API.
		do_action( 'litespeed_control_force_public', 'Published document' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed API.
		do_action( 'litespeed_control_set_ttl', $ttl ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed API.
		header_register_callback(
			static function () use ( $tags, $ttl ): void {
				$headers = headers_list();
				if ( ! preg_grep( '/^X-LiteSpeed-Tag:\s*\S/i', $headers ) ) {
					if ( ! defined( 'LSWCP_TAG_PREFIX' ) || ! has_action( 'litespeed_purge' ) ) {
						header( 'X-LiteSpeed-Cache-Control: no-cache,no-store' );
						return;
					}
					// LiteSpeed Tag::output() uses this namespace for public tags on this blog.
					$prefix = LSWCP_TAG_PREFIX . ( is_multisite() ? get_current_blog_id() : '' ) . '_';
					header( 'X-LiteSpeed-Tag: ' . implode( ',', array_map( static fn( string $tag ): string => $prefix . $tag, $tags ) ) );
				}
				if ( ! preg_grep( '/^X-LiteSpeed-Cache-Control:/i', $headers ) ) {
					header( 'X-LiteSpeed-Cache-Control: public, max-age=' . $ttl );
				}
			}
		);
	}

	/**
	 * Mark a versioned, partial, or rejected document request as uncacheable at the edge.
	 *
	 * @param bool $error Whether the response represents an error.
	 */
	public static function forbid( bool $error ): void {
		if ( ! defined( 'DONOTCACHEPAGE' ) ) {
			define( 'DONOTCACHEPAGE', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress cache convention.
		}
		do_action( 'litespeed_control_set_nocache', 'Document non-cacheable response' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed API.
		if ( $error ) {
			nocache_headers();
		}
		header_register_callback(
			static function () use ( $error ): void {
				header( 'X-LiteSpeed-Cache-Control: no-cache,no-store' );
				header_remove( 'X-LiteSpeed-Tag' );
				if ( $error ) {
					header_remove( 'Link' );
					header_remove( 'Content-Disposition' );
					header( 'X-Robots-Tag: noindex, nofollow' );
				}
			}
		);
	}

	/**
	 * Dependency shared by native attachment writes and original PDF URLs.
	 *
	 * @param string $relative Path under the uploads directory.
	 */
	public static function path_tag( string $relative ): string {
		return 'LK.pdf.' . substr( hash( 'sha256', ltrim( $relative, '/' ) ), 0, 12 );
	}

	/**
	 * Purge every tag in the current web response or native WP-CLI purge queue.
	 *
	 * @param string[] $tags Affected documents and index.
	 */
	public static function purge( array $tags ): void {
		foreach ( array_unique( $tags ) as $tag ) {
			do_action( 'litespeed_purge', $tag ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed API.
		}
	}
}

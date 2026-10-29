<?php
/**
 * Keeps a commerce form that carries a per-request secret out of the public page cache.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cache;

/**
 * Official no-cache controls for a form this plugin renders.
 *
 * Query-string exclusion is registered by the tools plugin. This class does
 * not write the host cache option.
 */
final class DynamicHtml {

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
}

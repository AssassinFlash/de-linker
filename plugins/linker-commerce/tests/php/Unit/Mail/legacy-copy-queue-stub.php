<?php
/**
 * The legacy plugin's copy queue, present on the review instances and absent
 * from this plugin's unit tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

if ( ! function_exists( 'tv_b2b_queue_business_mail_copies' ) ) {
	/**
	 * Stand-in for the function the legacy plugin registers. The silence test
	 * only needs the name to exist and to be callable.
	 *
	 * @param array<string, mixed> $args Arguments.
	 * @return array<string, mixed>
	 */
	function tv_b2b_queue_business_mail_copies( array $args ): array { // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedFunctionFound -- the legacy plugin's own name; the silence matches it.
		return $args;
	}
}

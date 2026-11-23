<?php
/**
 * Genie actions with a private retry receipt.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

/** Only mutations that produce a saved result need a receipt. */
final class ResourcePolicy {
	/**
	 * Map only actual mutating resource routes. Reads consume no turn allowance.
	 *
	 * @param string $route Native route.
	 * @param string $method Native method.
	 * @param bool   $select Existing conversation selection.
	 */
	public static function action( string $route, string $method, bool $select = false ): string {
		if ( ! in_array( $method, array( 'POST', 'DELETE' ), true ) ) {
			return '';
		}
		// WP_REST_Server matches registered paths with the i modifier.
		$route = strtolower( $route );
		return match ( true ) {
			in_array( $route, array( '/linker-ai/v1/genie/turn', '/linker-ai/v1/genie/turn/start' ), true ) => 'genie',
			'/linker-ai/v1/genie/solution' === $route => 'solution_save',
			'/linker-ai/v1/genie/conversations' === $route => $select ? '' : 'conversation_create',
			default => '',
		};
	}
}

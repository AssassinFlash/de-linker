<?php
/**
 * Bounded lexical request gate before WordPress's native JSON parser.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;
use WP_REST_Request;

/** Strings are scanned without allocating a second decoded document. */
final class BodyGate {

	/**
	 * Reject bytes/depth/encoding before native has_valid_params parses JSON.
	 * Syntax and schema validation remain with native REST and the private app.
	 *
	 * @param WP_REST_Request $request Raw native request.
	 * @return true|WP_Error Bounded input or explicit refusal.
	 */
	public function check( WP_REST_Request $request ): bool|WP_Error {
		$body   = (string) $request->get_body();
		$length = strlen( $body );
		if ( $length > Gateway::MAX_BODY_BYTES ) {
			return Failure::make( 'body', 413 );
		}
		if ( 1 !== preg_match( '/\Aapplication\/json(?:\s*;\s*charset\s*=\s*utf-8)?\z/i', (string) $request->get_header( 'content-type' ) ) ) {
			return Failure::make( 'content_type', 415 );
		}
		if ( 1 !== preg_match( '//u', $body ) ) {
			return Failure::make( 'input', 400 );
		}
		$depth  = 0;
		$quoted = false;
		$offset = 0;
		while ( $offset < $length ) {
			// Native C scanning skips large CSV/text spans without per-byte PHP
			// allocations. Escaped quote/backslash pairs cannot change depth.
			$offset += strcspn( $body, $quoted ? '"\\' : '[]{}"', $offset );
			if ( $offset >= $length ) {
				break;
			}
			$token = $body[ $offset ];
			if ( $quoted && '\\' === $token ) {
				$offset += 2;
				continue;
			}
			if ( '"' === $token ) {
				$quoted = ! $quoted;
			} elseif ( '[' === $token || '{' === $token ) {
				++$depth;
				if ( $depth > Gateway::MAX_JSON_DEPTH ) {
					return Failure::make( 'input_depth', 400 );
				}
			} elseif ( --$depth < 0 ) {
				return Failure::make( 'input', 400 );
			}
			++$offset;
		}
		return true;
	}
}

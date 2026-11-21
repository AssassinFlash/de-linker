<?php
/**
 * The bot guard of Genie's public forms.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/** Native contact fields and the connection address used for first-time browser claims. */
final class FormGuard {
	/**
	 * Whether a hidden guest form field was filled.
	 *
	 * @param array<string,mixed> $guard Submitted fields.
	 */
	public static function trapped( array $guard ): bool {
		$trap = $guard['website'] ?? '';
		return ! is_string( $trap ) || '' !== trim( $trap );
	}

	/** The connection address supplied by the web server. */
	public static function address(): string {
		return isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
	}
}

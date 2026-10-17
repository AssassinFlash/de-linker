<?php
/**
 * The HOME-based private config location used by WordPress requests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

/**
 * Keeps the environment-file directory mechanism in one reusable helper.
 * Web PHP receives HOME from wp-config.php, as the retired query encoder did.
 */
final class PrivateConfigDirectory {

	/**
	 * A file outside the web root, or empty when HOME is unavailable.
	 *
	 * @param string      $filename Private config filename, supplied by code.
	 * @param string|null $home     Fake HOME in tests; null reads the process HOME.
	 */
	public static function path( string $filename, ?string $home = null ): string {
		$directory = $home ?? getenv( 'HOME' );
		return is_string( $directory ) && '' !== $directory
			? rtrim( $directory, '/' ) . '/.config/terravolt-builder/' . $filename
			: '';
	}
}

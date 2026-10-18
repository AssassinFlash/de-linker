<?php
/**
 * The plugin's own classes resolve without Composer's classmap.
 *
 * A deploy renames the plugin directory; the 2026-10-18 deploys each logged a
 * single request where a class of this plugin was "not found" while its file
 * was on disk (the classmap and the switched tree disagreed for that request).
 * This loader maps Linker\Commerce\* onto includes/ by namespace, so a request
 * that slipped through such a moment still boots. Composer keeps handling the
 * vendor classes; this loader returns false for everything it does not own.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

/**
 * Namespace-to-file loading for this plugin, registered first in the chain.
 */
final class Autoload {

	/**
	 * The namespace this plugin owns.
	 */
	private const PREFIX = 'Linker\\Commerce\\';

	/**
	 * Loads a class of this plugin; false when the name is not ours or the file is absent.
	 *
	 * @param string $class Fully qualified class name.
	 */
	public static function load( string $class ): bool {
		if ( ! str_starts_with( $class, self::PREFIX ) ) {
			return false;
		}
		$relative = str_replace( '\\', '/', substr( $class, strlen( self::PREFIX ) ) );
		$file     = dirname( __DIR__ ) . '/includes/' . $relative . '.php';
		if ( ! is_readable( $file ) ) {
			return false;
		}
		require_once $file;
		return true;
	}

	/**
	 * Hooks the loader ahead of Composer's.
	 */
	public static function register(): void {
		spl_autoload_register( array( self::class, 'load' ), true, true );
	}
}

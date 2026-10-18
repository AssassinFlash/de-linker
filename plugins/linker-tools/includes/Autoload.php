<?php
/**
 * The plugin's own classes resolve without Composer's classmap.
 *
 * The 2026-10-18 deploys logged a request in which a class of the companion
 * plugin was "not found" while its file was on disk (classmap and switched
 * tree disagreeing for one request). This loader maps Linker\Tools\* onto
 * includes/ by namespace; Composer keeps handling the vendor classes.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * Namespace-to-file loading for this plugin, registered first in the chain.
 */
final class Autoload {

	/**
	 * The namespace this plugin owns.
	 */
	private const PREFIX = 'Linker\\Tools\\';

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

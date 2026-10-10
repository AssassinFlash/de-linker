<?php
/**
 * The engineering data files this plugin ships and the feed builds on.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

/**
 * The shipped engineering data files: data/compatibility.json and
 * data/engineering-overlay.json (docs/specs/8-engineering-data.md). One
 * reader for both, with the content version the feed reports so its readers
 * can tell a data change from a product change.
 */
final class EngineeringData {

	/**
	 * The compatibility contract: pair patterns, verdicts, conditions, documents.
	 */
	public const COMPATIBILITY_FILE = 'data/compatibility.json';

	/**
	 * The engineering overlay: components that are not products.
	 */
	public const OVERLAY_FILE = 'data/engineering-overlay.json';

	/**
	 * Product meta that holds the document list: url, title, type, lang.
	 */
	public const DOCUMENTS_META_KEY = '_linker_documents';

	/**
	 * The decoded data file, cached per request.
	 *
	 * @param string $file One of the file constants.
	 * @return array<string, mixed>|null The decoded object, null when unreadable.
	 */
	public static function json( string $file ): ?array {
		static $cache = array();
		if ( isset( $cache[ $file ] ) ) {
			return $cache[ $file ];
		}
		$path = self::path( $file );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a data file of this plugin.
		$bytes = is_readable( $path ) ? file_get_contents( $path ) : false;
		if ( false === $bytes ) {
			$cache[ $file ] = null;
			return null;
		}
		$decoded = json_decode( $bytes, true );
		if ( ! is_array( $decoded ) ) {
			$cache[ $file ] = null;
			return null;
		}
		$cache[ $file ] = $decoded;
		return $decoded;
	}

	/**
	 * The version of a data file: the sha256 of its bytes, or "missing".
	 *
	 * @param string $file One of the file constants.
	 * @return string 64 hex characters, or "missing" when the file is unreadable.
	 */
	public static function version( string $file ): string {
		$path = self::path( $file );
		$hash = is_readable( $path ) ? hash_file( 'sha256', $path ) : false;

		return is_string( $hash ) ? $hash : 'missing';
	}

	/**
	 * The absolute path of a data file.
	 *
	 * @param string $file One of the file constants.
	 * @return string
	 */
	private static function path( string $file ): string {
		return dirname( __DIR__, 2 ) . '/' . $file;
	}
}

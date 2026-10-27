<?php
/**
 * Current Woo engineering declarations and explicit one-time migration inputs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * Runtime facts, declarations and document permissions are maintained in Woo.
 * Shipped JSON is available only to explicitly invoked migration tools.
 */
final class EngineeringData {

	/**
	 * Retained one-time migration input; runtime declarations live in Woo.
	 */
	public const COMPATIBILITY_FILE = 'data/compatibility.json';

	/**
	 * One-time migration input only; runtime reference facts live in Woo.
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
		$decoded        = self::json_from( self::path( $file ) );
		$cache[ $file ] = $decoded;
		return $decoded;
	}

	/**
	 * The decoded JSON of a file path: null when it is unreadable or not a
	 * JSON object — a broken data file fails as absent, never as half-read.
	 *
	 * @param string $path Absolute path.
	 * @return array<string, mixed>|null
	 */
	public static function json_from( string $path ): ?array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a data file of this plugin.
		$bytes = is_readable( $path ) ? file_get_contents( $path ) : false;
		if ( false === $bytes ) {
			return null;
		}
		$decoded = json_decode( $bytes, true );
		// A JSON list is not a data file of this plugin; only an object reads.
		if ( ! is_array( $decoded ) || array_is_list( $decoded ) ) {
			return null;
		}

		return $decoded;
	}

	/**
	 * Content version of the current Woo projection, or missing when malformed.
	 *
	 * @param array<string,mixed>|null $manifest Reuse the caller's authority read.
	 */
	public static function compatibility_version( ?array $manifest = null ): string {
		$data = self::compatibility( $manifest );

		return is_string( $data['version'] ?? null ) && '' !== $data['version'] ? $data['version'] : 'missing';
	}

	/**
	 * One current Woo projection for PHP consumers and the engineering feed.
	 *
	 * @param array<string,mixed>|null $manifest Reuse the caller's authority read.
	 * @return array<string,mixed>|null No file fallback on absent or malformed claims.
	 */
	public static function compatibility( ?array $manifest = null ): ?array {
		$manifest ??= Publication::manifest();
		return Publication\CompatibilityClaims::projection( $manifest['products'], $manifest['documents'] );
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

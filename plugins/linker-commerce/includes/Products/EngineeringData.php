<?php
/**
 * The engineering data files this plugin ships and the feed builds on.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * The compatibility contract and the retained one-time reference migration
 * input. Runtime reference facts and document permissions are maintained in Woo.
 */
final class EngineeringData {

	/**
	 * The compatibility contract: pair patterns, verdicts, conditions, documents.
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
	 * The compatibility contract's version: the `version` the file itself
	 * states, or "missing" when the file is unreadable. The feed reports this
	 * value as its compatibility_version (docs/specs/8-engineering-data.md
	 * target shape 5, feed.schema.json).
	 */
	public static function compatibility_version(): string {
		$data = self::json( self::COMPATIBILITY_FILE );

		return is_string( $data['version'] ?? null ) && '' !== $data['version'] ? $data['version'] : 'missing';
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

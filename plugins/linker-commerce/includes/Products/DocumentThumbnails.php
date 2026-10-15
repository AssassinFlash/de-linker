<?php
/**
 * The document rows' first-page thumbnails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * The first-page thumbnails of the documents the register lists: WebP images
 * built once by tools/faq/thumbs.py and shipped with the plugin in
 * assets/faq-thumbs/, next to a manifest that maps a document to its file.
 *
 * Build time, not request time: the register's files are the live uploads, and
 * rasterising them on request would fetch and parse 350 MB of manuals for a
 * page that shows 52x72 pixel previews (docs/specs/176-faq-download.md §3). A
 * document the build could not render — one over the pipeline's per-file cap
 * or whose download failed — has no entry, and its row falls back to the type
 * tile the design shows for a document without a thumbnail.
 *
 * The manifest's key is the document URL's path, not the URL: the same file is
 * served by the live host and by a local instance, and a thumbnail belongs to
 * the file. That is also why one build serves both language pages.
 */
final class DocumentThumbnails {

	/**
	 * Directory of the shipped images and their manifest, relative to the
	 * plugin.
	 */
	public const DIRECTORY = 'assets/faq-thumbs';

	/**
	 * The manifest file tools/faq/thumbs.py writes next to the images.
	 */
	public const MANIFEST = 'manifest.json';

	/**
	 * The decoded manifest, read once per request.
	 *
	 * @var array<string, array{file: string, width: int, height: int}>|null
	 */
	private static ?array $files = null;

	/**
	 * The thumbnail of a document URL, or null when the build shipped none.
	 *
	 * @param string $url Document URL as the register states it.
	 * @return array{src: string, width: int, height: int}|null
	 */
	public static function of( string $url ): ?array {
		$manifest = self::manifest();
		$key      = self::key( $url );
		if ( ! isset( $manifest[ $key ] ) ) {
			return null;
		}

		return array(
			'src'    => plugins_url( self::DIRECTORY . '/' . $manifest[ $key ]['file'], dirname( __DIR__, 2 ) . '/linker-commerce.php' ),
			'width'  => $manifest[ $key ]['width'],
			'height' => $manifest[ $key ]['height'],
		);
	}

	/**
	 * A document URL's manifest key: its path, so the live host and a local
	 * instance resolve the same file to the same thumbnail.
	 *
	 * @param string $url Document URL.
	 */
	public static function key( string $url ): string {
		$path = (string) wp_parse_url( $url, PHP_URL_PATH );

		return '' === $path ? $url : $path;
	}

	/**
	 * The manifest's entries: URL path → {file, width, height}. A name that is
	 * not the pipeline's own `<sha1>.webp` is dropped here — the manifest is a
	 * build artifact on disk, and only that shape reaches a URL.
	 *
	 * @return array<string, array{file: string, width: int, height: int}>
	 */
	public static function manifest(): array {
		if ( null !== self::$files ) {
			return self::$files;
		}
		self::$files = array();
		$path        = dirname( __DIR__, 2 ) . '/' . self::DIRECTORY . '/' . self::MANIFEST;
		if ( ! is_readable( $path ) ) {
			return self::$files;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local plugin asset on disk, not a remote URL.
		$payload = json_decode( (string) file_get_contents( $path ), true );
		foreach ( is_array( $payload ) ? $payload : array() as $key => $entry ) {
			if ( ! is_string( $key ) || ! is_array( $entry ) ) {
				continue;
			}
			$file = $entry['file'] ?? null;
			if ( ! is_string( $file ) || 1 !== preg_match( '/^[a-f0-9]{40}\.webp$/', $file ) ) {
				continue;
			}
			self::$files[ $key ] = array(
				'file'   => $file,
				'width'  => (int) ( $entry['width'] ?? 0 ),
				'height' => (int) ( $entry['height'] ?? 0 ),
			);
		}

		return self::$files;
	}
}

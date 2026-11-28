<?php
/**
 * Byte ranges for the site's public PDF downloads.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/** Send the selected interval without loading the entire document into memory. */
final class DocumentStream {
	/**
	 * Resolve an inclusive range, including open-ended and suffix ranges.
	 *
	 * @param int    $size File size in bytes.
	 * @param string $range HTTP Range or the empty string for the entire file.
	 * @return array{int,int}|null
	 */
	public static function range( int $size, string $range ): ?array {
		if ( '' === $range ) {
			return array( 0, $size - 1 );
		}
		if ( ! preg_match( '/^bytes=(\d*)-(\d*)$/D', $range, $matches ) || ( '' === $matches[1] && '' === $matches[2] ) ) {
			return null;
		}
		$start = '' === $matches[1] ? max( 0, $size - (int) $matches[2] ) : (int) $matches[1];
		$end   = '' === $matches[1] || '' === $matches[2] ? $size - 1 : min( $size - 1, (int) $matches[2] );
		return $start <= $end ? array( $start, $end ) : null;
	}

	/**
	 * Stream authorized bytes from a local file.
	 *
	 * @param string $path Absolute path.
	 * @param int    $start First byte.
	 * @param int    $length Byte count.
	 */
	public static function send( string $path, int $start, int $length ): void {
		// phpcs:disable WordPress.WP.AlternativeFunctions -- The registered document is a local file supporting seekable byte ranges.
		$stream = fopen( $path, 'rb' );
		if ( false === $stream ) {
			return;
		}
		try {
			fseek( $stream, $start );
			while ( $length > 0 && ! feof( $stream ) ) {
				$chunk = fread( $stream, min( 65536, $length ) );
				if ( false === $chunk || '' === $chunk ) {
					break;
				}
				echo $chunk; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Original document bytes.
				$length -= strlen( $chunk );
			}
		} finally {
			fclose( $stream );
		}
		// phpcs:enable
	}
}

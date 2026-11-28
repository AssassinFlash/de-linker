<?php
/**
 * Serve the approved engineering toolkit from its stable public URLs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\Publication\DocumentCache;

/** Dispatch a registered toolkit file before the WordPress main query. */
final class ToolkitEndpoint {
	/** Register the canonical toolkit route. */
	public function register(): void {
		add_filter( 'do_parse_request', array( $this, 'serve' ), 1 );
	}

	/**
	 * Stream GET requests and return identical representation headers for HEAD.
	 *
	 * @param bool $parse Whether WordPress should parse the request.
	 */
	public function serve( bool $parse ): bool {
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- Only an exact route and registered filename can name a local file.
		$path   = (string) wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH );
		$prefix = (string) wp_parse_url( PageUrls::root() . ToolkitRegistry::ROUTE_PREFIX, PHP_URL_PATH );
		if ( ! $parse || ! str_starts_with( $path, $prefix ) ) {
			return $parse;
		}
		$item   = ToolkitRegistry::find_by_filename( substr( $path, strlen( $prefix ) ) );
		$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
		$range  = wp_unslash( $_SERVER['HTTP_RANGE'] ?? '' );
		// phpcs:enable
		if ( null === $item || ! is_readable( $item['path'] ) ) {
			$this->error( 404 );
		}
		if ( ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) {
			header( 'Allow: GET, HEAD' );
			$this->error( 405 );
		}

		$pdf  = 'pdf' === $item['format'];
		$span = DocumentStream::range( $item['bytes'], $pdf ? $range : '' );
		if ( $pdf ) {
			header( 'Accept-Ranges: bytes' );
		}
		if ( null === $span ) {
			header( 'Content-Range: bytes */' . $item['bytes'] );
			$this->error( 416 );
		}
		list( $start, $end ) = $span;
		$length              = $end - $start + 1;
		if ( $pdf && '' !== $range ) {
			status_header( 206 );
			header( 'Content-Range: bytes ' . $start . '-' . $end . '/' . $item['bytes'] );
			DocumentCache::forbid( false );
			header( 'Cache-Control: private, no-store, max-age=0' );
		} else {
			status_header( 200 );
			DocumentCache::allow( array( 'LK.toolkit', 'LK.toolkit.' . $item['suite'] ), DAY_IN_SECONDS );
			header( 'Cache-Control: public, max-age=86400, stale-while-revalidate=3600' );
		}
		header( 'Content-Type: ' . $item['mime'] );
		header( 'Content-Language: ' . $item['content_language'] );
		header( 'Content-Disposition: ' . ( $pdf ? 'inline' : 'attachment' ) . '; filename="' . $item['filename'] . '"' );
		header( 'Content-Length: ' . $length );
		header( 'X-Robots-Tag: index, follow' );
		header( 'X-Content-Type-Options: nosniff' );
		header( 'Link: <' . $item['url'] . '>; rel="canonical"' );
		header( 'Last-Modified: ' . gmdate( 'D, d M Y H:i:s', (int) filemtime( $item['path'] ) ) . ' GMT' );
		header( 'ETag: "' . substr( $item['sha256'], 0, 16 ) . '"' );
		if ( 'GET' === $method ) {
			DocumentStream::send( $item['path'], $start, $length );
		}
		exit;
	}

	/**
	 * An unknown file, unsupported method or unsatisfiable range has no representation.
	 *
	 * @param int $status HTTP error status.
	 */
	private function error( int $status ): never {
		status_header( $status );
		DocumentCache::forbid( true );
		header( 'Cache-Control: no-store, private, max-age=0' );
		header( 'X-Robots-Tag: noindex, nofollow' );
		header( 'Content-Length: 0' );
		exit;
	}
}

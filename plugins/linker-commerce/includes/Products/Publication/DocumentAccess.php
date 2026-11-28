<?php
/**
 * Original technical PDF URLs pass a current Woo relation before bytes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\DocumentStream;

/** Authorizes original uploads before publishing bytes to the tagged edge cache. */
final class DocumentAccess {
	public const QUERY_VAR         = 'linker_public_document';
	public const VERSION_QUERY_VAR = 'linker_document_sha256';

	/**
	 * Native WordPress rewrite block precedes its existing-file shortcut.
	 *
	 * @param string $rules Native WordPress rewrite rules.
	 */
	public function rewrite_rules( string $rules ): string {
		$uploads = wp_upload_dir();
		$prefix  = ltrim( (string) wp_parse_url( $uploads['baseurl'], PHP_URL_PATH ), '/' );
		$home    = trim( (string) wp_parse_url( home_url(), PHP_URL_PATH ), '/' );
		if ( '' !== $home && str_starts_with( $prefix, $home . '/' ) ) {
			$prefix = substr( $prefix, strlen( $home ) + 1 );
		}
		$gate = 'RewriteRule ^' . preg_quote( $prefix, '#' ) . '/(.+\.pdf)$ index.php?' . self::QUERY_VAR . '=$1 [END,NC,QSA]';
		return str_replace( 'RewriteEngine On', "RewriteEngine On\n# Current Woo technical-document permission\n" . $gate, $rules );
	}

	/** Internal request path, also used by the local server's dynamic router. */
	public function serve(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- a public download; resolve() validates the unslashed path before use.
		$value = $_GET[ self::QUERY_VAR ] ?? null;
		if ( ! is_string( $value ) ) {
			return;
		}
		$uploads = wp_upload_dir();
		// Preserve original-URL identity even when QSA includes a second query
		// variable. Direct index.php source links still name their explicit path.
		$request_uri  = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- managed resolver validates the complete path.
		$request_path = wp_parse_url( $request_uri, PHP_URL_PATH );
		$base_path    = wp_parse_url( $uploads['baseurl'], PHP_URL_PATH );
		$original     = is_string( $request_path ) && is_string( $base_path ) && str_starts_with( $request_path, rtrim( $base_path, '/' ) . '/' ) && 'pdf' === strtolower( pathinfo( $request_path, PATHINFO_EXTENSION ) );
		if ( $original ) {
			$value = substr( $request_path, strlen( rtrim( $base_path, '/' ) ) + 1 );
		}
		$file   = DocumentFiles::resolve( rtrim( $uploads['baseurl'], '/' ) . '/' . ltrim( wp_unslash( $value ), '/' ) );
		$method = isset( $_SERVER['REQUEST_METHOD'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REQUEST_METHOD'] ) ) : 'GET';
		$range  = isset( $_SERVER['HTTP_RANGE'] ) ? sanitize_text_field( wp_unslash( $_SERVER['HTTP_RANGE'] ) ) : '';
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- public source identity; response() validates exact SHA-256 syntax and bytes.
		$expected = $_GET[ self::VERSION_QUERY_VAR ] ?? '';
		$expected = is_string( $expected ) ? wp_unslash( $expected ) : 'invalid';
		$response = $this->response( $file, $method, $range, $expected, $original && ! str_contains( $request_uri, '?' ) ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- response() validates method/range/version, no string is reflected.
		global $wp_query;
		$error_response = $response['status'] >= 400;
		if ( ! $error_response && $wp_query instanceof \WP_Query ) {
			$wp_query->is_404 = false;
		}
		status_header( $response['status'] );
		if ( $response['cacheable'] ) {
			DocumentCache::allow( $response['tags'], DAY_IN_SECONDS );
		} else {
			DocumentCache::forbid( $error_response );
		}
		header( 'X-Content-Type-Options: nosniff' );
		foreach ( $response['headers'] as $name => $content ) {
			header( $name . ': ' . $content );
		}
		if ( $response['length'] > 0 && 'HEAD' !== $method && null !== $file ) {
			DocumentStream::send( $file['path'], $response['start'], $response['length'] );
		}
		exit;
	}

	/**
	 * Authorize and describe a single byte-range response.
	 *
	 * @param array<string,string>|null $file Resolved local PDF.
	 * @param string                    $method Request method.
	 * @param string                    $range Optional HTTP Range header.
	 * @param string                    $expected Optional recorded file SHA-256.
	 * @param bool                      $clean Original uploads URL without a query string.
	 * @return array{status:int,headers:array<string,string>,start:int,length:int,cacheable:bool,tags:list<string>}
	 */
	public function response( ?array $file, string $method, string $range = '', string $expected = '', bool $clean = true ): array {
		$denied = array(
			'status'    => 410,
			'headers'   => array(
				'Content-Length' => '0',
				'Cache-Control'  => DocumentCache::PRIVATE_CONTROL,
				'X-Robots-Tag'   => 'noindex, nofollow',
			),
			'start'     => 0,
			'length'    => 0,
			'cacheable' => false,
			'tags'      => array(),
		);
		if ( ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) {
			$denied['status']           = 405;
			$denied['headers']['Allow'] = 'GET, HEAD';
			return $denied;
		}
		if ( null === $file ) {
			return $denied;
		}
		if ( '' !== $expected && ( 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $expected ) || ! hash_equals( $expected, $file['blob_sha256'] ) ) ) {
			return $denied;
		}
		try {
			$authorization = Publication::authorize_document( $file );
		} catch ( \RuntimeException $error ) {
			return array_replace( $denied, array( 'status' => 503 ) );
		}
		if ( null === $authorization ) {
			return $denied;
		}
		$size   = (int) filesize( $file['path'] );
		$bounds = DocumentStream::range( $size, $range );
		if ( null === $bounds ) {
			$denied['status']                   = 416;
			$denied['headers']['Accept-Ranges'] = 'bytes';
			$denied['headers']['Content-Range'] = 'bytes */' . $size;
			return $denied;
		}
		list( $start, $end ) = $bounds;
		$status              = '' === $range ? 200 : 206;
		$cacheable           = 'GET' === $method && 200 === $status && $clean && '' === $expected;
		$headers             = array(
			'Content-Type'     => 'application/pdf',
			'Accept-Ranges'    => 'bytes',
			'Content-Language' => self::language( $file['url'], $authorization['language'] ),
			'Last-Modified'    => gmdate( 'D, d M Y H:i:s', (int) filemtime( $file['path'] ) ) . ' GMT',
			'ETag'             => '"' . substr( $file['blob_sha256'], 0, 16 ) . '"',
			'Cache-Control'    => $clean && '' === $expected ? DocumentCache::PUBLIC_CONTROL : DocumentCache::PRIVATE_CONTROL,
		);
		if ( 206 === $status ) {
			$headers['Content-Range'] = 'bytes ' . $start . '-' . $end . '/' . $size;
		}
		$name                           = preg_replace( '/[^A-Za-z0-9._-]+/', '-', pathinfo( $file['path'], PATHINFO_FILENAME ) );
		$name                           = trim( (string) $name, '.-' );
		$headers['Content-Disposition'] = 'inline; filename="' . ( '' !== $name ? $name : 'document' ) . '.pdf"';
		$headers['X-Robots-Tag']        = 'index, follow';
		$headers['Link']                = '<' . $file['url'] . '>; rel="canonical"';
		$length                         = $end - $start + 1;
		$headers['Content-Length']      = (string) $length;
		return array(
			'status'    => $status,
			'headers'   => $headers,
			'start'     => $start,
			'length'    => $length,
			'cacheable' => $cacheable,
			'tags'      => $cacheable ? $authorization['cache_tags'] : array(),
		);
	}

	/**
	 * Language of the original OEM file, independent of the storefront language.
	 *
	 * @param string $url Public file URL.
	 * @param string $language Published document edition.
	 */
	private static function language( string $url, string $language ): string {
		$edition = Materials::document_edition( $url );
		$label   = strtoupper( (string) ( $edition['locale'] ?? $language ) );
		$name    = strtoupper( rawurldecode( basename( $url ) ) );
		if ( in_array( $label, array( 'MUL', 'MULTI', 'MULTILINGUAL', 'DE/EN', 'EN/DE' ), true ) || preg_match( '/(?:^|[^A-Z])(?:MUL|MULTI|DE[-_]EN|EN[-_]DE)(?:[^A-Z]|$)/', $name ) ) {
			return 'en, de-DE';
		}
		if ( '' !== $label ) {
			return in_array( $label, array( 'DE', 'DE-DE', 'GERMAN' ), true ) ? 'de-DE' : 'en';
		}
		return preg_match( '/(?:^|[^A-Z])DE(?:[^A-Z]|$)/', $name ) ? 'de-DE' : 'en';
	}
}

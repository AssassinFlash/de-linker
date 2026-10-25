<?php
/**
 * Managed technical-document paths. Content identity never grants access.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/** Resolve only real PDF files inside this site's uploads directory. */
final class DocumentFiles {
	/**
	 * Byte hashes live only within one authority assembly, never across reads.
	 *
	 * @var array<string,string>
	 */
	private static array $hashes = array();

	/**
	 * Whether the current authority assembly owns the bounded hash cache.
	 *
	 * @var bool
	 */
	private static bool $reading = false;

	/** Begin a fresh authority assembly. */
	public static function begin_read(): void {
		self::$hashes  = array();
		self::$reading = true;
	}

	/** Release request assembly data immediately. */
	public static function end_read(): void {
		self::$hashes  = array();
		self::$reading = false;
	}

	/**
	 * Resolve a managed local PDF, never an arbitrary local file.
	 *
	 * @param string $url Hosted URL.
	 * @return array{path:string,url:string,relative:string,blob_sha256:string}|null
	 */
	public static function resolve( string $url ): ?array {
		$file = self::locate( $url );
		if ( null === $file ) {
			return null;
		}
		$path = $file['path'];
		$sha  = self::$reading && isset( self::$hashes[ $path ] ) ? self::$hashes[ $path ] : hash_file( 'sha256', $path );
		if ( self::$reading && false !== $sha ) {
			self::$hashes[ $path ] = $sha;
		}
		return false === $sha ? null : $file + array( 'blob_sha256' => $sha );
	}

	/**
	 * Validate a current hosted path without claiming its content version.
	 *
	 * Listing metadata needs a readable managed PDF; cited facts and downloads
	 * still call resolve() to inspect the actual bytes.
	 *
	 * @param string $url Hosted URL.
	 * @return array{path:string,url:string,relative:string}|null
	 */
	public static function locate( string $url ): ?array {
		$uploads = wp_upload_dir();
		$parts   = wp_parse_url( $url );
		if ( ! is_array( $parts ) || isset( $parts['query'] ) || isset( $parts['user'] ) || isset( $parts['pass'] ) ) {
			return null;
		}
		$hosts = array_filter( array( wp_parse_url( home_url(), PHP_URL_HOST ), wp_parse_url( $uploads['baseurl'], PHP_URL_HOST ), 'de-linker.com', 'www.de-linker.com' ) );
		if ( isset( $parts['host'] ) && ! in_array( strtolower( $parts['host'] ), $hosts, true ) ) {
			return null;
		}
		$path = rawurldecode( $parts['path'] ?? '' );
		$base = rawurldecode( (string) wp_parse_url( $uploads['baseurl'], PHP_URL_PATH ) );
		if ( '' === $base || ! str_starts_with( $path, rtrim( $base, '/' ) . '/' ) || str_contains( $path, "\0" ) || str_contains( $path, '\\' ) ) {
			return null;
		}
		$relative = substr( $path, strlen( rtrim( $base, '/' ) ) + 1 );
		if ( in_array( '..', explode( '/', $relative ), true ) || in_array( '.', explode( '/', $relative ), true ) || 'pdf' !== strtolower( pathinfo( $relative, PATHINFO_EXTENSION ) ) ) {
			return null;
		}
		// Private inquiries, reports and uploads have their own owner gate.
		if ( preg_match( '#(?:^|/)(?:linker-private|linker-proformas|linker-reports|linker-genie|proforma|solution-reports|genie-uploads)(?:/|$)#i', $relative ) ) {
			return null;
		}
		$root = realpath( $uploads['basedir'] );
		$file = realpath( $uploads['basedir'] . '/' . $relative );
		if ( false === $root || false === $file || ! str_starts_with( $file, $root . DIRECTORY_SEPARATOR ) || ! is_file( $file ) || ! is_readable( $file ) ) {
			return null;
		}
		return array(
			'path'     => $file,
			'relative' => $relative,
			'url'      => rtrim( $uploads['baseurl'], '/' ) . '/' . implode( '/', array_map( 'rawurlencode', explode( '/', $relative ) ) ),
		);
	}

	/**
	 * A URL's stable identity, independent of content bytes.
	 *
	 * @param string $url Hosted URL.
	 */
	public static function id( string $url ): string {
		$path = wp_parse_url( $url, PHP_URL_PATH );
		return 'doc-' . hash( 'sha256', rawurldecode( is_string( $path ) ? $path : '' ) );
	}
}

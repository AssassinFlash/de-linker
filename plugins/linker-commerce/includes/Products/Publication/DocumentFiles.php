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
	/** Derived hashes for stable files in the most recent full manifest. */
	private const HASH_CACHE_OPTION = 'linker_publication_document_hashes_v1';

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

	/**
	 * Hashes of stable files already read in this request.
	 *
	 * One request can assemble the authority more than once; the documents are
	 * often unchanged. Keep the latest reusable identity per path.
	 *
	 * @var array<string,array{identity:string,sha:string}>
	 */
	private static array $verified = array();

	/**
	 * Stable hashes loaded for this manifest.
	 *
	 * @var array<array-key,mixed>
	 */
	private static array $cached = array();

	/**
	 * Stable hashes actually encountered in this manifest.
	 *
	 * @var array<string,array{identity:string,sha:string}>
	 */
	private static array $seen = array();

	/**
	 * Whether this authority assembly may reuse cross-request byte hashes.
	 *
	 * @var bool
	 */
	private static bool $cache_manifest = false;

	/**
	 * Begin a fresh authority assembly.
	 *
	 * @param bool $cache_manifest Reuse byte hashes only in a full manifest.
	 */
	public static function begin_read( bool $cache_manifest = false ): void {
		self::$hashes         = array();
		self::$reading        = true;
		self::$cache_manifest = $cache_manifest;
		self::$seen           = array();
		$cached               = $cache_manifest ? get_option( self::HASH_CACHE_OPTION, array() ) : array();
		self::$cached         = is_array( $cached ) ? $cached : array();
	}

	/** Release request assembly data immediately. */
	public static function end_read(): void {
		if ( self::$cache_manifest ) {
			// Retain only files in this manifest, including permitted aliases.
			ksort( self::$seen );
			ksort( self::$cached );
			if ( self::$seen !== self::$cached ) {
				update_option( self::HASH_CACHE_OPTION, self::$seen, false );
			}
		}
		self::$hashes         = array();
		self::$cached         = array();
		self::$seen           = array();
		self::$cache_manifest = false;
		self::$reading        = false;
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
		$sha = self::checksum( $file['path'] );
		return false === $sha ? null : $file + array( 'blob_sha256' => $sha );
	}

	/**
	 * Byte checksum for a path, read once per unchanged file in this request.
	 *
	 * @param string $path Resolved local path.
	 * @return string|false
	 */
	private static function checksum( string $path ): string|false {
		if ( self::$reading && isset( self::$hashes[ $path ] ) ) {
			return self::$hashes[ $path ];
		}
		// PHP stat timestamps have whole-second precision. Reuse across authority
		// reads only after that change interval has closed, using a fresh stat.
		clearstatcache( false, $path );
		$now  = time();
		$stat = stat( $path );
		if ( false === $stat ) {
			return false;
		}
		$identity  = implode( ':', array( $stat['dev'], $stat['ino'], $stat['size'], $stat['mtime'], $stat['ctime'] ) );
		$key       = $stat['ctime'] < $now && $stat['mtime'] < $now ? $identity : null;
		$cache_key = hash( 'sha256', $path );
		$known     = self::$verified[ $path ] ?? ( self::$cache_manifest ? self::$cached[ $cache_key ] ?? null : null );
		$stable    = false;
		if ( null !== $key && is_array( $known ) && ( $known['identity'] ?? null ) === $key && is_string( $known['sha'] ?? null ) && 1 === preg_match( '/^[a-f0-9]{64}$/D', $known['sha'] ) ) {
			$sha    = $known['sha'];
			$stable = true;
		} else {
			$sha = hash_file( 'sha256', $path );
			if ( false !== $sha ) {
				// A changed file has no usable digest for this read or a later one.
				clearstatcache( false, $path );
				$after = stat( $path );
				if ( false === $after || implode( ':', array( $after['dev'], $after['ino'], $after['size'], $after['mtime'], $after['ctime'] ) ) !== $identity ) {
					return false;
				}
				if ( null !== $key ) {
					self::$verified[ $path ] = array(
						'identity' => $key,
						'sha'      => $sha,
					);
					$stable                  = true;
				}
			}
		}
		if ( self::$cache_manifest && $stable ) {
			self::$seen[ $cache_key ] = array(
				'identity' => $key,
				'sha'      => $sha,
			);
		}
		if ( self::$reading && false !== $sha ) {
			self::$hashes[ $path ] = $sha;
		}
		return $sha;
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

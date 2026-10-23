<?php
/**
 * Original technical PDF URLs pass a current Woo relation before bytes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;

/** No redirect back to a static URL, and no public cache of an allowed result. */
final class DocumentAccess {
	public const QUERY_VAR = 'linker_public_document';

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
		$gate     = 'RewriteRule ^' . preg_quote( $prefix, '#' ) . '/(.+\\.pdf)$ index.php?' . self::QUERY_VAR . '=$1 [END,NC]';
		$no_cache = 'RewriteRule ^' . preg_quote( $prefix, '#' ) . '/(.+\\.pdf)$ - [E=Cache-Control:no-cache,NC]';
		return str_replace( 'RewriteEngine On', "RewriteEngine On\n# Current Woo technical-document permission\n" . $no_cache . "\n" . $gate, $rules );
	}

	/** Internal request path, also used by the local server's dynamic router. */
	public function serve(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- a public download; resolve() validates the unslashed path before use.
		$value = $_GET[ self::QUERY_VAR ] ?? null;
		if ( ! is_string( $value ) ) {
			return;
		}
		$uploads  = wp_upload_dir();
		$file     = DocumentFiles::resolve( rtrim( $uploads['baseurl'], '/' ) . '/' . ltrim( wp_unslash( $value ), '/' ) );
		$method   = isset( $_SERVER['REQUEST_METHOD'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REQUEST_METHOD'] ) ) : 'GET';
		$range    = isset( $_SERVER['HTTP_RANGE'] ) ? sanitize_text_field( wp_unslash( $_SERVER['HTTP_RANGE'] ) ) : '';
		$response = $this->response( $file, $method, $range ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- response() validates method and range, no string is reflected.
		if ( ! defined( 'DONOTCACHEPAGE' ) ) {
			define( 'DONOTCACHEPAGE', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress cache convention.
		}
		status_header( $response['status'] );
		nocache_headers();
		header( 'Cache-Control: no-store, private, max-age=0' );
		header( 'X-Content-Type-Options: nosniff' );
		foreach ( $response['headers'] as $name => $content ) {
			header( $name . ': ' . $content );
		}
		if ( $response['length'] > 0 && 'HEAD' !== $method && null !== $file ) {
			$stream = fopen( $file['path'], 'rb' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- authorized local PDF byte stream.
			if ( false !== $stream ) {
				fseek( $stream, $response['start'] ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fseek -- a validated range.
				$remaining = $response['length'];
				while ( $remaining > 0 && ! feof( $stream ) ) {
					// 64 KiB is a streaming buffer, not a product/business threshold.
					$chunk = fread( $stream, min( 65536, $remaining ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fread -- authorized stream.
					if ( false === $chunk ) {
						break;
					}
					echo $chunk; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- exact PDF bytes.
					$remaining -= strlen( $chunk );
				}
				fclose( $stream ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- authorized stream.
			}
		}
		exit;
	}

	/**
	 * Authorize and describe a single byte-range response.
	 *
	 * @param array<string,string>|null $file Resolved local PDF.
	 * @param string                    $method Request method.
	 * @param string                    $range Optional HTTP Range header.
	 * @return array{status:int,headers:array<string,string>,start:int,length:int}
	 */
	public function response( ?array $file, string $method, string $range = '' ): array {
		$denied = array(
			'status'  => 410,
			'headers' => array( 'Content-Length' => '0' ),
			'start'   => 0,
			'length'  => 0,
		);
		if ( ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) {
			return array_replace(
				$denied,
				array(
					'status'  => 405,
					'headers' => array(
						'Allow'          => 'GET, HEAD',
						'Content-Length' => '0',
					),
				)
			);
		}
		if ( null === $file ) {
			return $denied;
		}
		$allowed = false;
		foreach ( Publication::manifest()['documents'] as $document ) {
			if ( $document['blob_sha256'] === $file['blob_sha256'] && in_array( $file['url'], $document['aliases'], true ) ) {
				$allowed = true;
				break;
			}
		}
		if ( ! $allowed ) {
			return $denied;
		}
		$size    = (int) filesize( $file['path'] );
		$start   = 0;
		$end     = $size - 1;
		$status  = 200;
		$headers = array(
			'Content-Type'  => 'application/pdf',
			'Accept-Ranges' => 'bytes',
		);
		if ( '' !== $range ) {
			if ( ! preg_match( '/^bytes=(\d*)-(\d*)$/D', $range, $matches ) || ( '' === $matches[1] && '' === $matches[2] ) ) {
				return array_replace(
					$denied,
					array(
						'status'  => 416,
						'headers' => array(
							'Content-Range'  => 'bytes */' . $size,
							'Content-Length' => '0',
						),
					)
				);
			}
			if ( '' === $matches[1] ) {
				$start = max( 0, $size - (int) $matches[2] );
			} else {
				$start = (int) $matches[1];
				$end   = '' === $matches[2] ? $end : min( $end, (int) $matches[2] );
			}
			if ( $start > $end || $start >= $size ) {
				return array_replace(
					$denied,
					array(
						'status'  => 416,
						'headers' => array(
							'Content-Range'  => 'bytes */' . $size,
							'Content-Length' => '0',
						),
					)
				);
			}
			$status                   = 206;
			$headers['Content-Range'] = 'bytes ' . $start . '-' . $end . '/' . $size;
		}
		$length                    = $end - $start + 1;
		$headers['Content-Length'] = (string) $length;
		return array(
			'status'  => $status,
			'headers' => $headers,
			'start'   => $start,
			'length'  => $length,
		);
	}
}

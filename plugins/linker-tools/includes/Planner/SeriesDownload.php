<?php
/** Bounded, owned PV interval export through the native HTTP transport.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** A temporary file owned by this request, never exposed as a path. */
final class SeriesDownload {
	public const MAX_BYTES = 128 * 1024 * 1024;

	/**
	 * Own one request-local temporary file.
	 *
	 * @param string $file Request-owned temporary path.
	 * @param int    $size Verified file length.
	 */
	private function __construct( private string $file, public int $size ) {}

	/** Remove any file still held by this request. */
	public function __destruct() {
		$this->remove();
	}

	/**
	 * Fetch a verified series under the native project owner.
	 *
	 * @param Principal           $principal Verified owner.
	 * @param array<string,mixed> $command Native owned asset request.
	 * @param Transport           $transport Native private transport.
	 * @return self|WP_Error Validated temporary file or refusal.
	 */
	public static function fetch( Principal $principal, array $command, Transport $transport ): self|WP_Error {
		$keys = array_keys( $command );
		sort( $keys );
		if ( array( 'asset_id', 'project_id', 'schema_version', 'series_csv' ) !== $keys || 1 !== $command['schema_version'] || true !== $command['series_csv'] || ! is_string( $command['asset_id'] ) || ! is_string( $command['project_id'] ) ) {
			return Failure::make( 'input', 400 );
		}
		unset( $command['series_csv'] );
		$asset = $transport->object( $principal, 'assets/read', $command );
		if ( is_wp_error( $asset ) ) {
			return $asset;
		}
		$sha = $asset['content_sha256'] ?? null;
		if ( ( $asset['id'] ?? null ) !== $command['asset_id'] || ( $asset['project_id'] ?? null ) !== $command['project_id'] || 'planning_pv_series_csv_v1' !== ( $asset['purpose'] ?? null ) || 'text/csv' !== ( $asset['media_type'] ?? null ) || ! is_string( $sha ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $sha ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		$file = wp_tempnam( 'linker-pv-series' );
		if ( '' === $file || ! is_file( $file ) ) {
			return Failure::make( 'unavailable', 503 );
		}
		$download = new self( $file, 0 );
		register_shutdown_function( array( $download, 'remove' ) );
		$reply = $transport->stream_series( $principal, $command, $file );
		if ( is_wp_error( $reply ) ) {
			$download->remove();
			return $reply;
		}
		clearstatcache( true, $file );
		$size = filesize( $file );
		$hash = hash_file( 'sha256', $file );
		if ( ! is_int( $size ) || $size < 1 || $size > self::MAX_BYTES || ! is_string( $hash ) || ! hash_equals( $sha, $hash ) ) {
			$download->remove();
			return Failure::make( 'invalid_reply', 502 );
		}
		$download->size = $size;
		return $download;
	}

	/** Output exactly the validated file, then promptly remove it. */
	public function output(): void {
		$handle = fopen( $this->file, 'rb' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Request-owned bounded HTTP temporary file.
		if ( false !== $handle ) {
			while ( ! feof( $handle ) && ! connection_aborted() ) {
				$chunk = fread( $handle, 65536 ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fread -- Stream the validated temporary file.
				if ( false === $chunk ) {
					break;
				}
				echo $chunk; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Exact verified CSV attachment bytes.
			}
			fclose( $handle ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Close request-owned stream.
		}
		$this->remove();
	}

	/** Remove only this request's temporary file. */
	public function remove(): void {
		if ( '' !== $this->file ) {
			@unlink( $this->file ); // phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged, WordPress.WP.AlternativeFunctions.unlink_unlink -- Request-owned temporary file may already have been removed.
			$this->file = '';
		}
	}
}

<?php
/**
 * Customer documents kept out of the web server's reach.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use RuntimeException;

/**
 * Keeps documents that belong to one customer (Proforma invoices, design
 * reports) in a directory under uploads that the web server does not serve:
 * it carries a deny-all .htaccess (the site runs on LiteSpeed, which reads it)
 * and the file names have a random part. Customers reach a file only through
 * DocumentDownload, which checks who asks.
 */
final class PrivateFiles {

	/**
	 * Sets up the storage.
	 *
	 * @param string $directory Directory under uploads, e.g. "proforma".
	 */
	public function __construct( private readonly string $directory ) {}

	/**
	 * Writes a file.
	 *
	 * @param int    $owner_id Object the file belongs to (inquiry, solution); its directory.
	 * @param string $name     Readable part of the file name.
	 * @param string $bytes    Content.
	 * @return string Path relative to the directory.
	 * @throws RuntimeException When the file cannot be written.
	 */
	public function write( int $owner_id, string $name, string $bytes ): string {
		$this->protect();
		$relative = $owner_id . '/' . sanitize_file_name( $name ) . '-' . bin2hex( random_bytes( 8 ) ) . '.pdf';
		$path     = $this->root() . '/' . $relative;
		if ( ! wp_mkdir_p( dirname( $path ) ) ) {
			throw new RuntimeException( 'Cannot create ' . dirname( $path ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- a log message, not output.
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- uploads is written directly, as WordPress does for media.
		if ( false === file_put_contents( $path, $bytes ) ) {
			throw new RuntimeException( 'Cannot write ' . $path ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- a log message, not output.
		}
		return $relative;
	}

	/**
	 * Absolute path of a stored file, or '' when there is none.
	 *
	 * @param string $relative Path relative to the directory.
	 */
	public function path( string $relative ): string {
		if ( '' === $relative || str_contains( $relative, '..' ) ) {
			return '';
		}
		$path = $this->root() . '/' . $relative;
		return is_file( $path ) ? $path : '';
	}

	/**
	 * Deletes a stored file.
	 *
	 * @param string $relative Path relative to the directory.
	 */
	public function delete( string $relative ): void {
		$path = $this->path( $relative );
		if ( '' !== $path ) {
			wp_delete_file( $path );
		}
	}

	/**
	 * Reclaims the per-object directory after its post has been permanently deleted.
	 *
	 * @param int $owner_id Deleted object's ID, the directory used by write().
	 */
	public function delete_owner( int $owner_id ): void {
		$directory = $this->root() . '/' . $owner_id;
		if ( $owner_id <= 0 || ! is_dir( $directory ) || is_link( $directory ) ) {
			return;
		}
		$files = glob( $directory . '/*.pdf' );
		if ( false === $files ) {
			return;
		}
		foreach ( $files as $file ) {
			wp_delete_file_from_directory( $file, $directory );
		}
		$entries = scandir( $directory );
		if ( is_array( $entries ) && array() === array_values( array_diff( $entries, array( '.', '..' ) ) ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_rmdir -- matches the per-object uploads directory created by write().
			rmdir( $directory );
		}
	}

	/**
	 * The directory.
	 */
	private function root(): string {
		return wp_upload_dir( null, false )['basedir'] . '/' . $this->directory;
	}

	/**
	 * Creates the directory with its deny-all .htaccess and an empty index.html.
	 *
	 * @throws RuntimeException When the directory cannot be created.
	 */
	private function protect(): void {
		$root = $this->root();
		if ( ! wp_mkdir_p( $root ) ) {
			throw new RuntimeException( 'Cannot create ' . $root ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- a log message, not output.
		}
		$files = array(
			'.htaccess'  => "Require all denied\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n",
			'index.html' => '',
		);
		foreach ( $files as $name => $content ) {
			if ( ! is_file( $root . '/' . $name ) ) {
				// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- uploads is written directly, as WordPress does for media.
				file_put_contents( $root . '/' . $name, $content );
			}
		}
	}
}

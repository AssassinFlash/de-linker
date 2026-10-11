<?php
/**
 * Plugin Name: Linker error recorder
 * Description: Writes PHP errors to wp-content/linker-errors/php.log (rotating at 256 KB), because the host runs with log_errors off and has no error log this project can read.
 *
 * A must-use plugin: it loads before the regular plugins, so the errors worth
 * having — the ones that break the site — are recorded even when a plugin is
 * the thing that breaks. It uses nothing from WordPress (no database, no
 * options, no HTTP, no autoloader): a recorder that needs a working site to
 * report a broken one is not a recorder.
 *
 * What it changes on the host, and why each part is enough:
 *
 * - `log_errors=1` and `error_log=<its own file>`: both are PHP_INI_ALL, so a
 *   runtime change is enough, and PHP then writes fatals, warnings and notices
 *   into the file itself. On the host `log_errors` is off (measured), which is
 *   why errors currently go nowhere this project can read.
 * - `display_errors=0`: an error is never a visitor's to see.
 * - Rotation at max_bytes, keeping one previous file: an append-only file on a
 *   shared host is a future outage of its own, and a fatal in a loop must not
 *   fill the disk.
 * - A deny-all .htaccess and an empty index.html beside the file: wp-content is
 *   web-served, and a stack trace is not public. The site's private upload
 *   directories carry the same two files (Linker\Commerce\Account\PrivateFiles);
 *   this plugin cannot reuse that class because it must run when the plugins
 *   do not.
 *
 * Deployed by the cutover (docs/specs/17-cutover.md).
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu;

defined( 'ABSPATH' ) || exit;

/*
 * This file uses plain PHP file functions, the @ operator and ini_set() where
 * the WordPress rules would ask for WP_Filesystem, WP_DEBUG_LOG and checked
 * calls. It must run when WordPress's own code is the thing that broke:
 * WP_Filesystem needs a working WordPress, wp_delete_file() needs it too, and
 * WP_DEBUG_LOG writes one file that never rotates, which is the failure this
 * plugin exists to avoid. Every silenced call is followed by a check of its
 * result or is a best effort whose failure leaves the site as it was.
 */
// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.NoSilencedErrors.Discouraged, WordPress.PHP.IniSet

/**
 * Keeps a rotated record of the site's PHP errors.
 */
final class ErrorRecorder {

	/**
	 * Directory under wp-content the log lives in.
	 */
	public const DIRECTORY = 'linker-errors';

	/**
	 * The log file.
	 */
	public const FILE = 'php.log';

	/**
	 * The file the log is rotated into.
	 */
	public const PREVIOUS = 'php.1.log';

	/**
	 * Rotate when the log reaches this size: 256 KB holds an outage's worth of
	 * fatal lines with their stack traces, and is small enough that a fatal in
	 * a loop cannot fill a shared host.
	 */
	public const MAX_BYTES = 262144;

	/**
	 * Points PHP's error logging at the rotating file, and rotates it when the
	 * last request left it full.
	 *
	 * @param string $content_dir Absolute path of wp-content.
	 * @param int    $max_bytes   Rotate at this size.
	 */
	public static function start( string $content_dir, int $max_bytes = self::MAX_BYTES ): void {
		$directory = rtrim( $content_dir, '/' ) . '/' . self::DIRECTORY;
		if ( ! is_dir( $directory ) && ! @mkdir( $directory, 0755, true ) && ! is_dir( $directory ) ) {
			// Nowhere to write: leave PHP exactly as it was.
			return;
		}
		self::protect( $directory );
		self::rotate( $directory, $max_bytes );

		@ini_set( 'log_errors', '1' );
		@ini_set( 'display_errors', '0' );
		@ini_set( 'error_log', $directory . '/' . self::FILE );
	}

	/**
	 * The log's path, whether or not it exists yet.
	 *
	 * @param string $content_dir Absolute path of wp-content.
	 */
	public static function path( string $content_dir ): string {
		return rtrim( $content_dir, '/' ) . '/' . self::DIRECTORY . '/' . self::FILE;
	}

	/**
	 * Moves a full log aside, keeping one previous file.
	 *
	 * @param string $directory Directory of the log.
	 * @param int    $max_bytes Rotate at this size.
	 */
	private static function rotate( string $directory, int $max_bytes ): void {
		$log = $directory . '/' . self::FILE;
		// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged -- a stat cannot break a request; a missing file is the normal case.
		$size = @filesize( $log );
		if ( false === $size || $size < $max_bytes ) {
			return;
		}
		$previous = $directory . '/' . self::PREVIOUS;
		// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged -- rotation is best effort: a log that cannot be rotated is still a log.
		@unlink( $previous );
		// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged -- see above.
		@rename( $log, $previous );
	}

	/**
	 * Refuses web requests for the directory: a deny file for the web server,
	 * an empty index for a directory listing that ignores it.
	 *
	 * @param string $directory Directory of the log.
	 */
	private static function protect( string $directory ): void {
		$files = array(
			'.htaccess'  => "Require all denied\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n",
			'index.html' => '',
		);
		foreach ( $files as $name => $content ) {
			if ( ! is_file( $directory . '/' . $name ) ) {
				// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a stamp beside a log file, written the way the private upload directories write theirs.
				@file_put_contents( $directory . '/' . $name, $content );
			}
		}
	}
}

if ( defined( 'WP_CONTENT_DIR' ) ) {
	ErrorRecorder::start( (string) WP_CONTENT_DIR );
}

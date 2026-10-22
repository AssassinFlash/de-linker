<?php
/**
 * Connection-owned mutex for inquiry notification generation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

/** A database mutex is automatically released when a worker dies. */
final class Lock {
	/**
	 * Run without waiting; a durable scheduled task retries a busy lock.
	 *
	 * @param string           $key Logical operation.
	 * @param callable(): void $work Work under the connection-owned lock.
	 * @param int              $wait_seconds Optional bounded wait for a short native capacity edit.
	 */
	public static function run( string $key, callable $work, int $wait_seconds = 0 ): bool {
		global $wpdb;
		// Follow Genie's proven database/prefix namespace for server-wide locks.
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		$name     = 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/' . $key );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- A MySQL connection mutex has no WordPress API; zero wait protects the caller.
		// #568 allows at most one second for short DB-only business/mail edits.
		// Every existing review/model consumer retains the default zero wait.
		$taken = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $name, max( 0, min( 1, $wait_seconds ) ) ) );
		if ( '1' !== (string) $taken ) {
			return false;
		}
		try {
			$work();
		} finally {
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
		}
		// phpcs:enable
		return true;
	}
}

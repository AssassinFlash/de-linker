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
	 * @param bool             $guard_connection Guard only native mutex SQL, never the callback's model/SMTP work.
	 * @throws \RuntimeException Native mutex identity or release cannot be confirmed.
	 * @throws \Throwable The callback's original failure remains explicit.
	 */
	public static function run( string $key, callable $work, int $wait_seconds = 0, bool $guard_connection = false ): bool {
		global $wpdb;
		// Follow Genie's proven database/prefix namespace for server-wide locks.
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		$name     = 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/' . $key );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- A MySQL connection mutex has no WordPress API; zero wait protects the caller.
		// #568 allows at most one second for short DB-only business/mail edits.
		// Every existing review/model consumer retains the default zero wait.
		$owner   = $wpdb;
		$handle  = null;
		$thread  = 0;
		$acquire = static function () use ( $owner, $name, $wait_seconds, $guard_connection, &$handle, &$thread ) {
			if ( $guard_connection ) {
				$handle = $owner->__get( 'dbh' );
				if ( ! $handle instanceof \mysqli ) {
					throw new \RuntimeException( 'native_mutex_connection_unavailable' ); }
				$thread = $handle->thread_id;
			}
			return $owner->get_var( $owner->prepare( 'SELECT GET_LOCK(%s, %d)', $name, max( 0, min( 1, $wait_seconds ) ) ) );
		};
		$taken   = $guard_connection ? \Linker\Commerce\Mail\ConnectionFence::run( $acquire ) : $acquire();
		if ( '1' !== (string) $taken ) {
			return false;
		}
		$failure = null;
		try {
			$work();
		} catch ( \Throwable $error ) {
			$failure = $error;
			throw $error;
		} finally {
			try {
				$release = static fn () => $owner->get_var( $owner->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
				if ( $guard_connection ) {
					if ( $wpdb !== $owner || $owner->__get( 'dbh' ) !== $handle || ! $handle instanceof \mysqli || $handle->thread_id !== $thread ) {
						throw new \RuntimeException( 'native_mutex_connection_changed' );
					}
					if ( '1' !== (string) \Linker\Commerce\Mail\ConnectionFence::run( $release ) ) {
						throw new \RuntimeException( 'native_mutex_release_unconfirmed' );
					}
				} else {
					$release();
				}
			} catch ( \Throwable $cleanup_error ) {
				if ( null === $failure ) {
					throw $cleanup_error; }
			}
		}
		// phpcs:enable
		return true;
	}
}

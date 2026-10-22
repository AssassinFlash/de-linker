<?php
/**
 * Short native mysqli scope that cannot replay a lost transaction on a new connection.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

// phpcs:disable WordPress.DB.RestrictedFunctions -- wpdb has no scoped strict-driver API and can replay lost SQL; use only its existing native handle, restoring policy in finally.

/** Scoped driver policy; no global configuration or caller commit is changed. */
final class ConnectionFence {
	/**
	 * WordPress can reconnect and replay SQL 2006 in autocommit. Fail before replay.
	 * Nested calls restore exactly their caller's policy, including on exceptions.
	 *
	 * @template T
	 * @param callable $work Short native transaction/write work only, no provider or SMTP.
	 * @phpstan-param callable():T $work
	 * @phpstan-return T
	 * @phpstan-impure
	 * @return mixed Native result.
	 * @throws \RuntimeException Unsupported or changed native connection.
	 */
	public static function run( callable $work ): mixed {
		global $wpdb;
		$owner   = $wpdb;
		$handle  = $owner->__get( 'dbh' );
		$retries = $owner->__get( 'reconnect_retries' );
		if ( ! $handle instanceof \mysqli || ! is_int( $retries ) ) {
			throw new \RuntimeException( 'native_connection_fence_unavailable' );
		}
		$driver = new \mysqli_driver();
		$report = $driver->report_mode;
		$id     = $handle->thread_id;
		$guard  = static function ( string $sql ) use ( $owner, $handle, $id ): string {
			self::verify( $owner, $handle, $id );
			// Another wpdb constructor can reset mysqli's request-wide policy.
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT );
			return $sql;
		};
		$owner->__set( 'reconnect_retries', 0 );
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT );
		add_filter( 'query', $guard, PHP_INT_MIN );
		try {
			$result = $work();
			self::verify( $owner, $handle, $id );
			// A thread id cached by mysqli is not a liveness acknowledgement.
			$read = $handle->query( 'SELECT CONNECTION_ID()' );
			if ( ! $read instanceof \mysqli_result ) {
				throw new \RuntimeException( 'native_connection_fence_unconfirmed' );
			}
			$row = $read->fetch_row();
			$read->free();
			if ( ! is_array( $row ) || (string) $id !== (string) $row[0] ) {
				throw new \RuntimeException( 'native_connection_fence_changed' );
			}
			return $result;
		} finally {
			remove_filter( 'query', $guard, PHP_INT_MIN );
			$owner->__set( 'reconnect_retries', $retries );
			mysqli_report( $report );
		}
	}

	/**
	 * Verify the original client/connection before native SQL and final acknowledgement.
	 *
	 * @param \wpdb   $owner The exact native owner.
	 * @param \mysqli $handle The original driver handle.
	 * @param int     $id Original thread, never emitted or used as a public credential.
	 * @throws \RuntimeException A replacement connection cannot acknowledge the original work.
	 */
	private static function verify( \wpdb $owner, \mysqli $handle, int $id ): void {
		global $wpdb;
		if ( $wpdb !== $owner || $owner->__get( 'dbh' ) !== $handle || $handle->thread_id !== $id || 0 !== $owner->__get( 'reconnect_retries' ) ) {
			throw new \RuntimeException( 'native_connection_fence_changed' );
		}
	}
}

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
	/** Active native scopes, restored in LIFO order.
	 *
	 * @var list<self>
	 */
	private static array $stack = array();
	/** Whether the restoration fallback is registered.
	 *
	 * @var bool
	 */
	private static bool $shutdown = false;
	/** Whether this scope has restored its policy.
	 *
	 * @var bool
	 */
	private bool $closed = false;
	/** The original WordPress client.
	 *
	 * @var \wpdb
	 */
	private readonly \wpdb $owner;
	/** The original driver handle.
	 *
	 * @var \mysqli
	 */
	private readonly \mysqli $handle;
	/** The original server connection identity.
	 *
	 * @var int
	 */
	private readonly int $id;
	/** The previous reconnect policy.
	 *
	 * @var int
	 */
	private readonly int $retries;
	/** The previous driver error policy.
	 *
	 * @var int
	 */
	private readonly int $report;
	/** The scoped guard before each native query.
	 *
	 * @var \Closure
	 */
	private readonly \Closure $guard;

	/**
	 * Install policy only for this native scope.
	 *
	 * @throws \RuntimeException Unsupported native connection.
	 */
	private function __construct() {
		global $wpdb;
		$this->owner = $wpdb;
		$handle      = $wpdb->__get( 'dbh' );
		$retries     = $wpdb->__get( 'reconnect_retries' );
		if ( ! $handle instanceof \mysqli || ! is_int( $retries ) ) {
			throw new \RuntimeException( 'native_connection_fence_unavailable' );
		}
		$this->handle  = $handle;
		$this->retries = $retries;
		$this->report  = ( new \mysqli_driver() )->report_mode;
		$this->id      = $handle->thread_id;
		$this->guard   = function ( string $sql ): string {
			$this->verify();
			// Another wpdb constructor can reset mysqli's request-wide policy.
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT );
			return $sql;
		};
		$wpdb->__set( 'reconnect_retries', 0 );
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT );
		add_filter( 'query', $this->guard, PHP_INT_MIN );
	}

	/**
	 * Own a policy scope across native before/after hooks; close in the owner's finally.
	 * The fallback only restores driver policy at shutdown, never commits/rolls back.
	 *
	 * @throws \RuntimeException Unsupported native connection.
	 */
	public static function enter(): self {
		$scope         = new self();
		self::$stack[] = $scope;
		if ( ! self::$shutdown ) {
			self::$shutdown = true;
			register_shutdown_function(
				static function (): void {
					while ( array() !== self::$stack ) {
						self::$stack[ count( self::$stack ) - 1 ]->close();
					}
				}
			);
		}
		return $scope;
	}

	/**
	 * Restore policy in LIFO order even when an outer owner aborts its nested scopes.
	 * No database query, commit or compensating write occurs here after connection loss.
	 */
	public function close(): void {
		if ( $this->closed ) {
			return;
		}
		while ( array() !== self::$stack && end( self::$stack ) !== $this ) {
			self::$stack[ count( self::$stack ) - 1 ]->close();
		}
		array_pop( self::$stack );
		$this->closed = true;
		remove_filter( 'query', $this->guard, PHP_INT_MIN );
		$this->owner->__set( 'reconnect_retries', $this->retries );
		mysqli_report( $this->report );
	}

	/**
	 * WordPress can reconnect and replay SQL 2006 in autocommit. Fail before replay.
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
		$scope = self::enter();
		try {
			$result = $work();
			$scope->assert_current();
			return $result;
		} finally {
			$scope->close();
		}
	}

	/**
	 * Call before owner COMMIT and before acknowledging the returned result.
	 * This checks identity/liveness, not that a lost COMMIT was rolled back.
	 *
	 * @phpstan-impure
	 * @throws \RuntimeException A replaced or closed connection cannot acknowledge work.
	 */
	public function assert_current(): void {
		$this->verify();
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT );
		$read = $this->handle->query( 'SELECT CONNECTION_ID()' );
		if ( ! $read instanceof \mysqli_result ) {
			throw new \RuntimeException( 'native_connection_fence_unconfirmed' );
		}
		$row = $read->fetch_row();
		$read->free();
		if ( ! is_array( $row ) || (string) $this->id !== (string) $row[0] ) {
			throw new \RuntimeException( 'native_connection_fence_changed' );
		}
	}

	/**
	 * A replacement connection cannot acknowledge the original work.
	 *
	 * @throws \RuntimeException The original client/connection/policy has changed.
	 */
	private function verify(): void {
		global $wpdb;
		if ( $this->closed || $wpdb !== $this->owner || $this->owner->__get( 'dbh' ) !== $this->handle || $this->handle->thread_id !== $this->id || 0 !== $this->owner->__get( 'reconnect_retries' ) ) {
			throw new \RuntimeException( 'native_connection_fence_changed' );
		}
	}
}

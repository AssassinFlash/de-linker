<?php
/**
 * A short native writer that retains its original connection and transaction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

/** Joins a caller through a savepoint; never commits or rolls back that caller. */
final class NativeTransaction {
	/** Active managed native writers; external transactions are never adopted.
	 *
	 * @var list<self>
	 */
	private static array $stack = array();
	/** Immediate same-job consumers, only after confirmed owned commit.
	 *
	 * @var list<callable():void>
	 */
	private array $after = array();
	/** Original connection policy.
	 *
	 * @var ConnectionFence
	 */
	private readonly ConnectionFence $fence;
	/** Whether this writer owns the native transaction.
	 *
	 * @var bool
	 */
	private readonly bool $own;
	/** Server-owned original savepoint.
	 *
	 * @var string
	 */
	private readonly string $point;
	/** Whether commit/rollback has closed this scope.
	 *
	 * @var bool
	 */
	private bool $finished = false;

	/**
	 * Start immediately before the native writes, after provider work has ended.
	 *
	 * @throws \RuntimeException The original transaction cannot be established.
	 */
	public function __construct() {
		global $wpdb;
		$this->fence = ConnectionFence::enter();
		$started     = false;
		try {
			$this->own   = ! Capacity::transaction_active();
			$this->point = 'linker_native_' . bin2hex( random_bytes( 8 ) );
			if ( $this->own && ! BudgetTransaction::begin() ) {
				throw new \RuntimeException( 'native_transaction_start_failed' );
			}
			$started = $this->own;
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.InterpolatedNotPrepared -- Server-generated hexadecimal savepoint, never public input.
			if ( false === $wpdb->query( "SAVEPOINT {$this->point}" ) ) {
				throw new \RuntimeException( 'native_transaction_savepoint_failed' );
			}
			self::$stack[] = $this;
		} catch ( \Throwable $error ) {
			if ( $started ) {
				try {
					$this->fence->assert_current();
					$wpdb->query( 'ROLLBACK' ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Only this constructor's confirmed original owned transaction.
				} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- A failed original connection cannot compensate on a new client.
				}
			}
			$this->fence->close();
			throw $error;
		}
	}

	/**
	 * Confirm exactly this transaction before acknowledging native success.
	 *
	 * @throws \RuntimeException A changed connection or lost transaction is unknown.
	 */
	public function commit(): void {
		global $wpdb;
		$this->fence->assert_current();
		// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.InterpolatedNotPrepared -- Exact original server-generated savepoint proves no nested COMMIT/reconnect escaped.
		if ( $this->finished || false === $wpdb->query( "RELEASE SAVEPOINT {$this->point}" ) ) {
			throw new \RuntimeException( 'native_transaction_commit_unconfirmed' );
		}
		if ( $this->own && false === $wpdb->query( 'COMMIT' ) ) {
			throw new \RuntimeException( 'native_transaction_commit_unconfirmed' );
		}
		// phpcs:enable
		$this->fence->assert_current();
		if ( $this->own && Capacity::transaction_active() ) {
			throw new \RuntimeException( 'native_transaction_commit_unconfirmed' );
		}
		$this->finished = true;
		array_pop( self::$stack );
		$this->fence->close();
		foreach ( $this->after as $work ) {
			if ( ! $this->own ) {
				self::after_commit( $work );
				continue;
			}
			try {
				$work();
			} catch ( \Throwable $error ) {
				// The committed original job and AS remain the recovery source.
				CapacityHealth::failed();
			}
		}
	}

	/**
	 * Roll back only a live original connection; a lost commit remains unknown.
	 *
	 * @throws \RuntimeException Closed/changed connections cannot compensate on a new client.
	 */
	public function rollback(): void {
		global $wpdb;
		if ( $this->finished ) {
			return;
		}
		try {
			$this->fence->assert_current();
			// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.InterpolatedNotPrepared, WordPress.DB.PreparedSQL.NotPrepared -- Owned transaction or original generated savepoint only.
			$sql = $this->own ? 'ROLLBACK' : "ROLLBACK TO SAVEPOINT {$this->point}";
			if ( false === $wpdb->query( $sql ) ) {
				throw new \RuntimeException( 'native_transaction_rollback_unconfirmed' );
			}
			// phpcs:enable
		} finally {
			$this->finished = true;
			array_pop( self::$stack );
			$this->fence->close();
		}
	}

	/**
	 * Keep original immediate delivery after a managed writer commits.
	 * Unmanaged caller transactions retain their durable AS consumer instead.
	 *
	 * @param callable():void $work Original job-id consumer, no copied body.
	 */
	public static function after_commit( callable $work ): bool {
		$owner = end( self::$stack );
		if ( ! $owner instanceof self || $owner->finished ) {
			return false;
		}
		$owner->after[] = $work;
		return true;
	}

	/**
	 * Run DB-only writes; provider HTTP and SMTP belong outside this scope.
	 *
	 * @template T
	 * @param callable $work Short native writes.
	 * @phpstan-param callable():T $work
	 * @phpstan-return T
	 * @return mixed Native result.
	 * @throws \Throwable A failed or ambiguous native phase cannot return success.
	 */
	public static function run( callable $work ): mixed {
		$scope = new self();
		try {
			$result = $work();
			$scope->commit();
			return $result;
		} catch ( \Throwable $error ) {
			try {
				$scope->rollback();
			} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- Preserve original unknown failure without reconnect/compensation.
			}
			throw $error;
		}
	}
}

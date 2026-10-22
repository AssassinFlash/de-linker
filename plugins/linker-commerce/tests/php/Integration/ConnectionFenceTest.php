<?php
/**
 * Real server-side connection death must not turn atomic native writes into autocommit.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\ConnectionFence;

// phpcs:disable WordPress.DB.RestrictedFunctions -- Actual driver policy restoration and server-side connection death are the native behavior under test.

/**
 * Uses an independent local native connection to kill only this test process's DB thread.
 *
 * @coversNothing
 */
final class ConnectionFenceTest extends IntegrationTestCase {
	/**
	 * First write replay and failure after one uncommitted write both leave no partial data.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $partial Whether one first write precedes the server-side disconnect.
	 */
	public function test_real_connection_death_cannot_replay_write_in_autocommit( bool $partial ): void {
		global $wpdb;
		$observer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$name     = 'synthetic568_connection_' . self::tag();
		$retries  = self::retries();
		$report   = ( new \mysqli_driver() )->report_mode;
		$killed   = false;
		$caught   = false;
		$kill     = static function ( string $sql ) use ( $observer, $name, &$killed ): string {
			if ( ! $killed && str_contains( $sql, $name . '_second' ) && str_starts_with( $sql, 'INSERT' ) ) {
				$killed = true;
				global $wpdb;
				$observer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill );
		try {
			ConnectionFence::run(
				static function () use ( $name, $partial ): void {
					global $wpdb;
					$wpdb->query( 'START TRANSACTION' );
					if ( $partial ) {
						$wpdb->insert(
							$wpdb->options,
							array(
								'option_name'  => $name . '_first',
								'option_value' => 'uncommitted',
								'autoload'     => 'off',
							)
						); }
					$wpdb->insert(
						$wpdb->options,
						array(
							'option_name'  => $name . '_second',
							'option_value' => 'must-not-replay',
							'autoload'     => 'off',
						)
					);
					$wpdb->query( 'COMMIT' );
				}
			);
		} catch ( \mysqli_sql_exception $error ) {
			$caught = in_array( $error->getCode(), array( 2006, 2013 ), true );
		} finally {
			remove_filter( 'query', $kill ); }
		self::assertTrue( $killed );
		self::assertTrue( $caught );
		self::assertSame( 0, (int) $observer->get_var( $observer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name LIKE %s', $wpdb->options, $observer->esc_like( $name ) . '%' ) ) );
		self::assertSame( $retries, self::retries() );
		self::assertSame( $report, ( new \mysqli_driver() )->report_mode );
		// Restore only our dead local test connection, never pretend this rolls back
		// or acknowledges the lost production transaction.
		self::assertTrue( $wpdb->db_connect( false ) );
		$observer->close();
	}

	/** Scoped nested policy is exactly restored; it neither starts nor commits a transaction. */
	public function test_nested_scopes_restore_native_policy_and_leave_outer_transaction_owned(): void {
		global $wpdb;
		$retries = self::retries();
		$report  = ( new \mysqli_driver() )->report_mode;
		$wpdb->query( 'START TRANSACTION' );
		try {
			ConnectionFence::run(
				static function (): void {
					global $wpdb;
					self::assertSame( 0, self::retries() );
					ConnectionFence::run(
						static function (): void {
							global $wpdb;
							self::assertSame( 0, self::retries() );
						}
					);
					self::assertSame( 0, self::retries() );
				}
			);
			self::assertTrue( \Linker\Commerce\Mail\Capacity::transaction_active() );
		} finally {
			$wpdb->query( 'ROLLBACK' ); }
		self::assertSame( $retries, self::retries() );
		self::assertSame( $report, ( new \mysqli_driver() )->report_mode );
	}
	/** Native before/after hooks can hold the exact same scope across their writes. */
	public function test_explicit_scope_survives_separate_hooks_and_close_is_idempotent(): void {
		$before = self::retries();
		$scope  = ConnectionFence::enter();
		self::assertSame( 0, self::retries() );
		$scope->assert_current();
		ConnectionFence::run(
			static function (): void {
				self::assertSame( 0, self::retries() );
			}
		);
		$scope->assert_current();
		$scope->close();
		$scope->close();
		self::assertSame( $before, self::retries() );
	}

	/**
	 * Read native driver policy after a nested scope really exits.
	 *
	 * @phpstan-impure
	 * @throws \RuntimeException Native fixture configuration is unavailable.
	 */
	private static function retries(): int {
		global $wpdb;
		$value = $wpdb->__get( 'reconnect_retries' );
		if ( ! is_int( $value ) ) {
			throw new \RuntimeException( 'invalid_native_retries' ); }
		return $value;
	}
}

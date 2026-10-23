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

	/** Transactional authorization must fence its lock before joining a caller's writes. */
	public function test_authorization_lock_disconnect_cannot_reconnect_and_commit_over_the_lost_caller(): void {
		global $wpdb;
		$id     = 'synthetic-fenced-auth-' . self::tag();
		$marker = 'synthetic-fenced-caller-' . self::tag();
		$lock   = 'linker-send-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $id );
		$peer   = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$hits   = 0;
		$work   = false;
		$fail   = static function ( string $sql ) use ( $lock, $peer, &$hits ): string {
			if ( 0 === $hits && str_contains( $sql, 'GET_LOCK(' ) && str_contains( $sql, $lock ) ) {
				++$hits;
				global $wpdb;
				$peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		$wpdb->query( 'START TRANSACTION' );
		$wpdb->insert(
			$wpdb->options,
			array(
				'option_name'  => $marker,
				'option_value' => 'caller-owned',
				'autoload'     => 'off',
			)
		);
		add_filter( 'query', $fail, 999 );
		try {
			$result             = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
				$id,
				static function ( array &$state ) use ( &$work ): void {
					$work               = true;
					$state['published'] = true;
				},
				true
			);
			$caller_rows        = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, $marker ) );
			$authorization_rows = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $id ) );
		} finally {
			remove_filter( 'query', $fail, 999 );
			// Only the dead local fixture is reconnected, after its owned operation returned.
			self::assertTrue( $wpdb->db_connect( false ) );
			delete_option( $marker );
			delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $id );
			$peer->close();
		}
		self::assertSame( 1, $hits );
		self::assertFalse( $result );
		self::assertFalse( $work, 'No publication may run after the native caller connection is lost at GET_LOCK.' );
		self::assertSame( 0, $caller_rows );
		self::assertSame( 0, $authorization_rows );
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

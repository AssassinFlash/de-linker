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

	/**
	 * Native source writers must fence their first mutex before inspecting a caller's transaction.
	 *
	 * @testWith ["vat_persist"]
	 *           ["vat_erase"]
	 *           ["vat_deliver"]
	 *           ["proforma"]
	 * @param string $writer Actual native source writer.
	 */
	public function test_native_source_first_lock_cannot_reconnect_over_an_uncommitted_caller( string $writer ): void {
		global $wpdb;
		$intake = get_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		$this->later(
			static function () use ( $intake ): void {
				delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
				if ( false !== $intake ) {
					update_option( \Linker\Commerce\Protection\IntakeStore::OPTION, $intake, false );
				} }
		);
		WC()->mailer();
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_DAY, time() ), false );
		$customer = $this->customer();
		$id       = $customer->get_id();
		$notices  = new \Linker\Commerce\Registration\VatNotice();
		$source   = $notices->persist(
			$id,
			'DE123456789',
			array(
				'status' => \Linker\Commerce\Registration\VatProfile::INVALID,
				'detail' => '',
			),
			false,
			''
		);
		self::assertIsArray( $source );
		if ( 'vat_deliver' === $writer ) {
			$source = $notices->persist(
				$id,
				'DE123456789',
				array(
					'status' => \Linker\Commerce\Registration\VatProfile::VALID,
					'detail' => '',
				),
				true,
				$source['version']
			);
			self::assertIsArray( $source );
			self::assertSame( 0, $source['job'] );
			self::assertSame( 'yes', get_user_meta( $id, $notices::PENDING, true ) );
		}
		$order = new \WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->set_status( \Linker\Commerce\Inquiry\Statuses::PROFORMA );
		$order->update_meta_data( \Linker\Commerce\Proforma\Issuer::NUMBER_META, 'SYNTHETIC-FIRST-LOCK-' . self::tag() );
		$order->update_meta_data( \Linker\Commerce\Proforma\Issuer::ISSUED_META, (string) time() );
		$order->update_meta_data( \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::PENDING, 'yes' );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::class ];
		self::assertInstanceOf( \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::class, $email );
		$key           = 'proforma' === $writer ? 'release-' . $order->get_id() : 'vat-source-' . $id;
		$lock          = 'linker-assessment-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $key );
		$peer          = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$marker        = 'synthetic-first-lock-caller-' . self::tag();
		$before_jobs   = self::newest_mail_job();
		$before_source = $peer->get_var( $peer->prepare( 'SELECT meta_value FROM %i WHERE user_id=%d AND meta_key=%s', $wpdb->usermeta, $id, $notices::SOURCE ) );
		$before_budget = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		$hits          = 0;
		$failed        = false;
		$kill          = static function ( string $sql ) use ( $lock, $peer, &$hits ): string {
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
		add_filter( 'query', $kill, 999 );
		try {
			try {
				if ( 'vat_persist' === $writer ) {
					$failed = is_wp_error(
						$notices->persist(
							$id,
							'DE987654321',
							array(
								'status' => \Linker\Commerce\Registration\VatProfile::VALID,
								'detail' => '',
							),
							true,
							$source['version']
						)
					);
				} elseif ( 'vat_erase' === $writer ) {
					$notices->erase( array(), $customer );
				} elseif ( 'vat_deliver' === $writer ) {
					$vat_email = WC()->mailer()->get_emails()[ \Linker\Commerce\Registration\Emails\VatReviewEmail::class ];
					self::assertInstanceOf( \Linker\Commerce\Registration\Emails\VatReviewEmail::class, $vat_email );
					( new \Linker\Commerce\Mail\Producer() )->woocommerce( array( $vat_email, 'trigger' ), $vat_email )( $id );
				} else {
					$email->trigger( $order->get_id(), $order );
				}
			} catch ( \Throwable $error ) {
				$failed = true;
			}
			$caller_rows  = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, $marker ) );
			$after_source = $peer->get_var( $peer->prepare( 'SELECT meta_value FROM %i WHERE user_id=%d AND meta_key=%s', $wpdb->usermeta, $id, $notices::SOURCE ) );
			$jobs         = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE post_type=%s AND ID>%d', $wpdb->posts, \Linker\Commerce\Mail\JobStore::POST_TYPE, $before_jobs ) );
			$after_budget = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		} finally {
			remove_filter( 'query', $kill, 999 );
			self::assertTrue( $wpdb->db_connect( false ) );
			delete_option( $marker );
			$peer->close();
			clean_user_cache( $id );
			wp_cache_delete( $id, 'user_meta' );
		}
		self::assertSame( 1, $hits );
		$fresh = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		self::assertInstanceOf( \WC_Order::class, $fresh );
		self::assertTrue(
			$failed,
			'Losing the original connection before the native source mutex must fail closed: ' . wp_json_encode(
				array(
					'caller_rows'           => $caller_rows,
					'source_changed'        => $before_source !== $after_source,
					'new_jobs'              => $jobs,
					'proforma_acknowledged' => '' !== $fresh->get_meta( $email::ACCEPTED ),
				)
			)
		);
		self::assertSame( 0, $caller_rows );
		self::assertSame( $before_source, $after_source );
		self::assertSame( 0, $jobs );
		self::assertSame( $before_budget, $after_budget );
		self::assertSame( '', $fresh->get_meta( $email::ACCEPTED ) );
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

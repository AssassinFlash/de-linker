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

	/**
	 * Outbox's initial transaction probe and held-meta read precede its final native writer.
	 *
	 * @testWith ["intercept"]
	 *           ["retry"]
	 * @param string $entry Actual native mail entry.
	 */
	public function test_first_outbox_read_cannot_turn_a_lost_caller_into_transport( string $entry ): void {
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
		$customer = $this->customer();
		$user     = get_userdata( $customer->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$message = \Linker\Commerce\Mail\Prepared::capture(
			static function () use ( $user ): void {
				wp_password_change_notification( $user );
			}
		);
		self::assertInstanceOf( \Linker\Commerce\Mail\Message::class, $message );
		self::assertTrue( \Linker\Commerce\Mail\NativeOrigin::valid( $message ) );
		$store       = new \Linker\Commerce\Mail\JobStore();
		$before_jobs = self::newest_mail_job();
		$job         = 'retry' === $entry ? $store->create( $message ) : 0;
		if ( 'retry' === $entry ) {
			self::assertGreaterThan( 0, $job );
			wp_cache_delete( $job, 'post_meta' ); }
		$peer            = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$before_budget   = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		$before_capacity = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Protection\IntakeStore::OPTION ) );
		$before_actions  = $peer->get_results( $peer->prepare( 'SELECT action_id,args,status FROM %i WHERE hook=%s ORDER BY action_id', $wpdb->prefix . 'actionscheduler_actions', \Linker\Commerce\Mail\Outbox::HOOK ), ARRAY_A );
		$before_meta     = $peer->get_results( $peer->prepare( 'SELECT meta_key,meta_value FROM %i WHERE post_id=%d ORDER BY meta_id', $wpdb->postmeta, $job ), ARRAY_A );
		$marker          = 'synthetic-outbox-first-read-' . self::tag();
		$hits            = 0;
		$transports      = 0;
		$kill            = static function ( string $sql ) use ( $entry, $job, $peer, &$hits ): string {
			global $wpdb;
			$target = 'intercept' === $entry ? str_starts_with( $sql, 'SAVEPOINT linker_mail_' ) : str_starts_with( $sql, 'SELECT' ) && str_contains( $sql, $wpdb->postmeta ) && preg_match( '/\b' . $job . '\b/', $sql );
			if ( 0 === $hits && $target ) {
				++$hits;
				$peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id ); }
			return $sql;
		};
		$transport       = static function ( $pre, array $atts ) use ( &$hits, &$transports, $message ) {
			if ( $hits > 0 && $message->subject === $atts['subject'] ) {
				++$transports;
				return true; }
			return $pre;
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
		add_filter( 'pre_wp_mail', $transport, -1000, 2 );
		try {
			try {
				if ( 'intercept' === $entry ) {
					wp_password_change_notification( $user );
				} else {
					/** This action is documented in Mail\Module::register(). */
					do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Actual original-job consumer under test.
				}
			} catch ( \Throwable $error ) {
				self::assertInstanceOf( \RuntimeException::class, $error );
			}
			$caller_rows    = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, $marker ) );
			$after_budget   = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
			$job_rows       = 'retry' === $entry ? (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE ID=%d', $wpdb->posts, $job ) ) : (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE post_type=%s AND ID>%d', $wpdb->posts, \Linker\Commerce\Mail\JobStore::POST_TYPE, $before_jobs ) );
			$after_capacity = $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Protection\IntakeStore::OPTION ) );
			$after_actions  = $peer->get_results( $peer->prepare( 'SELECT action_id,args,status FROM %i WHERE hook=%s ORDER BY action_id', $wpdb->prefix . 'actionscheduler_actions', \Linker\Commerce\Mail\Outbox::HOOK ), ARRAY_A );
			$after_meta     = $peer->get_results( $peer->prepare( 'SELECT meta_key,meta_value FROM %i WHERE post_id=%d ORDER BY meta_id', $wpdb->postmeta, $job ), ARRAY_A );
		} finally {
			remove_filter( 'query', $kill, 999 );
			remove_filter( 'pre_wp_mail', $transport, -1000 );
			self::assertTrue( $wpdb->db_connect( false ) );
			delete_option( $marker );
			$peer->close();
		}
		self::assertSame( 1, $hits );
		self::assertSame(
			0,
			$transports,
			(string) wp_json_encode(
				array(
					'entry'             => $entry,
					'caller_rows'       => $caller_rows,
					'transports'        => $transports,
					'budget_changed'    => $before_budget !== $after_budget,
					'original_job_rows' => $job_rows,
				)
			)
		);
		self::assertSame( 0, $caller_rows );
		self::assertSame( $before_budget, $after_budget );
		self::assertSame( $before_capacity, $after_capacity );
		self::assertSame( $before_actions, $after_actions );
		if ( 'retry' === $entry ) {
			self::assertSame( 1, $job_rows );
			self::assertSame( $before_meta, $after_meta );
			self::assertNotNull( $store->load( $job ) );
		} else {
			self::assertSame( 0, $job_rows );
		}
	}

	/** An actual failed single action must retain a later consumer for the same committed job.
	 *
	 * @testWith ["held",false]
	 *           ["probe",false]
	 *           ["held",true]
	 *           ["bound",false]
	 * @param string $entry Initial authoritative read.
	 * @param bool   $schedule_failure Refuse the first native successor to exercise independent recovery.
	 */
	public function test_native_action_scheduler_first_read_failure_retains_original_job_consumer( string $entry, bool $schedule_failure ): void {
		global $wpdb;
		$before_capacity = get_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		$this->later(
			static function () use ( $before_capacity ): void {
				delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
				if ( false !== $before_capacity ) {
					update_option( \Linker\Commerce\Protection\IntakeStore::OPTION, $before_capacity, false );
				}
			}
		);
		$customer = $this->customer();
		$user     = get_userdata( $customer->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$message = \Linker\Commerce\Mail\Prepared::capture(
			static function () use ( $user ): void {
				wp_password_change_notification( $user );
			}
		);
		self::assertInstanceOf( \Linker\Commerce\Mail\Message::class, $message );
		self::assertTrue( \Linker\Commerce\Mail\NativeOrigin::valid( $message ) );
		$store   = new \Linker\Commerce\Mail\JobStore();
		$job     = $store->create( $message );
		$actions = as_get_scheduled_actions(
			array(
				'hook'   => \Linker\Commerce\Mail\Outbox::HOOK,
				'args'   => array( $job ),
				'group'  => \Linker\Commerce\Mail\Outbox::GROUP,
				'status' => 'pending',
			),
			'ids'
		);
		self::assertCount( 1, $actions );
		$action    = (int) $actions[0];
		$original  = $store->load( $job );
		$capacity  = get_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		$budget    = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		$peer      = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$hits      = 0;
		$sent      = 0;
		$kill      = static function ( string $sql ) use ( $entry, $job, $peer, &$hits ): string {
			global $wpdb;
			$target = 'probe' === $entry ? str_starts_with( $sql, 'SAVEPOINT linker_mail_' ) : str_starts_with( $sql, 'SELECT' ) && str_contains( $sql, $wpdb->postmeta ) && preg_match( '/\b' . $job . '\b/', $sql );
			if ( 0 === $hits && $target ) {
				++$hits;
				$peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		$transport = static function ( $pre ) use ( &$sent ) {
			++$sent;
			return null === $pre ? true : $pre;
		};
		$refused   = 0;
		$refuse    = static function ( $pre, $timestamp, $hook, $args ) use ( $job, $schedule_failure, &$hits, &$refused ) {
			if ( $schedule_failure && $hits > 0 && \Linker\Commerce\Mail\Outbox::HOOK === $hook && array( $job ) === $args ) {
				++$refused;
				return 0;
			}
			return $pre;
		};
		wp_cache_delete( $job, 'post_meta' );
		add_filter( 'query', $kill, 999 );
		add_filter( 'pre_wp_mail', $transport, -1000 );
		add_filter( 'pre_as_schedule_single_action', $refuse, 10, 4 );
		try {
			\ActionScheduler_QueueRunner::instance()->process_action( $action, 'native first-read connection failure' );
		} finally {
			remove_filter( 'query', $kill, 999 );
			remove_filter( 'pre_wp_mail', $transport, -1000 );
			remove_filter( 'pre_as_schedule_single_action', $refuse, 10 );
			self::assertTrue( $wpdb->db_connect( false ) );
		}
		$this->later(
			static function () use ( $peer ): void {
				$peer->close();
			}
		);
		self::assertSame( 1, $hits );
		self::assertSame( 'failed', \ActionScheduler::store()->get_status( $action ) );
		self::assertSame( 0, $sent );
		self::assertEquals( $original, $store->load( $job ) );
		self::assertSame( $capacity, get_option( \Linker\Commerce\Protection\IntakeStore::OPTION ) );
		self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		$phase = get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true );
		self::assertIsArray( $phase );
		self::assertSame( 1, $phase['count'] );
		self::assertSame( $action, $phase['action'] );
		if ( $schedule_failure ) {
			self::assertGreaterThan( 0, $refused );
			self::assertSame( 0, $phase['scheduled'] );
			self::assertSame( 'notification_not_accepted', get_option( \Linker\Commerce\Mail\CapacityHealth::OPTION )['reason'] );
			self::assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ) );
			update_post_meta( $job, \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'synthetic retained original' ) );
			( new \Linker\Commerce\Mail\InitialReadRecovery( $store ) )->recover();
			self::assertSame( $phase, get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true ) );
			self::assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ) );
			delete_post_meta( $job, \Linker\Commerce\Mail\NotificationHold::META );
		}
		/** This action is documented in Inquiry\Assessment\RecoverySchedule. */
		do_action( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Actual existing recovery, not a fabricated retry.
		self::assertTrue( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ), 'The committed native job must still have a pending consumer after its single action failed.' );
		$phase    = get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true );
		$recovery = new \Linker\Commerce\Mail\InitialReadRecovery( $store );
		$recovery->failed( $action, new \Exception( 'native wrapper', 0, new \Linker\Commerce\Mail\InitialReadFailure( new \RuntimeException( 'synthetic initial read' ) ) ) );
		$recovery->recover();
		self::assertSame( $phase, get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true ), 'Duplicate native callbacks and heartbeat retain the same successor and failure count.' );
		$pending = as_get_scheduled_actions(
			array(
				'hook'   => \Linker\Commerce\Mail\Outbox::HOOK,
				'args'   => array( $job ),
				'group'  => \Linker\Commerce\Mail\Outbox::GROUP,
				'status' => 'pending',
			),
			'ids'
		);
		self::assertSame( array( $phase['scheduled'] ), array_map( 'intval', $pending ) );
		if ( 'probe' === $entry ) {
			add_filter( 'pre_wp_mail', $transport, -1000 );
			try {
				\ActionScheduler_QueueRunner::instance()->process_action( $phase['scheduled'], 'native recovered original notification' );
			} finally {
				remove_filter( 'pre_wp_mail', $transport, -1000 );
			}
			self::assertSame( 1, $sent, 'The recovered original, still natively authorized message reaches synthetic transport once.' );
			self::assertNull( $store->load( $job ) );
			self::assertSame( '', get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true ) );
			return;
		}
		if ( 'bound' === $entry ) {
			$maximum = count( \Linker\Commerce\Mail\Outbox::RETRY_DELAYS ) + 1;
			for ( $failure = 2; $failure <= $maximum; ++$failure ) {
				$hits = 0;
				wp_cache_delete( $job, 'post_meta' );
				add_filter( 'query', $kill, 999 );
				try {
					\ActionScheduler_QueueRunner::instance()->process_action( $phase['scheduled'], 'native bounded initial-read recovery' );
				} finally {
					remove_filter( 'query', $kill, 999 );
					self::assertTrue( $wpdb->db_connect( false ) );
				}
				self::assertSame( 1, $hits );
				$phase = get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true );
				self::assertSame( $failure, $phase['count'] );
				$recovery->failed( $action, new \Exception( 'late old callback', 0, new \Linker\Commerce\Mail\InitialReadFailure( new \RuntimeException( 'synthetic initial read' ) ) ) );
				self::assertSame( $phase, get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true ) );
			}
			self::assertSame( 0, $phase['due'] );
			self::assertSame( 0, $phase['scheduled'] );
			$recovery->recover();
			self::assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ) );
			self::assertEquals( $original, $store->load( $job ) );
			self::assertSame( $capacity, get_option( \Linker\Commerce\Protection\IntakeStore::OPTION ) );
			self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
			return;
		}
		// A later failure outside the typed initial reads must never consume the
		// previous phase again, even while the complete job is still retained.
		$unknown = static function (): void {
			throw new \RuntimeException( 'synthetic unknown external outcome' );
		};
		add_action( \Linker\Commerce\Mail\Outbox::HOOK, $unknown, 1 );
		try {
			\ActionScheduler_QueueRunner::instance()->process_action( $phase['scheduled'], 'native non-initial failure control' );
		} finally {
			remove_action( \Linker\Commerce\Mail\Outbox::HOOK, $unknown, 1 );
		}
		self::assertSame( 'failed', \ActionScheduler::store()->get_status( $phase['scheduled'] ) );
		$recovery->recover();
		self::assertSame( $phase, get_post_meta( $job, \Linker\Commerce\Mail\InitialReadRecovery::META, true ) );
		self::assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		self::assertEquals( $original, $store->load( $job ) );
		self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
	}

	/**
	 * Each new outer mutex is exercised through its native owner, not a replacement lock.
	 *
	 * @testWith ["reschedule"]
	 *           ["disposition"]
	 *           ["forget"]
	 *           ["intake"]
	 * @param string $entry Native capacity entry.
	 */
	public function test_new_native_entry_first_mutex_cannot_publish_after_caller_loss( string $entry ): void {
		global $wpdb;
		$restore = array();
		foreach ( array( \Linker\Commerce\Protection\IntakeStore::OPTION, \Linker\Commerce\Protection\Ledger::OPTION ) as $option ) {
			$restore[ $option ] = get_option( $option );
			delete_option( $option );
		}
		$cookie = $_COOKIE;
		$this->later(
			static function () use ( $restore, $cookie ): void {
				foreach ( $restore as $option => $value ) {
					delete_option( $option );
					if ( false !== $value ) {
								update_option( $option, $value, false ); }
				}
				$_COOKIE = $cookie;
			}
		);
		if ( 'reschedule' === $entry ) {
			$store = new \Linker\Commerce\Mail\JobStore();
			$id    = $store->create( new \Linker\Commerce\Mail\Message( array( self::TESTER ), 'Synthetic source schedule', 'Original complete job.', array(), array() ) );
			self::assertGreaterThan( 0, $id );
			$key  = 'mail-schedule-' . $id;
			$work = static fn () => $store->reschedule( $id, time() + HOUR_IN_SECONDS );
			$args = wp_json_encode( array( $id ) );
			$read = static fn ( \wpdb $peer ) => $peer->get_results( $peer->prepare( 'SELECT action_id,scheduled_date_gmt FROM %i WHERE hook=%s AND args=%s AND status=%s ORDER BY action_id', $wpdb->prefix . 'actionscheduler_actions', \Linker\Commerce\Mail\Outbox::HOOK, $args, 'pending' ), ARRAY_A );
		} elseif ( 'intake' === $entry ) {
			$_COOKIE[ \Linker\Commerce\Protection\Identity::COOKIE ] = md5( 'synthetic-native-first-lock' );
			$identity = \Linker\Commerce\Protection\Identity::current();
			self::assertInstanceOf( \Linker\Commerce\Protection\Identity::class, $identity );
			$id   = wp_generate_uuid4();
			$key  = 'intake-write-' . $id;
			$work = static fn () => \Linker\Commerce\Protection\Intake::run( 'verification', 'contact', $id, hash( 'sha256', $id ), $identity, array( 'message' => 'Synthetic original caller' ), array( new \Linker\Commerce\Protection\Allowance( 'synthetic_first_lock_site', 'site', 10, HOUR_IN_SECONDS ) ), array(), array(), static fn () => new \WP_Error( 'synthetic_no_business_write' ) );
			$read = static fn ( \wpdb $peer ) => $peer->get_var( $peer->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, \Linker\Commerce\Protection\IntakeStore::OPTION ) );
		} else {
			$order = new \WC_Order();
			$order->set_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED );
			if ( 'disposition' === $entry ) {
				$this->as_user( 1 );
				$order->set_customer_note( 'Вам перевод 123 руб. забрать тут https://fredmer.buzz/synthetic-first-lock' );
				$order->update_meta_data( '_linker_inquiry_source', 'contact' );
				\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, \Linker\Commerce\Inquiry\Assessment\Queue::META, array( 'snapshot' => array( 'submission' => array( 'message' => $order->get_customer_note() ) ) ) );
			} else {
				$order->update_meta_data( \Linker\Commerce\Protection\Intake::META, 'synthetic-existing-review' );
			}
			$order->save();
			$id = $order->get_id();
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
			if ( 'disposition' === $entry ) {
				$key       = 'historical-disposition-' . $id;
				$operation = wp_generate_uuid4();
				$hash      = hash( 'sha256', \Linker\Commerce\Protection\BusinessDisposition::body( $order ) );
				$work      = static fn () => \Linker\Commerce\Protection\BusinessDisposition::run( $id, $hash, $operation );
				$read      = static fn ( \wpdb $peer ) => $peer->get_results( $peer->prepare( 'SELECT comment_ID,comment_content FROM %i WHERE comment_post_ID=%d ORDER BY comment_ID', $wpdb->comments, $id ), ARRAY_A );
			} else {
				$key    = 'release-' . $id;
				$work   = static fn () => \Linker\Commerce\Protection\IntakeStore::forget( $order );
				$meta   = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ? $wpdb->prefix . 'wc_orders_meta' : $wpdb->postmeta;
				$column = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ? 'order_id' : 'post_id';
				$read   = static fn ( \wpdb $peer ) => $peer->get_results( $peer->prepare( 'SELECT meta_key,meta_value FROM %i WHERE %i=%d AND meta_key=%s', $meta, $column, $id, \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ), ARRAY_A );
			}
		}
		$result = $this->first_mutex_probe( $key, $work, $read );
		self::assertSame( 1, $result['hits'] );
		self::assertTrue( $result['failed'] );
		self::assertSame( 0, $result['caller_rows'] );
		self::assertTrue( $result['state_unchanged'], (string) wp_json_encode( $result ) );
	}

	/**
	 * Independent readback keeps the caller's lost write separate from new committed state.
	 *
	 * @param string                $key Exact original source mutex.
	 * @param callable():mixed      $work Native entry, never transport/provider.
	 * @param callable(\wpdb):mixed $read Exact native state on the independent observer.
	 * @return array{hits:int,failed:bool,caller_rows:int,state_unchanged:bool}
	 */
	private function first_mutex_probe( string $key, callable $work, callable $read ): array {
		global $wpdb;
		$peer   = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$lock   = 'linker-assessment-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $key );
		$marker = 'synthetic-first-mutex-' . self::tag();
		$hits   = 0;
		$failed = false;
		$before = $read( $peer );
		$kill   = static function ( string $sql ) use ( $lock, $peer, &$hits ): string {
			if ( 0 === $hits && str_contains( $sql, 'GET_LOCK(' ) && str_contains( $sql, $lock ) ) {
				++$hits;
				global $wpdb;
				$peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			} return $sql;
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
				$failed = is_wp_error( $work() );
			} catch ( \Throwable $error ) {
				$failed = true; }
			$after = $read( $peer );
			$rows  = (int) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE option_name=%s', $wpdb->options, $marker ) );
		} finally {
			remove_filter( 'query', $kill, 999 );
			self::assertTrue( $wpdb->db_connect( false ) );
			delete_option( $marker );
			$peer->close();
		}
		return array(
			'hits'            => $hits,
			'failed'          => $failed,
			'caller_rows'     => $rows,
			'state_unchanged' => $before === $after,
		);
	}

	/**
	 * Only mutex SQL changes policy; an unconfirmed release cannot conceal the work's error.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $primary Whether the work already failed.
	 */
	public function test_guarded_mutex_release_is_confirmed_without_masking_the_original_error( bool $primary ): void {
		global $wpdb;
		$key      = 'synthetic-guarded-release-' . self::tag();
		$name     = 'linker-assessment-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $key );
		$before   = self::retries();
		$hits     = 0;
		$caught   = null;
		$original = new \RuntimeException( 'synthetic-original-work-failure' );
		$reject   = static function ( string $sql ) use ( $name, &$hits ): string {
			if ( str_contains( $sql, 'RELEASE_LOCK(' ) && str_contains( $sql, $name ) ) {
				++$hits;
				return 'SELECT 0';
			} return $sql;
		};
		add_filter( 'query', $reject, 999 );
		try {
			try {
				\Linker\Commerce\Inquiry\Assessment\Lock::run(
					$key,
					static function () use ( $before, $primary, $original ): void {
						self::assertSame( $before, self::retries(), 'The callback can perform its model/SMTP work without a persistent SQL policy scope.' );
						if ( $primary ) {
							throw $original;
						} },
					0,
					true
				);
			} catch ( \Throwable $error ) {
				$caught = $error; }
		} finally {
			remove_filter( 'query', $reject, 999 );
			self::assertSame( '1', (string) $wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) ) );
		}
		self::assertSame( 1, $hits );
		self::assertSame( $before, self::retries() );
		self::assertInstanceOf( \RuntimeException::class, $caught );
		if ( $primary ) {
			self::assertSame( $original, $caught );
		} else {
			self::assertSame( 'native_mutex_release_unconfirmed', $caught->getMessage() ); }
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

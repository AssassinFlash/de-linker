<?php
/**
 * Native current-version VAT reminder recovery under the shared mail envelope.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Registration\VatNotice;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;

/** Native acceptance contract.
 *
 * @coversNothing
 */
final class VatNotificationCapacityTest extends IntegrationTestCase {
	/** Isolated registry, native transport still disabled by the instance. */
	protected function setUp(): void {
		parent::setUp();
		$before = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $before ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $before ) {
					update_option( IntakeStore::OPTION, $before, false );
				}
			}
		);
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false );
	}

	/** Approved accounts changing VAT have a persistent latest source, not just a past event. */
	public function test_full_pool_preserves_latest_approved_account_verdict_then_recovers_one_job_without_vies(): void {
		$id = $this->customer()->get_id();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$blocked  = $this->full_ordinary();
		$http     = 0;
		$provider = static function ( $pre, $args, $url ) use ( &$http ) {
			if ( ViesClient::ENDPOINT !== $url ) {
				return $pre;
			}
			++$http;
			self::assertFalse( Capacity::transaction_active(), 'VIES is outside native storage transactions.' );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => '{"valid":true}',
			);
		};
		add_filter( 'pre_http_request', $provider, 1, 3 );
		$this->later(
			static function () use ( $provider ): void {
				remove_filter( 'pre_http_request', $provider, 1 );
			}
		);
		$before = self::newest_mail_job();
		self::assertSame( VatProfile::VALID, ( new VatProfile( new ViesClient() ) )->update( $id, 'DE123456789', true ) );
		self::assertSame( 1, $http );
		$source = get_user_meta( $id, VatNotice::SOURCE, true );
		self::assertSame( 0, $source['job'] );
		self::assertSame( 'yes', get_user_meta( $id, VatNotice::PENDING, true ) );
		self::assertSame( VatProfile::VALID, get_user_meta( $id, VatProfile::STATUS_META, true ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame(
			$id,
			wp_update_user(
				array(
					'ID'         => $id,
					'user_email' => 'updated-vat-' . $id . '@example.test',
				)
			)
		);
		self::assertSame( VatProfile::VALID, ( new VatProfile( new ViesClient() ) )->update( $id, 'DE123456789', true ) );
		$this->free_ordinary( $blocked );
		VatNotice::recover();
		wp_cache_delete( $id, 'user_meta' );
		$accepted = get_user_meta( $id, VatNotice::SOURCE, true );
		self::assertNotSame( $source['version'], $accepted['version'], 'Native email change binds a new latest version without VIES.' );
		self::assertGreaterThan( $before, $accepted['job'] );
		self::assertSame( 'no', get_user_meta( $id, VatNotice::PENDING, true ) );
		$job = ( new JobStore() )->load( $accepted['job'] );
		self::assertNotNull( $job );
		self::assertStringContainsString( 'VAT', $job['message']->subject );
		self::assertTrue( $job['message']->is_internal() );
		self::assertStringContainsString( 'updated-vat-' . $id . '@example.test', implode( '\n', $job['message']->headers ), 'The current native email owns Reply-to, not a stale capture.' );
		VatNotice::recover();
		self::assertSame( $accepted['job'], self::newest_mail_job() );
		self::assertSame( 1, $http, 'Recovery never repeats VIES.' );
	}

	/** Older HTTP results and an exact-generation ACK cannot erase a newer native source. */
	public function test_generation_witness_and_ack_only_accept_the_exact_native_version(): void {
		$id      = $this->customer()->get_id();
		$notices = new VatNotice();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$first = $notices->persist(
			$id,
			'DE123456789',
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			true,
			''
		);
		self::assertIsArray( $first );
		$new = $notices->persist(
			$id,
			'DE987654321',
			array(
				'status' => VatProfile::INVALID,
				'detail' => '',
			),
			true,
			$first['version']
		);
		self::assertIsArray( $new );
		self::assertInstanceOf(
			\WP_Error::class,
			$notices->persist(
				$id,
				'DE123456789',
				array(
					'status' => VatProfile::VALID,
					'detail' => '',
				),
				true,
				$first['version']
			)
		);
		self::assertSame( 'DE987654321', get_user_meta( $id, VatProfile::NUMBER_META, true ) );
		$before = self::newest_mail_job();
		$last   = null;
		$notices->deliver(
			$id,
			static function () use ( $notices, $id, $new, &$last ): Message {
				$last = $notices->persist(
					$id,
					'DE222222222',
					array(
						'status' => VatProfile::VALID,
						'detail' => '',
					),
					true,
					$new['version']
				);
				return new Message( array( self::TESTER ), 'Synthetic VAT old generation', 'Old source must not acknowledge new facts.', array( Message::INTERNAL_HEADER ), array() );
			}
		);
		self::assertIsArray( $last );
		self::assertSame( $before, self::newest_mail_job(), 'Stale job and ACK roll back together.' );
		wp_cache_delete( $id, 'user_meta' );
		self::assertSame( $last, get_user_meta( $id, VatNotice::SOURCE, true ) );
		self::assertSame( 'yes', get_user_meta( $id, VatNotice::PENDING, true ) );
	}

	/** An email change during capture cannot ACK stale Reply-to; recovery uses only latest non-erased facts. */
	public function test_email_change_during_capture_retries_latest_version_and_erasure_stays_final(): void {
		$customer = $this->customer();
		$id       = $customer->get_id();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$notices = new VatNotice();
		$source  = $notices->persist(
			$id,
			'DE123456789',
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			true,
			''
		);
		self::assertIsArray( $source );
		$before = self::newest_mail_job();
		$skip   = static fn (): bool => false;
		add_filter( 'send_email_change_email', $skip );
		try {
			$notices->deliver(
				$id,
				static function () use ( $id ): Message {
					self::assertSame(
						$id,
						wp_update_user(
							array(
								'ID'         => $id,
								'user_email' => 'capture-vat-' . $id . '@example.test',
							)
						)
					);
					return new Message( array( self::TESTER ), 'Synthetic stale VAT email', 'No stale address can be acknowledged.', array( Message::INTERNAL_HEADER ), array() );
				}
			);
		} finally {
			remove_filter( 'send_email_change_email', $skip ); }
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( 'yes', get_user_meta( $id, VatNotice::PENDING, true ) );
		VatNotice::recover();
		$latest = get_user_meta( $id, VatNotice::SOURCE, true );
		self::assertNotSame( $source['version'], $latest['version'] );
		self::assertGreaterThan( $before, $latest['job'] );
		$job = ( new JobStore() )->load( $latest['job'] );
		self::assertNotNull( $job );
		self::assertStringContainsString( 'capture-vat-' . $id . '@example.test', implode( '\n', $job['message']->headers ) );
		$notices->erase( array(), $customer );
		VatNotice::recover();
		self::assertSame( $latest['job'], self::newest_mail_job() );
		self::assertTrue( get_user_meta( $id, VatNotice::SOURCE, true )['erased'] );
	}

	/** Native write failure is not falsely published as a pending changed verdict. */
	public function test_verdict_stamp_failure_rolls_back_both_native_fields_and_source(): void {
		$id = $this->customer()->get_id();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$fail = static fn ( $check, $user, $key ) => $id === $user && VatNotice::SOURCE === $key ? false : $check;
		add_filter( 'add_user_metadata', $fail, 10, 3 );
		$this->later(
			static function () use ( $fail ): void {
				remove_filter( 'add_user_metadata', $fail, 10 );
			}
		);
		$result = ( new VatNotice() )->persist(
			$id,
			'DE123456789',
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			true,
			''
		);
		self::assertInstanceOf( \WP_Error::class, $result );
		self::assertSame( VatProfile::INVALID, get_user_meta( $id, VatProfile::STATUS_META, true ) );
		self::assertSame( '', get_user_meta( $id, VatNotice::SOURCE, true ) );
		self::assertSame( '', get_user_meta( $id, VatNotice::PENDING, true ) );
	}

	/** Erasure tombstones even first in-flight checks; native deletion cannot recover a source. */
	public function test_native_erasure_and_deletion_do_not_resurrect_or_notify_old_sources(): void {
		$customer = $this->customer();
		$id       = $customer->get_id();
		$notices  = new VatNotice();
		$witness  = $notices->version( $id );
		$notices->erase( array(), $customer );
		self::assertTrue( get_user_meta( $id, VatNotice::SOURCE, true )['erased'] );
		self::assertInstanceOf(
			\WP_Error::class,
			$notices->persist(
				$id,
				'DE123456789',
				array(
					'status' => VatProfile::VALID,
					'detail' => '',
				),
				true,
				$witness
			)
		);
		$before = self::newest_mail_job();
		VatNotice::recover();
		self::assertSame( $before, self::newest_mail_job() );
		$id = $this->customer()->get_id();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$pending = $notices->persist(
			$id,
			'DE123456789',
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			true,
			''
		);
		self::assertIsArray( $pending );
		require_once ABSPATH . 'wp-admin/includes/user.php';
		wp_delete_user( $id );
		$before = self::newest_mail_job();
		VatNotice::recover();
		self::assertSame( $before, self::newest_mail_job() );
		self::assertInstanceOf(
			\WP_Error::class,
			$notices->persist(
				$id,
				'DE999999999',
				array(
					'status' => VatProfile::VALID,
					'detail' => '',
				),
				true,
				$pending['version']
			)
		);
	}

	/** A first VIES response cannot recreate metadata after a peer deleted the cached account. */
	public function test_peer_deleted_account_cannot_receive_a_late_first_vat_source(): void {
		$customer = $this->customer();
		$id       = $customer->get_id();
		$notices  = new VatNotice();
		self::assertSame( '', $notices->version( $id ) );
		self::assertInstanceOf( \WP_User::class, get_userdata( $id ) );
		$before = self::newest_mail_job();
		global $wpdb;
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		try {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Independent connection deletes only this test's native account, deliberately retaining this PHP request's primed caches.
			self::assertSame( 1, $peer->delete( $wpdb->users, array( 'ID' => $id ) ) );
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Same test-owned account metadata, as a completed native deletion leaves it.
			self::assertGreaterThan( 0, $peer->delete( $wpdb->usermeta, array( 'user_id' => $id ) ) );
			self::assertInstanceOf(
				\WP_Error::class,
				$notices->persist(
					$id,
					'DE123456789',
					array(
						'status' => VatProfile::INVALID,
						'detail' => 'Synthetic late VIES result',
					),
					true,
					''
				)
			);
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Prove the source did not recreate orphan native PII after the completed peer deletion.
			self::assertSame( '0', (string) $peer->get_var( $peer->prepare( 'SELECT COUNT(*) FROM %i WHERE user_id=%d', $wpdb->usermeta, $id ) ) );
			self::assertSame( $before, self::newest_mail_job() );
		} finally {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Compensate only this deleted synthetic account's orphan metadata if a red implementation recreated it.
			$peer->delete( $wpdb->usermeta, array( 'user_id' => $id ) );
			$peer->close();
			clean_user_cache( $id );
			wp_cache_delete( $id, 'user_meta' );
		}
	}

	/** Native erasure also holds an already accepted original job without dropping occupancy. */
	public function test_erasure_holds_accepted_job_and_never_recovers_another_one(): void {
		$customer = $this->customer();
		$id       = $customer->get_id();
		update_user_meta( $id, VatProfile::STATUS_META, VatProfile::INVALID );
		$notices = new VatNotice();
		$source  = $notices->persist(
			$id,
			'DE123456789',
			array(
				'status' => VatProfile::VALID,
				'detail' => '',
			),
			true,
			''
		);
		self::assertIsArray( $source );
		VatNotice::recover();
		$accepted = get_user_meta( $id, VatNotice::SOURCE, true );
		self::assertGreaterThan( 0, $accepted['job'] );
		$original = ( new JobStore() )->load( $accepted['job'] );
		$notices->erase( array(), $customer );
		self::assertTrue( \Linker\Commerce\Mail\NotificationHold::job_held( $accepted['job'] ) );
		self::assertArrayHasKey( $accepted['job'], get_option( IntakeStore::OPTION )['mail_capacity']['entries'] );
		$before = self::newest_mail_job();
		VatNotice::recover();
		self::assertSame( $before, self::newest_mail_job() );
		self::assertEquals( $original, ( new JobStore() )->load( $accepted['job'] ) );
	}

	/** This post-VIES source writer cannot commit or roll back its caller's transaction. */
	public function test_outer_transaction_is_preserved_before_any_source_mutation(): void {
		$id = $this->customer()->get_id();
		global $wpdb;
		$wpdb->query( 'START TRANSACTION' );
		try {
			update_user_meta( $id, 'synthetic_568_outer', 'pending' );
			$result = ( new VatNotice() )->persist(
				$id,
				'DE123456789',
				array(
					'status' => VatProfile::VALID,
					'detail' => '',
				),
				true,
				''
			);
			self::assertInstanceOf( \WP_Error::class, $result );
			self::assertTrue( Capacity::transaction_active() );
			self::assertSame( 'pending', get_user_meta( $id, 'synthetic_568_outer', true ) );
			self::assertSame( '', get_user_meta( $id, VatNotice::SOURCE, true ) );
		} finally {
			$wpdb->query( 'ROLLBACK' );
			wp_cache_delete( $id, 'user_meta' );
		}
		self::assertSame( '', get_user_meta( $id, 'synthetic_568_outer', true ) );
	}

	/** Native fixture return shape.
	 *
	 * @return array<string,mixed> Exact previous registry for local restoration.
	 */
	private function full_ordinary(): array {
		$before = get_option( IntakeStore::OPTION );
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 1; $i <= 192; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
		return is_array( $before ) ? $before : array();
	}

	/** Native fixture input.
	 *
	 * @param array<string,mixed> $before Original local registry.
	 */
	private function free_ordinary( array $before ): void {
		delete_option( IntakeStore::OPTION );
		if ( array() !== $before ) {
			update_option( IntakeStore::OPTION, $before, false );
		}
	}
}

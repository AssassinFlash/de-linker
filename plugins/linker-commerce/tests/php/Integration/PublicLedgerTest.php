<?php
/**
 * Multi-dimensional resource accounting on the real WordPress database.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Privacy;
use WP_Error;

/**
 * No business, provider or mail side effects belong in a quota transaction.
 *
 * @coversNothing
 */
final class PublicLedgerTest extends IntegrationTestCase {
	/** Preserve any local ledger instead of consuming its real remaining quota. */
	protected function setUp(): void {
		parent::setUp();
		$old = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$this->later(
			static function () use ( $old ): void {
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
			}
		);
	}

	/** Safe synthetic HMAC-like fingerprints contain no customer payload. */
	private function fingerprint(): string {
		return hash( 'sha256', 'synthetic request' );
	}

	/** Denying the last dimension must leave all earlier dimensions untouched. */
	public function test_multiple_dimensions_never_partially_spend(): void {
		$ledger = new Ledger();
		$a      = new Allowance( 'browser', 'synthetic-browser', 2, DAY_IN_SECONDS );
		$b      = new Allowance( 'site', 'site', 1, DAY_IN_SECONDS );
		$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), array( $a, $b ), 60 ) );
		$denied = $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), array( $a, $b ), 60 );
		$this->assertInstanceOf( WP_Error::class, $denied );
		$this->assertSame( 'linker_admission_quota', $denied->get_error_code() );
		$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), array( $a ), 60 ), 'The failed composite admission did not take the browser slot.' );
	}

	/** Replay is free to read but cannot dispatch twice or refund spent work. */
	public function test_dispatch_replay_and_recovery_keep_the_original_outcome(): void {
		$ledger = new Ledger();
		$limit  = array( new Allowance( 'day', 'synthetic', 1, DAY_IN_SECONDS ) );
		$id     = wp_generate_uuid4();
		$fp     = $this->fingerprint();
		$first  = $ledger->reserve( $id, $fp, $limit, 60 );
		$this->assertIsArray( $first );
		$this->assertSame( $first, $ledger->reserve( strtoupper( $id ), $fp, $limit, 60 ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->dispatch( $id, $fp ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->cancel( $id, $fp ) );
		$done = $ledger->complete( $id, $fp, 42 );
		$this->assertIsArray( $done );
		$this->assertSame( 42, $done['outcome'] );
		$this->assertSame( $done, $ledger->complete( $id, $fp, 42 ) );
		$this->assertSame( $done, $ledger->reserve( $id, $fp, $limit, 60 ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( $id, hash( 'sha256', 'changed' ), $limit, 60 ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( wp_generate_uuid4(), $fp, $limit, 60 ) );
	}

	/** A crashed unused reservation refunds; a dispatched call remains spent. */
	public function test_leases_recover_without_a_free_second_upstream_request(): void {
		$now    = 1600000000;
		$ledger = new Ledger(
			static function () use ( &$now ): int {
				return $now;
			}
		);
		$limits = array( new Allowance( 'day', 'synthetic', 1, DAY_IN_SECONDS ), new Allowance( 'flight', 'site', 1, 0 ) );
		$fp     = $this->fingerprint();
		$unused = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $unused, $fp, $limits, 5 ) );
		$now += 6;
		$sent = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $sent, $fp, $limits, 5 ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->dispatch( $unused, $fp ) );
		$this->assertIsArray( $ledger->dispatch( $sent, $fp ) );
		$now += 6;
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( wp_generate_uuid4(), $fp, $limits, 5 ) );
		$old = $ledger->reserve( $sent, $fp, $limits, 5 );
		$this->assertIsArray( $old );
		$this->assertSame( 'unresolved', $old['status'] );
		$this->assertIsArray( $ledger->complete( $sent, $fp, 7 ), 'Late reconciliation never dispatches the request again.' );
		$now = ( intdiv( $now, DAY_IN_SECONDS ) + 1 ) * DAY_IN_SECONDS + 1;
		$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), $fp, $limits, 5 ) );
	}

	/** Login imports actual anonymous spend once, not a new free allowance. */
	public function test_login_carry_is_atomic_and_preserves_actual_guest_spend(): void {
		$ledger  = new Ledger();
		$guest   = new Allowance( 'anonymous_day', 'browser', 3, DAY_IN_SECONDS, 2 );
		$account = new Allowance( 'account_day', 'account', 3, DAY_IN_SECONDS );
		$fp      = $this->fingerprint();
		$id      = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( $guest ), 60 ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp ) );
		$carry  = array(
			array(
				'source' => $guest,
				'target' => $account,
			),
		);
		$logged = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $logged, $fp, array( $account ), 60, $carry ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( wp_generate_uuid4(), $fp, array( $account ), 60, $carry ) );
		$this->assertIsArray( $ledger->cancel( $logged, $fp ) );
		$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), $fp, array( $account ), 60, $carry ), 'Only the unused logged-in unit was returned, not the imported guest spend.' );
	}

	/** An anonymous request not yet dispatched is not imported as actual spend. */
	public function test_login_does_not_import_unused_anonymous_reservations(): void {
		$ledger  = new Ledger();
		$guest   = new Allowance( 'guest_day', 'browser', 2, DAY_IN_SECONDS, 2 );
		$account = new Allowance( 'account_day', 'account', 1, DAY_IN_SECONDS );
		$fp      = $this->fingerprint();
		$id      = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( $guest ), 60 ) );
		$this->assertIsArray(
			$ledger->reserve(
				wp_generate_uuid4(),
				$fp,
				array( $account ),
				60,
				array(
					array(
						'source' => $guest,
						'target' => $account,
					),
				)
			)
		);
		$this->assertIsArray( $ledger->cancel( $id, $fp ) );
	}

	/** Corruption is reported without resetting limits or leaking stored input. */
	public function test_corrupt_state_is_not_accepted_as_a_fresh_budget(): void {
		update_option( Ledger::OPTION, 'corrupt synthetic journal', false );
		$result = ( new Ledger() )->reserve( wp_generate_uuid4(), $this->fingerprint(), array( new Allowance( 'day', 'site', 1, DAY_IN_SECONDS ) ), 60 );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_admission_storage', $result->get_error_code() );
		$this->assertSame( 'corrupt synthetic journal', get_option( Ledger::OPTION ) );
		$this->assertStringNotContainsString( 'corrupt synthetic', $result->get_error_message() );
	}

	/** A second real database connection cannot take the mutex or last slot. */
	public function test_real_second_connection_cannot_take_the_last_allowance(): void {
		global $wpdb;
		$original = $wpdb;
		$other    = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$other->set_prefix( $original->prefix );
		$name   = 'linker-admission-' . md5( (string) constant( 'DB_NAME' ) . '/' . $original->prefix );
		$ledger = new Ledger();
		$limits = array( new Allowance( 'day', 'site', 1, DAY_IN_SECONDS ) );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- This second connection holds the real server mutex while the first attempts admission.
		$this->assertSame( '1', (string) $other->get_var( $other->prepare( 'SELECT GET_LOCK(%s, 0)', $name ) ) );
		try {
			$busy = $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), $limits, 60 );
			$this->assertInstanceOf( WP_Error::class, $busy );
			$this->assertSame( 'linker_admission_busy', $busy->get_error_code() );
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
			$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), $limits, 60 ) );
			$wpdb   = $other;
			$denied = $ledger->reserve( wp_generate_uuid4(), $this->fingerprint(), $limits, 60 );
			$this->assertInstanceOf( WP_Error::class, $denied );
			$this->assertSame( 'linker_admission_quota', $denied->get_error_code() );
		} finally {
			$wpdb = $original;
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
			$other->close();
		}
		// phpcs:enable
	}
	/** A verified privacy request removes only its linked payload and cannot be undone by a late completion. */
	public function test_privacy_is_scoped_and_late_completion_cannot_restore_erased_data(): void {
		$ledger = new Ledger();
		$a      = new Allowance( 'account', 'account-a', 1, DAY_IN_SECONDS );
		$b      = new Allowance( 'account', 'account-b', 1, DAY_IN_SECONDS );
		$global = new Allowance( 'global_day', 'site', 2, DAY_IN_SECONDS );
		$fp     = $this->fingerprint();
		$first  = wp_generate_uuid4();
		$second = wp_generate_uuid4();
		foreach ( array( array( $first, $a, 42 ), array( $second, $b, 43 ) ) as [ $id, $account, $outcome ] ) {
			$this->assertIsArray( $ledger->reserve( $id, $fp, array( $account, $global ), 60 ) );
			$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
			$this->assertIsArray( $ledger->complete( $id, $fp, $outcome ) );
		}
		$export = $ledger->privacy( array( $a->owner() ), false );
		$this->assertIsArray( $export );
		$this->assertSame( array( $first ), array_column( $export['data'], 'id' ) );
		$this->assertIsArray( $ledger->privacy( array( $a->owner() ), true ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->complete( $first, $fp, 42 ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->lookup( $first, $fp ) );
		$remaining = $ledger->privacy( array( $a->owner() ), false );
		$this->assertIsArray( $remaining );
		$this->assertSame( array(), $remaining['data'] );
		$other = $ledger->privacy( array( $b->owner() ), false );
		$this->assertIsArray( $other );
		$this->assertSame( array( $second ), array_column( $other['data'], 'id' ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( wp_generate_uuid4(), $fp, array( $a, $global ), 60 ), 'Privacy removal cannot refund work already dispatched to the site-wide budget.' );
	}
	/** Native privacy registration resolves a verified account, never the current staff user. */
	public function test_native_privacy_callbacks_resolve_only_the_verified_requester(): void {
		$customer = $this->customer();
		$subject  = Identity::account( $customer->get_id() );
		$ledger   = new Ledger();
		$id       = wp_generate_uuid4();
		$fp       = $this->fingerprint();
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'account_day', $subject, 2, DAY_IN_SECONDS ) ), 60 ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp, 42 ) );
		$privacy = new Privacy();
		$privacy->register();
		try {
			$exporters = apply_filters( 'wp_privacy_personal_data_exporters', array() ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WordPress's native privacy registration, invoked as its verified-request path does.
			$export    = $exporters['linker-public-protection']['callback']( $customer->get_email(), 1 );
			$this->assertTrue( $export['done'] );
			$this->assertContains( 'admission-' . $id, array_column( $export['data'], 'item_id' ) );
			$erasers = apply_filters( 'wp_privacy_personal_data_erasers', array() ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WordPress's native privacy registration, invoked as its verified-request path does.
			$erased  = $erasers['linker-public-protection']['callback']( $customer->get_email(), 1 );
			$this->assertTrue( $erased['items_removed'] );
			$this->assertTrue( $erased['items_retained'], 'The minimal replay marker retention is disclosed.' );
			$after = $exporters['linker-public-protection']['callback']( $customer->get_email(), 1 );
			$this->assertSame( array(), $after['data'] );
		} finally {
			remove_filter( 'wp_privacy_personal_data_exporters', array( $privacy, 'exporters' ) );
			remove_filter( 'wp_privacy_personal_data_erasers', array( $privacy, 'erasers' ) );
		}
	}
	/** Privacy ownership of imported spend survives its shorter counter window. */
	public function test_imported_receipt_remains_exportable_after_the_counter_window(): void {
		$now     = 1600000000;
		$ledger  = new Ledger(
			static function () use ( &$now ): int {
				return $now;
			}
		);
		$guest   = new Allowance( 'guest', 'browser', 3, 60 );
		$account = new Allowance( 'account', 'account', 3, 60 );
		$fp      = $this->fingerprint();
		$id      = wp_generate_uuid4();
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( $guest ), 5 ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp ) );
		$this->assertIsArray(
			$ledger->reserve(
				wp_generate_uuid4(),
				$fp,
				array( $account ),
				5,
				array(
					array(
						'source' => $guest,
						'target' => $account,
					),
				)
			)
		);
		$now   += 61;
		$export = $ledger->privacy( array( $account->owner() ), false );
		$this->assertIsArray( $export );
		$this->assertContains( $id, array_column( $export['data'], 'id' ) );
	}
}

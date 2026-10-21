<?php
/**
 * Business-door policy against the native atomic journal.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\BusinessPolicy;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use WP_Error;

/**
 * A shared connection is not the narrow customer quota.
 *
 * @coversNothing
 */
final class BusinessPolicyTest extends IntegrationTestCase {
	/** Preserve the real instance journal and direct-connection fixture. */
	protected function setUp(): void {
		parent::setUp();
		$old     = get_option( Ledger::OPTION );
		$address = $_SERVER['REMOTE_ADDR'] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Preserve the runner's direct connection fixture.
		delete_option( Ledger::OPTION );
		$_SERVER['REMOTE_ADDR'] = '192.0.2.15';
		$this->later(
			static function () use ( $old, $address ): void {
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false ); }
				if ( null === $address ) {
					unset( $_SERVER['REMOTE_ADDR'] );
				} else {
					$_SERVER['REMOTE_ADDR'] = $address; }
			}
		);
	}

	/** Different forms share a subject budget, while shared-NAT customers remain independent. */
	public function test_business_actions_share_subject_limits_without_the_old_three_per_ip_gate(): void {
		$policy = new BusinessPolicy();
		$ledger = new Ledger();
		for ( $customer = 0; $customer < 2; ++$customer ) {
			$identity = new Identity( hash( 'sha256', 'browser-' . $customer ), '' );
			foreach ( array( 'contact', 'inquiry', 'genie_contact', 'genie_inquiry', 'conversation_mail' ) as $action ) {
				$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), hash( 'sha256', $action . $customer ), $policy->limits( array(), $action, $identity ), 60 ) );
			}
		}
		$a = new Identity( hash( 'sha256', 'browser-0' ), '' );
		$b = new Identity( hash( 'sha256', 'browser-1' ), '' );
		$this->assertSame( $policy->limits( array(), 'contact', $a )[0]->key( time() ), $policy->limits( array(), 'genie_inquiry', $a )[0]->key( time() ) );
		$this->assertNotSame( $policy->limits( array(), 'contact', $a )[0]->key( time() ), $policy->limits( array(), 'contact', $b )[0]->key( time() ) );
		$this->assertSame( array(), $policy->limits( array(), 'draft_write', $a ), 'Adding products does not spend the business-message budget.' );
	}

	/** Login imports real anonymous spend and logout cannot provide a new daily budget. */
	public function test_login_carry_and_browser_continuity_preserve_business_spend(): void {
		$now     = 1600000000;
		$ledger  = new Ledger(
			static function () use ( &$now ): int {
				return $now;
			}
		);
		$policy  = new BusinessPolicy();
		$guest   = new Identity( hash( 'sha256', 'same-browser' ), '' );
		$account = new Identity( $guest->browser, Identity::account( 12345 ) );
		$fp      = hash( 'sha256', 'synthetic-business' );
		for ( $hour = 0; $hour < 2; ++$hour ) {
			for ( $i = 0; $i < 10; ++$i ) {
				$id = wp_generate_uuid4();
				$this->assertIsArray( $ledger->reserve( $id, $fp, $policy->limits( array(), 'inquiry', $guest ), 60 ) );
				$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
				$this->assertIsArray( $ledger->complete( $id, $fp ) );
			}
			$now += HOUR_IN_SECONDS;
		}
		$admitted = $ledger->reserve( wp_generate_uuid4(), $fp, $policy->limits( array(), 'inquiry', $account ), 60, $policy->carry( array(), 'inquiry', $account ) );
		$this->assertIsArray( $admitted );
		$remaining = array_column( $admitted['allowances'], 'remaining', 'dimension' );
		$this->assertSame( 79, $remaining['business_account_day'] );
		$this->assertSame( 79, $remaining['business_browser_day'] );
		$logout = $ledger->reserve( wp_generate_uuid4(), $fp, $policy->limits( array(), 'contact', $guest ), 60 );
		$this->assertInstanceOf( WP_Error::class, $logout );
		$this->assertSame( 'linker_admission_quota', $logout->get_error_code() );
	}
}

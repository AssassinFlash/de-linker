<?php
/**
 * Trusted privacy owners and pre-parse proof checks on the real journal.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Admission;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Observation;
use Linker\Commerce\Protection\Proof;
use WP_Error;

/**
 * No external provider/business work belongs in these fixtures.
 *
 * @coversNothing
 */
final class PublicAdmissionOwnersTest extends IntegrationTestCase {
	/** Isolate the local journal and browser credential. */
	protected function setUp(): void {
		parent::setUp();
		$old     = get_option( Ledger::OPTION );
		$cookies = $_COOKIE;
		delete_option( Ledger::OPTION );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$this->later(
			static function () use ( $old, $cookies ): void {
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				$_COOKIE = $cookies;
			}
		);
	}

	/** A signed proof alone cannot authorize parsing after its real parent is erased. */
	public function test_preparse_parent_and_dispatch_share_native_revocation(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$ledger = new Ledger();
		$owner  = Allowance::owner_for( Identity::recipient( 'synthetic@example.test' ) );
		$parent = wp_generate_uuid4();
		$fp     = hash( 'sha256', 'synthetic verification' );
		$this->assertIsArray( $ledger->reserve( $parent, $fp, array( new Allowance( 'fixture_verification', 'site', 10, DAY_IN_SECONDS ) ), 90, array(), 'verification_genie', $identity->binding(), array( $owner ) ) );
		$this->assertIsArray( $ledger->dispatch( $parent, $fp ) );
		$this->assertIsArray( $ledger->complete( $parent, $fp, 1 ) );
		$admission = new Admission( new Configuration( 'enforce', '1x00000000000000000000AA', '1x0000000000000000000000000000000AA', 'fixture.test' ), $ledger );
		$permit    = $admission->reserve( 'genie', ( new Proof() )->issue( 'verified', 'genie', $identity, $parent ), wp_generate_uuid4(), array( 'message' => 'synthetic' ), array( new Allowance( 'fixture_turn', $identity->browser, 10, DAY_IN_SECONDS ) ), 90 );
		$this->assertIsArray( $permit );
		$this->assertIsArray( $admission->validate( $permit ) );
		$this->assertIsArray( $ledger->privacy( array( $owner ), true ) );
		$this->assertInstanceOf( WP_Error::class, $admission->validate( $permit ) );
		$this->assertInstanceOf( WP_Error::class, $admission->dispatch( $permit ) );
	}

	/** Validated guest-email ownership is retained in observe mode. */
	public function test_additional_owners_are_associated_without_new_quota(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$owner  = Allowance::owner_for( Identity::recipient( 'synthetic@example.test' ) );
		$ledger = new Ledger();
		$permit = Observation::reserve( $ledger, 'inquiry', wp_generate_uuid4(), array( 'message' => 'synthetic' ), array( new Allowance( 'fixture_inquiry', $identity->browser, 10, DAY_IN_SECONDS ) ), 90, array(), array( $owner ) );
		$this->assertArrayHasKey( 'shadow', $permit );
		$private = $ledger->privacy( array( $owner ), false );
		$this->assertIsArray( $private );
		$this->assertCount( 1, $private['data'] );
		$this->assertSame( 'observe_inquiry', $private['data'][0]['purpose'] );
		$this->assertIsArray( $ledger->privacy( array( $owner ), true ) );
		$late = Observation::advance( $ledger, $permit, 'complete', 123 );
		$this->assertSame( 'linker_admission_unknown_receipt', $late['advisory']['reason'] );
	}
	/** Enforced permits also carry the validated email independently of browser owners. */
	public function test_enforced_owner_is_exportable_and_erasable(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$ledger = new Ledger();
		$parent = wp_generate_uuid4();
		$fp     = hash( 'sha256', 'synthetic enforce verification' );
		$ledger->reserve( $parent, $fp, array( new Allowance( 'fixture_verification', 'site', 10, DAY_IN_SECONDS ) ), 90, array(), 'verification_inquiry', $identity->binding() );
		$ledger->dispatch( $parent, $fp );
		$ledger->complete( $parent, $fp, 1 );
		$owner     = Allowance::owner_for( Identity::recipient( 'synthetic@example.test' ) );
		$admission = new Admission( new Configuration( 'enforce', '1x00000000000000000000AA', '1x0000000000000000000000000000000AA', 'fixture.test' ), $ledger );
		$permit    = $admission->reserve( 'inquiry', ( new Proof() )->issue( 'verified', 'inquiry', $identity, $parent ), wp_generate_uuid4(), array( 'message' => 'synthetic' ), array( new Allowance( 'fixture_inquiry', $identity->browser, 10, DAY_IN_SECONDS ) ), 90, true, array(), array( $owner ) );
		$this->assertIsArray( $permit );
		$private = $ledger->privacy( array( $owner ), false );
		$this->assertIsArray( $private );
		$this->assertCount( 1, $private['data'] );
		$this->assertSame( 'inquiry', $private['data'][0]['purpose'] );
		$this->assertIsArray( $ledger->privacy( array( $owner ), true ) );
		$this->assertInstanceOf( WP_Error::class, $admission->validate( $permit ) );
		$this->assertInstanceOf( WP_Error::class, $admission->dispatch( $permit ) );
	}
}

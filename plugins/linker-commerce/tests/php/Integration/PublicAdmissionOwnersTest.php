<?php
/**
 * Privacy ownership for native Woo retry records.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
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

	/** Erasure removes disclosure and prevents pending work from dispatching. */
	public function test_native_receipt_respects_the_registered_privacy_owner(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$ledger = new Ledger();
		$owner  = Allowance::owner_for( Identity::recipient( 'synthetic@example.test' ) );
		$id     = wp_generate_uuid4();
		$input  = hash( 'sha256', 'synthetic inquiry' );

		$receipt = $ledger->reserve( $id, $input, array( new Allowance( 'fixture_inquiry', $identity->browser, 1, HOUR_IN_SECONDS ) ), 90, array(), 'inquiry', $identity->binding(), array( $owner ) );
		$this->assertIsArray( $receipt );
		$private = $ledger->privacy( array( $owner ), false );
		$this->assertIsArray( $private );
		$this->assertCount( 1, $private['data'] );
		$this->assertSame( 'inquiry', $private['data'][0]['purpose'] );

		$this->assertIsArray( $ledger->privacy( array( $owner ), true ) );
		$this->assertInstanceOf( WP_Error::class, $ledger->dispatch( $id, $input ) );
	}
}

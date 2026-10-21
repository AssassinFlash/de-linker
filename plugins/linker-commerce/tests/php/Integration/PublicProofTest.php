<?php
/**
 * Real WordPress subjects and scope-bound short-lived proofs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Proof;

/**
 * A proof is never authorization to native Woo/account records.
 *
 * @coversNothing
 */
final class PublicProofTest extends IntegrationTestCase {
	/** Retain the runner's cookie; the fixture never needs to send a header. */
	protected function setUp(): void {
		parent::setUp();
		$old                         = $_COOKIE[ Identity::COOKIE ] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact runner value retained for restoration.
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$this->later(
			static function () use ( $old ): void {
				if ( null === $old ) {
					unset( $_COOKIE[ Identity::COOKIE ] );
				} else {
					$_COOKIE[ Identity::COOKIE ] = $old;
				}
			}
		);
	}

	/** A prepare stamp, different scope/subject, modified proof or expiry is refused. */
	public function test_proof_binding_expiry_and_kind_separation(): void {
		$this->as_user( 0 );
		$subject = Identity::current();
		$this->assertInstanceOf( Identity::class, $subject );
		$now     = 1600000000;
		$proofs  = new Proof(
			static function () use ( &$now ): int {
				return $now;
			}
		);
		$id      = wp_generate_uuid4();
		$prepare = $proofs->issue( 'prepare', 'inquiry', $subject, $id );
		$this->assertNull( $proofs->read( $prepare, 'verified', 'inquiry', $subject ) );
		$valid = $proofs->issue( 'verified', 'inquiry', $subject, $id );
		$read  = $proofs->read( $valid, 'verified', 'inquiry', $subject );
		$this->assertIsArray( $read );
		$this->assertSame( $id, $read['id'] );
		$this->assertNull( $proofs->read( $valid, 'verified', 'registration', $subject ) );
		$other = new Identity( hash( 'sha256', 'different browser' ), '' );
		$this->assertNull( $proofs->read( $valid, 'verified', 'inquiry', $other ) );
		$changed = substr( $valid, 0, -1 ) . ( 'a' === substr( $valid, -1 ) ? 'b' : 'a' );
		$this->assertNull( $proofs->read( $changed, 'verified', 'inquiry', $subject ) );
		$now += Proof::LIFETIME;
		$this->assertNull( $proofs->read( $valid, 'verified', 'inquiry', $subject ) );
		$this->assertStringNotContainsString( str_repeat( 'a', 32 ), (string) wp_json_encode( $subject ) );
	}

	/** The browser count remains linkable through native login, without raw IDs. */
	public function test_native_login_changes_the_proof_subject_but_keeps_the_browser_bucket(): void {
		$this->as_user( 0 );
		$guest = Identity::current();
		$this->assertInstanceOf( Identity::class, $guest );
		$proofs = new Proof();
		$token  = $proofs->issue( 'verified', 'genie', $guest, wp_generate_uuid4() );
		$this->as_user( 1 );
		$signed = Identity::current();
		$this->assertInstanceOf( Identity::class, $signed );
		$this->assertSame( $guest->browser, $signed->browser );
		$this->assertNotSame( $guest->binding(), $signed->binding() );
		$this->assertSame( '', $guest->account );
		$this->assertSame( 64, strlen( $signed->account ) );
		$this->assertNull( $proofs->read( $token, 'verified', 'genie', $signed ) );
	}
}

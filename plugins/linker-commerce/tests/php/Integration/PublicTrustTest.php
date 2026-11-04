<?php
/**
 * Real admission of a trusted genie session.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Admission;
use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Proof;
use Linker\Commerce\Protection\Trust;
use WP_Error;

/**
 * One solved challenge admits the genie turns of that identity for the
 * window; nothing else changes: new identities and business actions keep
 * their proofs.
 *
 * @coversNothing
 */
final class PublicTrustTest extends IntegrationTestCase {

	/**
	 * Official public always-pass dummy keys, as the local fixture configuration.
	 */
	private const SITE_KEY = '1x00000000000000000000AA';
	private const SECRET   = '1x0000000000000000000000000000000AA';

	/**
	 * Sets the runner to a guest with one fixed synthetic browser cookie.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$old                         = $_COOKIE[ Identity::COOKIE ] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact runner value retained for restoration.
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact synthetic fixture value, never a live credential.
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

	/**
	 * Removes this identity's trust rows after each test.
	 */
	protected function tearDown(): void {
		$identity = Identity::current();
		if ( $identity instanceof Identity ) {
			( new Trust() )->revoke( 'genie', $identity );
		}
		parent::tearDown();
	}

	/**
	 * One reserve on the admission under test, with a proof or without one.
	 *
	 * @param string $proof Verified proof, '' for a proofless attempt.
	 * @return array<string,mixed>|WP_Error The permit or the refusal.
	 */
	private function reserve( string $proof = '' ): array|WP_Error {
		return $this->admission()->reserve(
			'genie',
			$proof,
			wp_generate_uuid4(),
			array(
				'messages' => array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
				),
			),
			array(),
			90
		);
	}

	/**
	 * A fresh identity must pass the challenge; one solved challenge admits
	 * its further turns without a proof until the window ends.
	 */
	public function test_one_solved_challenge_admits_the_sessions_genie_turns(): void {
		$refusal = $this->refused();
		$this->assertSame( 'linker_admission_proof', $refusal->get_error_code() );

		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$proof = ( new Proof() )->issue( 'verified', 'genie', $identity, wp_generate_uuid4() );

		$verified = $this->reserve( $proof );
		if ( $verified instanceof WP_Error ) {
			$this->fail( $verified->get_error_message() );
		}
		$this->assertTrue( ( new Trust() )->admitted( 'genie', $identity ) );
		$this->admission()->cancel( $verified );

		$trusted = $this->reserve();
		if ( $trusted instanceof WP_Error ) {
			$this->fail( 'A trusted genie session sends its turn without a fresh proof: ' . $trusted->get_error_message() );
		}
		$this->assertSame( array(), $trusted['proof'], 'A trusted turn carries no proof to consume.' );
		$this->admission()->cancel( $trusted );
	}

	/**
	 * The window ends and the challenge returns; revocation ends it at once.
	 */
	public function test_expired_trust_re_challenges_and_revocation_ends_it_at_once(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		( new Trust() )->grant( 'genie', $identity );

		$later   = time() + Trust::WINDOW + 1;
		$expired = new Trust(
			static function () use ( $later ): int {
				return $later;
			}
		);
		$this->assertFalse( $expired->admitted( 'genie', $identity ), 'Past the window the challenge returns.' );

		( new Trust() )->revoke( 'genie', $identity );
		$this->assertSame(
			'linker_admission_proof',
			$this->refused()->get_error_code()
		);
	}

	/**
	 * A different identity is not trusted by this session's challenge.
	 */
	public function test_a_new_identity_is_still_challenged(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		( new Trust() )->grant( 'genie', $identity );

		$old = $_COOKIE[ Identity::COOKIE ]; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact synthetic fixture value retained for restoration.
		$this->later(
			static function () use ( $old ): void {
				$_COOKIE[ Identity::COOKIE ] = $old;
			}
		);
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'b', 32 ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact synthetic fixture value, never a live credential.

		$other = Identity::current();
		$this->assertInstanceOf( Identity::class, $other );
		$this->assertFalse( ( new Trust() )->admitted( 'genie', $other ), 'Trust never crosses identities.' );

		$this->assertSame(
			'linker_admission_proof',
			$this->refused()->get_error_code()
		);
	}

	/**
	 * Business actions keep their single-use proofs: genie trust never
	 * admits one, and a used business proof fails later, on the ledger.
	 */
	public function test_business_actions_keep_their_single_use_proofs(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		( new Trust() )->grant( 'genie', $identity );

		$payload   = array( 'message' => 'Please contact me.' );
		$admission = $this->admission();
		$refused   = $admission->reserve( 'genie_contact', '', wp_generate_uuid4(), $payload, array(), 90, true );
		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 'linker_admission_proof', $refused->get_error_code(), 'Genie trust never admits a business action.' );

		$proof  = ( new Proof() )->issue( 'verified', 'genie_contact', $identity, wp_generate_uuid4() );
		$first  = $admission->reserve( 'genie_contact', $proof, wp_generate_uuid4(), $payload, array(), 90, true );
		$second = $admission->reserve( 'genie_contact', $proof, wp_generate_uuid4(), $payload, array(), 90, true );
		$this->assertNotInstanceOf( WP_Error::class, $first, $first instanceof WP_Error ? $first->get_error_message() : '' );
		$this->assertInstanceOf( WP_Error::class, $second );
		$this->assertNotSame( 'linker_admission_proof', $second->get_error_code(), 'The used proof fails later, on the ledger, not as absent.' );
		$admission->cancel( $first );
	}

	/**
	 * One enforce-mode admission on the fixture configuration.
	 */
	private function admission(): Admission {
		return new Admission( new Configuration( 'enforce', self::SITE_KEY, self::SECRET, 'example.test' ) );
	}

	/**
	 * A proofless genie reserve, asserted to be the admission refusal.
	 */
	private function refused(): WP_Error {
		$result = $this->reserve();
		$this->assertInstanceOf( WP_Error::class, $result );
		return $result;
	}
}

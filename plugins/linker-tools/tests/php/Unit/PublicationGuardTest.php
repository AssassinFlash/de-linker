<?php
/**
 * Revocation is a changed source; inability to read source is an outage.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\PublicationGuard;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

/**
 * Source runtime errors remain visible as unavailable current authority.
 *
 * @covers \Linker\Tools\Genie\PublicationGuard
 */
final class PublicationGuardTest extends TestCase {
	/** Test wording remains the plugin's actual translated source. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__', array( 'return_arg' => 0 ) );
	}

	/** Cache/runtime failure before the call is a 503, never a hidden 500. */
	public function test_unreadable_manifest_is_a_typed_outage(): void {
		$guard = new PublicationGuard(
			static function (): array {
				throw new \RuntimeException( 'fixture authority unreadable' );
			}
		);
		$error = $guard->dependencies();
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 503, $error->get_error_data()['status'] );
		$this->assertSame( 'linker_genie_publication_unavailable', $error->get_error_code() );
	}

	/** An authoritative rejection is different from loss of the validation source. */
	public function test_revoked_dependencies_are_409_and_validation_outage_is_503(): void {
		$changed = ( new PublicationGuard( check: static fn(): array => array( 'valid' => false ) ) )->validate( array() );
		$this->assertInstanceOf( WP_Error::class, $changed );
		$this->assertSame( 409, $changed->get_error_data()['status'] );
		$this->assertSame( 'linker_genie_publication_changed', $changed->get_error_code() );
		$unavailable = ( new PublicationGuard(
			check: static function (): array {
				throw new \RuntimeException( 'fixture validation unreadable' );
			}
		) )->validate( array() );
		$this->assertInstanceOf( WP_Error::class, $unavailable );
		$this->assertSame( 503, $unavailable->get_error_data()['status'] );
		$this->assertSame( 'linker_genie_publication_unavailable', $unavailable->get_error_code() );
	}
}

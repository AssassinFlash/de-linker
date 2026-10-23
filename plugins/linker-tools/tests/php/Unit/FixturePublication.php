<?php
/**
 * Fixed permission of the HTTP proxy transport tests.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\PublicationGuard;
use WP_Error;
use WP_REST_Response;

/** The source permission tests run separately from the HTTP/thread fixtures. */
final class FixturePublication extends PublicationGuard {
	/**
	 * Read fixed current permission for the transport fixture.
	 *
	 * @return array<string,mixed>
	 */
	public function dependencies(): array|WP_Error {
		return array(
			'products'  => array(),
			'documents' => array(),
		);
	}

	/**
	 * Fixture source stays current throughout these transport tests.
	 *
	 * @param array<string,mixed> $dependencies Source proof.
	 */
	public function validate( array $dependencies ): true|WP_Error {
		unset( $dependencies );
		return true;
	}

	/**
	 * Transport tests have no receipt storage.
	 *
	 * @param WP_REST_Response    $reply Response.
	 * @param array<string,mixed> $dependencies Source proof.
	 */
	public function remember( WP_REST_Response $reply, array $dependencies ): void {
		unset( $reply, $dependencies );
	}
}

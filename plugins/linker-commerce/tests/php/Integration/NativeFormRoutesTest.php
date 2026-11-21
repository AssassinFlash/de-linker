<?php
/**
 * Public form verification takes place at the native submission handler.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

/**
 * Checks WordPress route registration for the native submission forms.
 *
 * @coversNothing
 */
final class NativeFormRoutesTest extends IntegrationTestCase {
	/** Customers do not have to start or redeem a separate REST proof. */
	public function test_native_forms_do_not_publish_an_intermediate_verification_route(): void {
		$routes = rest_get_server()->get_routes();
		$this->assertArrayNotHasKey( '/linker/v1/protection/prepare', $routes );
		$this->assertArrayNotHasKey( '/linker/v1/protection/verify', $routes );
	}
}

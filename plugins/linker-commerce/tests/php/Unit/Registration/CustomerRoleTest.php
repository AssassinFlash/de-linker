<?php
/**
 * Tests for business types.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for CustomerRole.
 *
 * @covers \Linker\Commerce\Registration\CustomerRole
 */
final class CustomerRoleTest extends TestCase {

	/**
	 * Installer, EPC contractor and distributor (AGENTS.md §1: the site's customers); unknown keys have no name.
	 */
	public function test_options(): void {
		WP_Mock::passthruFunction( '__' );

		$this->assertSame(
			array(
				'installer'   => 'Installer',
				'epc'         => 'EPC contractor',
				'distributor' => 'Distributor',
			),
			CustomerRole::options()
		);
		$this->assertSame( 'EPC contractor', CustomerRole::label( 'epc' ) );
		$this->assertSame( '', CustomerRole::label( 'wholesaler' ) );
	}
}

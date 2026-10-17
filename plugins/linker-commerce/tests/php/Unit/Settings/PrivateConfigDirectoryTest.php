<?php
/**
 * HOME-based config resolution used in web and CLI requests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Settings\PrivateConfigDirectory;
use Linker\Commerce\Tests\TestCase;

/**
 * Resolves fake paths only; never opens credential files.
 *
 * @covers \Linker\Commerce\Settings\PrivateConfigDirectory
 */
final class PrivateConfigDirectoryTest extends TestCase {

	/**
	 * One directory rule serves both SAPIs, and an absent HOME fails closed.
	 */
	public function test_resolves_the_private_home_directory(): void {
		$this->assertSame( '/home/example/.config/terravolt-builder/sunriver-smtp.env', PrivateConfigDirectory::path( 'sunriver-smtp.env', '/home/example' ) );
		$this->assertSame( '', PrivateConfigDirectory::path( 'sunriver-smtp.env', '' ) );
	}
}

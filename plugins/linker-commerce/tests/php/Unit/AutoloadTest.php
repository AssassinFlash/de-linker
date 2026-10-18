<?php
/**
 * The plugin's own classes load without Composer's classmap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit;

use Linker\Commerce\Autoload;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for the namespace fallback loader.
 *
 * @covers \Linker\Commerce\Autoload
 */
final class AutoloadTest extends TestCase {

	/**
	 * A class of this plugin resolves from its namespace even when the classmap
	 * is the one a deploy-window request sees.
	 */
	public function test_the_plugins_classes_load_by_namespace(): void {
		$this->assertTrue( Autoload::load( \Linker\Commerce\Registration\Approval::class ) );
	}

	/**
	 * A name this plugin does not own, or one without a file, is left to the
	 * rest of the chain.
	 */
	public function test_foreign_and_missing_names_are_not_ours(): void {
		$this->assertFalse( Autoload::load( 'Other\\Thing' ) );
		$this->assertFalse( Autoload::load( 'Linker\\Commerce\\Not\\A\\Class' ) );
	}
}

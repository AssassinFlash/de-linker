<?php
/**
 * Tests for the WindPress scan provider.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\WindPress;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for WindPress.
 *
 * @covers \Linker\Commerce\Presentation\WindPress
 */
final class WindPressTest extends TestCase {

	/**
	 * The plugin registers on the official compile.providers filter.
	 */
	public function test_register_adds_the_provider(): void {
		$windpress = new WindPress();
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );

		$windpress->register();

		$this->assertConditionsMet();
	}

	/**
	 * The provider is enabled and points at this plugin's scanner.
	 */
	public function test_providers_appends_linker_commerce(): void {
		$windpress = new WindPress();
		$providers = $windpress->providers( array() );

		$this->assertSame( 'linker-commerce', $providers[0]['id'] );
		$this->assertSame( array( $windpress, 'scan' ), $providers[0]['callback'] );
		$this->assertTrue( $providers[0]['enabled'] );
	}

	/**
	 * The scanner returns the LiveCanvas templates and the PHP that prints Tailwind classes.
	 */
	public function test_scan_includes_templates_and_php(): void {
		$contents = ( new WindPress() )->scan();
		$names    = array_column( $contents, 'name' );

		$this->assertContains( 'livecanvas/checkout_page.html', $names );
		$this->assertContains( 'livecanvas/single_product.html', $names );
		$this->assertNotSame( array(), $contents );
		foreach ( $contents as $file ) {
			$this->assertArrayHasKey( 'name', $file );
			$this->assertArrayHasKey( 'content', $file );
			$this->assertNotSame( '', $file['content'] );
		}
	}
}

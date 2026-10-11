<?php
/**
 * Tests for the WindPress scan provider.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\WindPress;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for WindPress: the provider registers on WindPress's compile filter,
 * scans the entries, and knows the ask chip's anchor classes (ticket #68).
 *
 * @covers \Linker\Tools\Genie\WindPress
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
	public function test_providers_appends_linker_tools(): void {
		$windpress = new WindPress();
		$providers = $windpress->providers( array() );

		$this->assertSame( 'linker-tools', $providers[0]['id'] );
		$this->assertSame( array( $windpress, 'scan' ), $providers[0]['callback'] );
		$this->assertTrue( $providers[0]['enabled'] );
	}

	/**
	 * The scanner returns the entries, the file that prints the ask chip's
	 * utility classes — content that really carries them.
	 */
	public function test_scan_returns_the_entries(): void {
		$contents = ( new WindPress() )->scan();

		$this->assertSame( array( 'includes/Genie/Entries.php' ), array_column( $contents, 'name' ) );
		$this->assertStringContainsString( 'min-h-11', $contents[0]['content'] );
		$this->assertStringContainsString( 'text-[#0c7f73]', $contents[0]['content'] );
	}

	/**
	 * The anchor check finds a class whose escaped selector is missing and
	 * passes a compiled cache that carries the chip's classes.
	 */
	public function test_anchor_classes(): void {
		$windpress = new WindPress();

		$this->assertSame(
			array( 'min-h-11', 'rounded-xl', 'border-neutral-200' ),
			$windpress->missing_anchor_classes( '/* nothing compiled */' )
		);
		$this->assertSame(
			array(),
			$windpress->missing_anchor_classes( '.min-h-11{min-height:2.75rem}.rounded-xl{border-radius:.75rem}.border-neutral-200{border-color:#e5e5e5}' )
		);
		// A longer class name is not the anchor class: .min-h-110 does not
		// satisfy .min-h-11 — and the real .min-h-11 next to it does.
		$this->assertContains( 'min-h-11', $windpress->missing_anchor_classes( '.min-h-110{min-height:27.5rem}' ) );
		$this->assertNotContains( 'min-h-11', $windpress->missing_anchor_classes( '.min-h-110{min-height:27.5rem}.min-h-11{min-height:2.75rem}' ) );
	}
}

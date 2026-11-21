<?php
/**
 * Tests for the bot guard of Genie's two public forms.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\FormGuard;
use WP_Mock\Tools\TestCase;

/**
 * The shared hidden field is rejected only when filled.
 *
 * @covers \Linker\Tools\Genie\FormGuard
 */
final class FormGuardTest extends TestCase {
	/** An empty or absent hidden field accepts an immediate request. */
	public function test_the_hidden_website_field(): void {
		$this->assertFalse( FormGuard::trapped( array() ) );
		$this->assertFalse( FormGuard::trapped( array( 'website' => '' ) ) );
		$this->assertTrue( FormGuard::trapped( array( 'website' => 'https://example.test' ) ) );
		$this->assertTrue( FormGuard::trapped( array( 'website' => array( 'test' ) ) ) );
	}
}

<?php
/**
 * Saved legacy content delegates to the current application.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Configurator\Mount;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Existing content uses the single current renderer.
 *
 * @covers \Linker\Tools\Configurator\Mount
 */
final class MountTest extends TestCase {

	/** The historical name remains registered. */
	public function test_register_hooks_the_shortcode(): void {
		$mount = new Mount();
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_configurator', array( $mount, 'shortcode' ) ),
			)
		);
		$mount->register();
		$this->assertConditionsMet();
	}

	/** One canonical renderer owns scripts, identity, translations and state. */
	public function test_saved_content_delegates_without_the_retired_bundle(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction(
			'do_shortcode',
			array(
				'times'  => 1,
				'args'   => array( '[linker_planner]' ),
				'return' => '<section data-linker-planner></section>',
			)
		);
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );
		$this->assertSame( '<section data-linker-planner></section>', ( new Mount() )->shortcode() );
		$this->assertConditionsMet();
	}

	/** Native admin previews do not open a customer session. */
	public function test_no_mount_in_the_admin(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => true ) );
		WP_Mock::userFunction( 'do_shortcode', array( 'times' => 0 ) );
		$this->assertSame( '', ( new Mount() )->shortcode() );
		$this->assertConditionsMet();
	}
}

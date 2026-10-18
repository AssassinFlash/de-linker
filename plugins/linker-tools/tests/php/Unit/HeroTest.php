<?php
/**
 * Tests for the home hero's entry (ticket #232): the page script loads on
 * the front page only.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Hero;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Hero.
 *
 * @covers \Linker\Tools\Genie\Hero
 */
final class HeroTest extends TestCase {

	/**
	 * The entry is enqueued on the front page only.
	 */
	public function test_assets_load_on_the_front_page(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => true ) );
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'times' => 1,
				'args'  => array( Hero::HANDLE ),
			)
		);
		// The hero reuses the dock's component styles (GenieCard, Reply,
		// AttachmentCard); enqueueing them here makes the dependency explicit.
		WP_Mock::userFunction(
			'wp_enqueue_style',
			array(
				'times' => 1,
				'args'  => array( Entries::HANDLE ),
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_style',
			array(
				'times' => 1,
				'args'  => array( Hero::HANDLE ),
			)
		);

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * Every other page — and the admin — loads nothing.
	 */
	public function test_other_pages_load_nothing(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * The admin loads nothing, even on the front page's request.
	 */
	public function test_admin_loads_nothing(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * Registration hangs the enqueue on `wp_enqueue_scripts`.
	 */
	public function test_register_hooks_the_assets(): void {
		$hero = new Hero();
		WP_Mock::expectActionAdded(
			'wp_enqueue_scripts',
			array( $hero, 'assets' )
		);

		$hero->register();

		$this->assertConditionsMet();
	}
}

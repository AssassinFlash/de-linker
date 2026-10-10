<?php
/**
 * Tests for the retired tool entry addresses.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Redirects;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Redirects.
 *
 * @covers \Linker\Tools\Redirects
 */
final class RedirectsTest extends TestCase {

	/**
	 * The site address of the test.
	 */
	private const HOME = 'https://de-linker.test';

	/**
	 * WordPress functions target() reads.
	 */
	private function wordpress(): void {
		WP_Mock::userFunction( 'home_url' )->andReturnUsing(
			static fn( string $path = '' ): string => self::HOME . $path
		);
	}

	/**
	 * Every retired design-canvas address goes to the configurator page of
	 * its own language, with the roof step (#12 item 2; /de/design-canvas/
	 * is the old plugin's English-slug-under-/de/ alias, /de/entwurfsflache/
	 * the German page slug).
	 */
	public function test_retired_canvas_addresses_go_to_the_configurators_roof_step(): void {
		$this->wordpress();
		$redirects = new Redirects();

		$this->assertSame( self::HOME . '/linker-planner/?step=roof', $redirects->target( '/design-canvas/' ) );
		$this->assertSame( self::HOME . '/de/linker-planer/?step=roof', $redirects->target( '/de/design-canvas/' ) );
		$this->assertSame( self::HOME . '/de/linker-planer/?step=roof', $redirects->target( '/de/entwurfsflache/' ) );
	}

	/**
	 * The configurator's own former address goes to the page itself (it was
	 * the configurator, not a step of it); German likewise.
	 */
	public function test_the_configurators_former_address_goes_to_the_page(): void {
		$this->wordpress();
		$redirects = new Redirects();

		$this->assertSame( self::HOME . '/linker-planner/', $redirects->target( '/quote-configurator/' ) );
		$this->assertSame( self::HOME . '/de/linker-planer/', $redirects->target( '/de/angebots-konfigurator/' ) );
	}

	/**
	 * Addresses that still exist stay: null means no redirect.
	 */
	public function test_live_addresses_stay(): void {
		$this->wordpress();
		$redirects = new Redirects();

		$this->assertNull( $redirects->target( '/linker-planner/' ) );
		$this->assertNull( $redirects->target( '/de/linker-planer/' ) );
		$this->assertNull( $redirects->target( '/design-canvas-exhibition/' ) );
		$this->assertNull( $redirects->target( '/' ) );
	}
}

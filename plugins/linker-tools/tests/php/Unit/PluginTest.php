<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Assets;
use Linker\Tools\Plugin;
use Linker\Tools\Redirects;
use Linker\Tools\SiteChrome;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\Tools\Plugin
 */
final class PluginTest extends TestCase {

	/**
	 * The plugin registers its scripts on init and its redirects on
	 * template_redirect.
	 */
	public function test_register_adds_the_hooks(): void {
		$assets    = new Assets( '/srv/www/wp-content/plugins/linker-tools/linker-tools.php' );
		$redirects = new Redirects();
		$chrome    = new SiteChrome( '/srv/www/wp-content/plugins/linker-tools/linker-tools.php' );

		WP_Mock::expectActionAdded( 'init', array( $assets, 'register' ) );
		WP_Mock::expectActionAdded( 'template_redirect', WP_Mock\Functions::type( 'Closure' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $chrome, 'assets' ) );

		( new Plugin( $assets, $redirects, $chrome ) )->register();

		$this->assertConditionsMet();
	}
}

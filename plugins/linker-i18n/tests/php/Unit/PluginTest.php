<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Plugin;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\I18n\Plugin
 */
final class PluginTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-i18n/linker-i18n.php';

	/**
	 * The plugin loads its text domain on init.
	 */
	public function test_register_adds_the_hooks(): void {
		$plugin = new Plugin( self::FILE );

		WP_Mock::expectActionAdded( 'init', array( $plugin, 'load_textdomain' ) );

		$plugin->register();

		$this->assertConditionsMet();
	}

	/**
	 * Translations load from the plugin's own languages/ directory.
	 */
	public function test_load_textdomain_uses_the_languages_directory(): void {
		WP_Mock::userFunction(
			'plugin_basename',
			array(
				'args'   => array( self::FILE ),
				'return' => 'linker-i18n/linker-i18n.php',
			)
		);
		WP_Mock::userFunction(
			'load_plugin_textdomain',
			array(
				'times' => 1,
				'args'  => array( 'linker-i18n', false, 'linker-i18n/languages' ),
			)
		);

		( new Plugin( self::FILE ) )->load_textdomain();

		$this->assertConditionsMet();
	}
}

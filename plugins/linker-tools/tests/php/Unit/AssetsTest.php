<?php
/**
 * Tests for the script and style registration.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Assets;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Assets, run against the committed build/ directory.
 *
 * @covers \Linker\Tools\Assets
 */
final class AssetsTest extends TestCase {

	private const PLUGIN_URL = 'https://de-linker.test/wp-content/plugins/linker-tools/';

	/**
	 * Each entry is registered from its asset file, with WordPress's React and
	 * JSX runtime as dependencies instead of bundled copies.
	 */
	public function test_registers_every_built_entry_from_its_asset_file(): void {
		$plugin_file = dirname( __DIR__, 3 ) . '/linker-tools.php';
		$plugin_dir  = dirname( $plugin_file ) . '/';

		WP_Mock::userFunction(
			'plugin_dir_path',
			array(
				'args'   => array( $plugin_file ),
				'return' => $plugin_dir,
			)
		);
		WP_Mock::userFunction(
			'plugin_dir_url',
			array(
				'args'   => array( $plugin_file ),
				'return' => self::PLUGIN_URL,
			)
		);

		foreach ( array( 'configurator', 'genie', 'shared' ) as $entry ) {
			$asset = require $plugin_dir . 'build/' . $entry . '.asset.php';

			$this->assertContains( 'react-jsx-runtime', $asset['dependencies'] );
			$this->assertContains( 'wp-element', $asset['dependencies'] );
			$this->assertContains( 'wp-i18n', $asset['dependencies'] );

			WP_Mock::userFunction(
				'wp_register_script',
				array(
					'times' => 1,
					'args'  => array(
						'linker-tools-' . $entry,
						self::PLUGIN_URL . 'build/' . $entry . '.js',
						$asset['dependencies'],
						$asset['version'],
						array( 'in_footer' => true ),
					),
				)
			);
			WP_Mock::userFunction(
				'wp_set_script_translations',
				array(
					'times' => 1,
					'args'  => array( 'linker-tools-' . $entry, 'linker-tools', $plugin_dir . 'languages' ),
				)
			);

			// Only an entry that imports CSS has build/<entry>.css.
			$styled = file_exists( $plugin_dir . 'build/' . $entry . '.css' );
			WP_Mock::userFunction(
				'wp_register_style',
				array(
					'times' => $styled ? 1 : 0,
					'args'  => array(
						'linker-tools-' . $entry,
						self::PLUGIN_URL . 'build/' . $entry . '.css',
						array(),
						$asset['version'],
					),
				)
			);
			WP_Mock::userFunction(
				'wp_style_add_data',
				array(
					'times' => $styled ? 1 : 0,
					'args'  => array( 'linker-tools-' . $entry, 'rtl', 'replace' ),
				)
			);
		}

		$this->assertFileExists( $plugin_dir . 'build/configurator.css' );

		( new Assets( $plugin_file ) )->register();

		$this->assertConditionsMet();
	}
}

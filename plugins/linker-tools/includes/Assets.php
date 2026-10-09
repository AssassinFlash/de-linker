<?php
/**
 * Script registration for the built apps.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * Registers each entry that `@wordpress/scripts` built into build/.
 *
 * An entry builds to build/<entry>.js plus build/<entry>.asset.php, which lists
 * the WordPress script handles it needs and a content hash used as the version.
 * Registering does not load anything: the code that prints an app's mount point
 * enqueues its handle, linker-tools-<entry>.
 */
final class Assets {

	/**
	 * Sets up the registrar.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Registers every built entry as a script with its translations.
	 */
	public function register(): void {
		$plugin_dir  = plugin_dir_path( $this->plugin_file );
		$asset_files = glob( $plugin_dir . 'build/*.asset.php' );
		if ( false === $asset_files ) {
			return;
		}

		foreach ( $asset_files as $asset_file ) {
			$entry  = basename( $asset_file, '.asset.php' );
			$handle = 'linker-tools-' . $entry;
			$asset  = require $asset_file;

			wp_register_script(
				$handle,
				plugin_dir_url( $this->plugin_file ) . 'build/' . $entry . '.js',
				$asset['dependencies'],
				$asset['version'],
				array( 'in_footer' => true )
			);
			wp_set_script_translations( $handle, 'linker-tools', $plugin_dir . 'languages' );
		}
	}
}

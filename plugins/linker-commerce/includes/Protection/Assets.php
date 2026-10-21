<?php
/**
 * Shared first-party client; third-party verification loads only on interaction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** No customer CSS or private validation key is emitted. */
final class Assets {
	public const HANDLE = 'linker-public-protection';

	/**
	 * Source file locates the one Commerce build.
	 *
	 * @param string        $file Main plugin file.
	 * @param Configuration $configuration Private current configuration.
	 */
	public function __construct( private readonly string $file, private readonly Configuration $configuration ) {}

	/** Native consumers enqueue this shared client on their own surfaces. */
	public function enqueue(): void {
		$path = plugin_dir_path( $this->file ) . 'build/protection.asset.php';
		if ( ! is_file( $path ) ) {
			return;
		}
		$asset = require $path;
		wp_enqueue_script( self::HANDLE, plugin_dir_url( $this->file ) . 'build/protection.js', $asset['dependencies'], $asset['version'], true );
		wp_set_script_translations( self::HANDLE, 'linker-commerce', plugin_dir_path( $this->file ) . 'languages' );
		wp_add_inline_script(
			self::HANDLE,
			'window.linkerPublicProtectionConfig=' . wp_json_encode(
				array(
					'api'      => rest_url( Controller::NAMESPACE . Controller::ROUTE ),
					'nonce'    => wp_create_nonce( 'wp_rest' ),
					'mode'     => $this->configuration->mode,
					'language' => str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en',
				),
				JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT
			) . ';',
			'before'
		);
	}
}

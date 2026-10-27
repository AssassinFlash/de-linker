<?php
/**
 * Compatibility shortcode for content saved before the unified workbench.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Configurator;

/** Both shortcode names use the same native application and coordinator. */
final class Mount {

	/** Retain existing saved content while the native template is updated. */
	public function register(): void {
		add_shortcode( 'linker_configurator', array( $this, 'shortcode' ) );
	}

	/**
	 * Delegate to the current application without loading the retired bundle.
	 *
	 * @param array<string,string>|string $atts Historical shortcode attributes.
	 */
	public function shortcode( $atts = array() ): string {
		unset( $atts );
		return is_admin() ? '' : do_shortcode( '[linker_planner]' );
	}
}

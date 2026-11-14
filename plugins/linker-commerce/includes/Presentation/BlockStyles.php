<?php
/**
 * Stops WordPress printing block-editor styles this site never uses.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * The presentation layer is LiveCanvas markup plus WindPress styles; the theme
 * is not a block theme, has no `theme.json` and does not support editor styles.
 * WordPress still prints its block-preset stylesheet on every page anyway.
 *
 * Measured on production 2026-11-14: `global-styles-inline-css` was 133,557 of
 * 401,054 bytes of HTML (33%) and defined 1,390 `--wp--preset--` variables plus
 * the block library rules. Nothing consumed them: no other stylesheet or inline
 * style referenced `--wp--preset--`, `style="..."` never used one, and the page
 * carried zero `wp-block-*` classes.
 *
 * This removes only that dead stylesheet. Site tokens, WindPress output,
 * LiveCanvas markup and every block that would need the styles are untouched;
 * a block theme or a theme that opts into editor styles keeps the default.
 */
final class BlockStyles {

	/** Register the guards. */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'drop_global_styles' ), 100 );
		add_filter( 'should_load_separate_core_block_assets', '__return_true' );
	}

	/**
	 * Dequeue the core block stylesheet when nothing on the site can use it.
	 *
	 * `wp_enqueue_global_styles` adds the handle; the cascade it prints is read
	 * by block themes and by themes that extend editor styles, so those two
	 * cases keep it.
	 */
	public function drop_global_styles(): void {
		if ( wp_is_block_theme() || current_theme_supports( 'editor-styles' ) ) {
			return;
		}
		wp_dequeue_style( 'global-styles' );
	}
}

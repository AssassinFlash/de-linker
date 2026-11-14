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
 * Core enqueues the handle twice, so dequeuing once is not enough:
 * `wp_enqueue_global_styles` runs on `wp_enqueue_scripts` and again on
 * `wp_footer` (priority 1), because a classic theme with on-demand block assets
 * prints a placeholder in the head and hoists the footer copy into it. The
 * guard therefore also runs on `wp_footer`, immediately after core's own call.
 *
 * A block theme or a theme that opts into editor styles reads these presets, so
 * both cases keep the default.
 */
final class BlockStyles {

	/** Core enqueues the handle on `wp_footer` at this priority. */
	private const CORE_FOOTER_PRIORITY = 1;

	/** Register the guards. */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'drop_global_styles' ), 100 );
		add_action( 'wp_footer', array( $this, 'drop_global_styles' ), self::CORE_FOOTER_PRIORITY + 1 );
		add_filter( 'should_load_separate_core_block_assets', '__return_true' );
	}

	/**
	 * Dequeue the core block stylesheet when nothing on the site can use it.
	 *
	 * The placeholder core prints in the head for classic themes is removed with
	 * it: once the real stylesheet is gone, `wp_hoist_late_printed_styles()` has
	 * nothing to inject and the placeholder would print an empty rule.
	 */
	public function drop_global_styles(): void {
		if ( wp_is_block_theme() || current_theme_supports( 'editor-styles' ) ) {
			return;
		}
		wp_dequeue_style( 'global-styles' );
		wp_deregister_style( 'global-styles' );
		wp_dequeue_style( 'wp-global-styles-placeholder' );
		wp_deregister_style( 'wp-global-styles-placeholder' );
	}
}

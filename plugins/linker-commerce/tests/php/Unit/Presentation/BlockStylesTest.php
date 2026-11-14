<?php
/**
 * Block-editor styles stay off pages that cannot use them.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\BlockStyles;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The dead-preset stylesheet is removed only where nothing can read it.
 *
 * @covers \Linker\Commerce\Presentation\BlockStyles
 */
final class BlockStylesTest extends TestCase {

	/** The site's own theme prints no blocks, so the cascade is removed. */
	public function test_a_classic_theme_drops_the_global_stylesheet(): void {
		WP_Mock::userFunction( 'wp_is_block_theme' )->andReturn( false );
		WP_Mock::userFunction( 'current_theme_supports' )
			->with( 'editor-styles' )
			->andReturn( false );
		WP_Mock::userFunction( 'wp_dequeue_style' )->with( 'global-styles' );
		WP_Mock::userFunction( 'wp_deregister_style' )->with( 'global-styles' );
		WP_Mock::userFunction( 'wp_dequeue_style' )->with( 'wp-global-styles-placeholder' );
		WP_Mock::userFunction( 'wp_deregister_style' )->with( 'wp-global-styles-placeholder' );

		( new BlockStyles() )->drop_global_styles();

		$this->assertConditionsMet();
	}

	/** A block theme reads the presets, so its cascade is left alone. */
	public function test_a_block_theme_keeps_the_global_stylesheet(): void {
		WP_Mock::userFunction( 'wp_is_block_theme' )->andReturn( true );
		WP_Mock::userFunction( 'current_theme_supports' )->never();
		WP_Mock::userFunction( 'wp_dequeue_style' )->never();
		WP_Mock::userFunction( 'wp_deregister_style' )->never();

		( new BlockStyles() )->drop_global_styles();

		$this->assertConditionsMet();
	}

	/** Editor-style support is the other documented reader of the presets. */
	public function test_editor_style_support_keeps_the_global_stylesheet(): void {
		WP_Mock::userFunction( 'wp_is_block_theme' )->andReturn( false );
		WP_Mock::userFunction( 'current_theme_supports' )
			->with( 'editor-styles' )
			->andReturn( true );
		WP_Mock::userFunction( 'wp_dequeue_style' )->never();
		WP_Mock::userFunction( 'wp_deregister_style' )->never();

		( new BlockStyles() )->drop_global_styles();

		$this->assertConditionsMet();
	}

	/**
	 * Core enqueues the handle again in the footer, so the guard must run there
	 * too; a head-only dequeue leaves the hoisted copy in place.
	 */
	public function test_the_guard_also_runs_after_cores_footer_enqueue(): void {
		$styles = new BlockStyles();
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $styles, 'drop_global_styles' ), 100 );
		WP_Mock::expectActionAdded( 'wp_footer', array( $styles, 'drop_global_styles' ), 2 );
		WP_Mock::expectFilterAdded( 'should_load_separate_core_block_assets', '__return_true' );

		$styles->register();

		$this->assertConditionsMet();
	}
}

<?php
/**
 * The real wp_footer translation pipeline of the planner module.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Planner\Application;
use PHPUnit\Framework\TestCase;

/**
 * Exercises the delivery mechanism itself, not a reconstructed tag: WordPress
 * prints the module translation data on wp_footer at priority 21 through
 * wp_print_inline_script_tag(), which has no tag-level filter, so the full
 * catalog loader must reach the page as a footer script of its own.
 */
final class PlannerTranslationCatalogTest extends TestCase {

	/** Restore the process locale for the remaining tests. */
	protected function tearDown(): void {
		restore_current_locale();
		parent::tearDown();
	}

	/** The shell subset prints inline and the catalog loader follows it. */
	public function test_wp_footer_prints_shell_subset_then_catalog_loader(): void {
		switch_to_locale( 'de_DE_formal' );
		wp_enqueue_script_module( Application::HANDLE );

		ob_start();
		/**
		 * Fires the footer exactly as a page render does; core's own action.
		 *
		 * @since 0.1.0
		 */
		do_action( 'wp_footer' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own action, fired as core fires it.
		$html = (string) ob_get_clean();

		$data_pos = strpos( $html, 'wp-script-module-translation-data-' . Application::HANDLE );
		$this->assertIsInt( $data_pos, 'the module translation data is printed on wp_footer' );
		$data_tag = substr( $html, $data_pos, 20000 );
		$this->assertStringContainsString( 'Neues Projekt', $data_tag, 'the inline subset carries the shell translations' );
		$this->assertStringNotContainsString( 'Projekt anlegen', $data_tag, 'the inline subset stays a subset; form strings arrive on demand' );

		$loader_pos = strpos( $html, 'linker-planner-translation-loader' );
		$this->assertIsInt( $loader_pos, 'the on-demand catalog loader is printed as its own script' );
		$this->assertGreaterThan( $data_pos, $loader_pos, 'the loader runs after the translation data has printed' );
		$loader = substr( $html, $loader_pos, 8000 );
		$this->assertStringContainsString( 'linkerToolsCatalog', $loader );
		$this->assertStringContainsString( 'languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json?ver=', $loader );

		// The URL the loader fetches must hold the form strings.
		$this->assertSame( 1, preg_match( '~languages/(linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721\.json)\?ver=([a-f0-9]{12})~', $loader, $matches ) );
		$catalog_name = $matches[1] ?? $this->fail( 'The loader names no versioned catalog file.' );
		$file         = dirname( __DIR__, 3 ) . '/languages/' . $catalog_name;
		$this->assertFileIsReadable( $file );
		$catalog = (string) file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- read-only catalog fixture of this checkout.
		$this->assertStringContainsString( 'Projekt anlegen', $catalog );
		$this->assertStringContainsString( 'Abbrechen', $catalog );
	}
}

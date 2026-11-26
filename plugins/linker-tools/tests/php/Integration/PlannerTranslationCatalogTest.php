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

/** The native page starts its catalog fetch in the head and installs it after wp-i18n is ready. */
final class PlannerTranslationCatalogTest extends TestCase {

	/** Restore the process locale for the remaining tests. */
	protected function tearDown(): void {
		restore_current_locale();
		parent::tearDown();
	}

	/** The shell subset prints inline and the catalog loader follows it. */
	public function test_head_delivers_the_native_locale_before_the_async_workspace_entry(): void {
		switch_to_locale( 'de_DE_formal' );
		$previous                = $GLOBALS['lc_main_html'] ?? null;
		$GLOBALS['lc_main_html'] = '[linker_planner]'; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- LiveCanvas supplies its template through this global.
		try {
			$app = new Application( dirname( __DIR__, 3 ) . '/linker-tools.php' );
			$app->assets();
			ob_start();
			$app->preload();
			$head = (string) ob_get_clean();
		} finally {
			$GLOBALS['lc_main_html'] = $previous; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- LiveCanvas supplies its template through this global.
		}
		$this->assertStringContainsString( 'rel="modulepreload"', $head );
		$this->assertStringContainsString( 'assets/planner.js?ver=', $head );
		$this->assertMatchesRegularExpression( '~<link rel="preload" as="fetch" href="[^"]+">~', $head );
		$this->assertStringContainsString( 'mode: "no-cors"', $head );
		$this->assertStringContainsString( 'linker-planner-catalog-request', $head );

		ob_start();
		$app->translations();
		$html = (string) ob_get_clean();

		$data_pos = strpos( $html, 'wp-script-module-translation-data-' . Application::HANDLE );
		$this->assertIsInt( $data_pos, 'the initial native translations print for this workspace' );
		$data_tag = substr( $html, $data_pos, 20000 );
		$this->assertStringContainsString( 'Neues Projekt', $data_tag, 'the inline subset carries the shell translations' );
		$this->assertStringNotContainsString( 'Projekt anlegen', $data_tag, 'the inline subset stays small; form strings come from the catalog' );

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
		$this->assertStringContainsString( $matches[0], $head );
		$this->assertFileIsReadable( $file );
		$catalog = (string) file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- read-only catalog fixture of this checkout.
		$this->assertStringContainsString( 'Projekt anlegen', $catalog );
		$this->assertStringContainsString( 'Abbrechen', $catalog );
	}
}

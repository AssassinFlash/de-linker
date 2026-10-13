<?php
/**
 * Tests for moving design tokens into Additional CSS.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\Tokens;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Tests for Tokens.
 *
 * @covers \Linker\Commerce\Presentation\Tokens
 */
final class TokensTest extends TestCase {

	/**
	 * The normalized sha256 of the exported tokens stylesheet: comments
	 * stripped, whitespace collapsed, lowercased. The string checks below
	 * only catch a renamed plugin path — the full-teardown audits (PR #64,
	 * #65) showed a whole-CSS byte copy can slip past them (404 lines did).
	 * The hash catches any wholesale change: when a change to tokens.css is
	 * INTENDED, recompute the hash (`php -r '\\'`-free one-liner in the test
	 * failure message) and re-pin it in the same diff, so the review sees a
	 * conscious token-layer change instead of a silent transplant.
	 */
	private const NORMALIZED_SHA256 = '3af62481d18d673982dbabb0ab81e629d2bef4496251349a7ced0b3a5c7c54b4';

	/**
	 * The exported stylesheet names the self-hosted fonts and the live accent,
	 * and its normalized content is exactly the pinned hash.
	 */
	public function test_css_uses_plugin_fonts_and_live_tokens(): void {
		$css = Tokens::css();

		$this->assertStringContainsString( '--proto-accent: #0c7f73', $css );
		$this->assertStringContainsString( '/wp-content/plugins/linker-commerce/assets/fonts/plus-jakarta-sans-400.ttf', $css );
		$this->assertStringNotContainsString( 'terravolt-b2b-core', $css );

		$stripped   = preg_replace( '/\/\*.*?\*\//s', '', $css ) ?? '';
		$normalized = strtolower( preg_replace( '/\s+/', ' ', $stripped ) ?? '' );
		$this->assertSame(
			self::NORMALIZED_SHA256,
			hash( 'sha256', trim( $normalized ) ),
			'tokens.css changed beyond its pinned normalized hash — if intended, re-pin NORMALIZED_SHA256 in this test within the same diff.'
		);
	}

	/**
	 * Every font the stylesheet serves resolves to its plugin file, and each
	 * file is really there: the presentation installer requires these files
	 * before it writes (a missing font is the same broken presentation for
	 * the visitor as an empty template).
	 */
	public function test_fonts_resolves_every_font_the_stylesheet_serves(): void {
		$fonts = Tokens::fonts();

		$this->assertSame(
			array(
				dirname( __DIR__, 4 ) . '/assets/fonts/plus-jakarta-sans-400.ttf',
				dirname( __DIR__, 4 ) . '/assets/fonts/plus-jakarta-sans-500.ttf',
				dirname( __DIR__, 4 ) . '/assets/fonts/plus-jakarta-sans-600.ttf',
				dirname( __DIR__, 4 ) . '/assets/fonts/plus-jakarta-sans-700.ttf',
				dirname( __DIR__, 4 ) . '/assets/fonts/dm-serif-display-400.ttf',
			),
			$fonts
		);
		foreach ( $fonts as $font ) {
			$this->assertFileExists( $font );
		}
	}

	/**
	 * The stylesheet path is the volume export, the file WindPressVolume
	 * publishes. There is no second tokens.css beside it.
	 */
	public function test_path_is_the_windpress_volume_export(): void {
		$this->assertSame( dirname( __DIR__, 4 ) . '/content/windpress/tokens.css', Tokens::path() );
		$this->assertFileExists( Tokens::path() );
		$this->assertFileDoesNotExist( dirname( __DIR__, 4 ) . '/content/tokens.css' );
	}

	/**
	 * Uninstall removes the marked Additional CSS block an earlier run
	 * left behind, and a second call finds nothing to remove. CSS outside
	 * the block stays.
	 */
	public function test_uninstall_removes_only_the_marked_block(): void {
		$before = "/* the site's own rule */\nh1{color:red}";
		$after  = "/* later site css */\np{margin:0}";
		$saved  = array( $before . "\n\n" . Tokens::MARKER . "\n:root{--stale:1}\n/* /linker-commerce-tokens */\n\n" . $after );
		WP_Mock::userFunction(
			'wp_get_custom_css',
			array(
				'return' => static function () use ( &$saved ): string {
					return $saved[0];
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_custom_css_post',
			array(
				'return' => static function ( string $css ) use ( &$saved ): int {
					$saved[0] = $css;
					return 1;
				},
			)
		);

		$tokens = new Tokens();
		$this->assertTrue( $tokens->uninstall() );
		$this->assertFalse( $tokens->uninstall() );

		$this->assertStringContainsString( $before, $saved[0] );
		$this->assertStringContainsString( $after, $saved[0] );
		$this->assertStringNotContainsString( Tokens::MARKER, $saved[0] );
		$this->assertStringNotContainsString( '--stale', $saved[0] );
	}

	/**
	 * Tokens inlined in a LiveCanvas header partial are removed so the page no longer depends on that partial's life cycle.
	 */
	public function test_detach_strips_the_inline_block(): void {
		$partial = new WP_Post(
			(object) array(
				'ID'           => 17,
				'post_type'    => 'lc_partial',
				'post_content' => '<header><style data-site-css="tokens.css">:root{--proto-accent:#0c7f73}</style><div id="tv-header-v2">nav</div></header>',
			)
		);
		$written = '';
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $partial ) ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$written ): int {
					$written = (string) $data['post_content'];
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );

		$this->assertSame( 1, ( new Tokens() )->detach_from_partials() );
		$this->assertStringNotContainsString( 'tokens.css', $written );
		$this->assertStringContainsString( 'tv-header-v2', $written );
	}
}

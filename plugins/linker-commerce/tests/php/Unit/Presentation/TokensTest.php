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
	 * The exported stylesheet names the self-hosted fonts and the live accent.
	 */
	public function test_css_uses_plugin_fonts_and_live_tokens(): void {
		$css = Tokens::css();

		$this->assertStringContainsString( '--proto-accent: #0c7f73', $css );
		$this->assertStringContainsString( '/wp-content/plugins/linker-commerce/assets/fonts/plus-jakarta-sans-400.ttf', $css );
		$this->assertStringNotContainsString( 'terravolt-b2b-core', $css );
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
	 * Additional CSS gains the tokens once, and a second install replaces the same marked block.
	 */
	public function test_install_is_idempotent(): void {
		$saved = array( '' );
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
		$tokens->install();
		$tokens->install();

		$this->assertSame( 1, substr_count( $saved[0], Tokens::MARKER ) );
		$this->assertStringContainsString( '--proto-accent: #0c7f73', $saved[0] );
	}

	/**
	 * CSS outside the managed block survives every install: a site's own
	 * Additional CSS keeps its place before and after the tokens block.
	 */
	public function test_install_preserves_css_outside_the_marked_block(): void {
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

		( new Tokens() )->install();

		$this->assertStringStartsWith( $before, $saved[0] );
		$this->assertStringEndsWith( $after, $saved[0] );
		$this->assertStringNotContainsString( '--stale', $saved[0] );
		$this->assertStringContainsString( '--proto-accent: #0c7f73', $saved[0] );
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

<?php
/**
 * Tests for the home hero's entry (ticket #232): the page script loads on
 * the front page only.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Hero;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Hero.
 *
 * @covers \Linker\Tools\Genie\Hero
 */
final class HeroTest extends TestCase {

	/**
	 * The entry is enqueued on the front page only.
	 */
	public function test_assets_load_on_the_front_page(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => '/assets/hero-loader.js' ) );
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'times' => 1,
				'args'  => array(
					'linker-tools-hero-loader',
					'/assets/hero-loader.js',
					array( 'linker-tools-genie-loader' ),
					substr( (string) md5_file( dirname( __DIR__, 3 ) . '/assets/hero-loader.js' ), 0, 12 ),
					array(
						'in_footer' => true,
						'strategy'  => 'defer',
					),
				),
			)
		);
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/** German hero configuration references its public catalog and styles. */
	public function test_config_links_the_german_hero_catalog(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'de_DE_formal' ) );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => static fn( string $path ): string => '/' . $path ) );
		WP_Mock::userFunction( 'wp_scripts', array( 'return' => new FakeScripts() ) );
		WP_Mock::userFunction( 'wp_styles', array( 'return' => new FakeScripts() ) );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WordPress encoder test double.
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( $config, int $flags ): string => (string) json_encode( $config, $flags ) ) );
		$payload = array();
		WP_Mock::userFunction(
			'wp_print_inline_script_tag',
			array(
				'return' => static function ( string $json, array $attrs ) use ( &$payload ): void {
					self::assertSame( 'application/json', $attrs['type'] );
					self::assertArrayHasKey( 'data-linker-hero-loader', $attrs );
					$payload = json_decode( $json, true );
				},
			)
		);
		( new Hero() )->config();
		$this->assertMatchesRegularExpression( '/6796211aef57736d0923df38ef696ad2\.json\?ver=[a-f0-9]{12}$/', $payload['translationUrls'][0] );
		$this->assertArrayNotHasKey( 'translations', $payload );
		$this->assertStringContainsString( '/hero.js?ver=', $payload['src'] );
	}

	/**
	 * Every other page — and the admin — loads nothing.
	 */
	public function test_other_pages_load_nothing(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * The admin loads nothing, even on the front page's request.
	 */
	public function test_admin_loads_nothing(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'times' => 0 ) );

		( new Hero() )->assets();

		$this->assertConditionsMet();
	}

	/**
	 * Registration hangs the enqueue on `wp_enqueue_scripts`.
	 */
	public function test_register_hooks_the_assets(): void {
		$hero = new Hero();
		WP_Mock::expectActionAdded(
			'wp_enqueue_scripts',
			array( $hero, 'assets' )
		);

		WP_Mock::expectActionAdded( 'wp_footer', array( $hero, 'config' ) );
		$hero->register();

		$this->assertConditionsMet();
	}
}

<?php
/**
 * Tests for the Solution Configurator's mount point.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Configurator\Mount;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Mount: the page's mount point carries what the app cannot know
 * server-side, and it loads the built entry.
 *
 * @covers \Linker\Tools\Configurator\Mount
 */
final class MountTest extends TestCase {


	/**
	 * The shortcode registers under the name the LiveCanvas template prints.
	 */
	public function test_register_hooks_the_shortcode(): void {
		$mount = new Mount();
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_configurator', array( $mount, 'shortcode' ) ),
			)
		);

		$mount->register();

		$this->assertConditionsMet();
	}

	/**
	 * The mount point: the app's name, the engine's address — this plugin's
	 * own engine route, so the browser never talks to the self-signed engine
	 * directly — the REST root and a REST nonce.
	 */
	public function test_the_shortcode_prints_the_mount_point_and_loads_the_app(): void {
		$enqueued = array();
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction(
			'rest_url',
			array(
				'return' => static fn( string $path = '' ): string => 'http://127.0.0.1:8975/wp-json/' . $path,
			)
		);
		WP_Mock::userFunction(
			'wp_create_nonce',
			array(
				'args'   => array( 'wp_rest' ),
				'return' => 'abc123',
			)
		);
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn( string $url ): string => $url ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'return' => static function ( string $handle ) use ( &$enqueued ): bool {
					$enqueued[] = 'script:' . $handle;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_style',
			array(
				'return' => static function ( string $handle ) use ( &$enqueued ): bool {
					$enqueued[] = 'style:' . $handle;
					return true;
				},
			)
		);

		$html = ( new Mount() )->shortcode();

		$this->assertSame(
			'<div data-linker-app="configurator" data-engine-url="http://127.0.0.1:8975/wp-json/linker-ai/v1/engine" data-rest-url="http://127.0.0.1:8975/wp-json/" data-rest-nonce="abc123"></div>',
			$html
		);
		$this->assertSame( array( 'script:' . Mount::HANDLE, 'style:' . Mount::HANDLE ), $enqueued );
		$this->assertConditionsMet();
	}

	/**
	 * The backend's own preview of the page prints no app.
	 */
	public function test_no_mount_in_the_admin(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_option', array( 'times' => 0 ) );

		$this->assertSame( '', ( new Mount() )->shortcode() );
	}

	/**
	 * Every word of the page is the app's: the markup is a mount point and a
	 * data attribute set, nothing a designer would have to lay out.
	 */
	public function test_the_markup_carries_no_copy_and_no_style(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction(
			'rest_url',
			array(
				'return' => static fn( string $path = '' ): string => 'https://de-linker.com/wp-json/' . $path,
			)
		);
		WP_Mock::userFunction( 'wp_create_nonce', array( 'return' => 'nonce' ) );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn( string $url ): string => $url ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'return' => true ) );

		$html = ( new Mount() )->shortcode();

		$this->assertStringNotContainsString( 'style=', $html );
		$this->assertStringNotContainsString( 'class=', $html );
		$this->assertStringNotContainsString( 'Configuration', $html );
		$this->assertStringContainsString( 'data-linker-app="configurator"', $html );
	}
}

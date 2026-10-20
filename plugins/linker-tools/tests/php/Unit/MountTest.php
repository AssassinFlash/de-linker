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
	 * Query keys this class sets, restored so other tests see a clean request.
	 *
	 * @var array<string, mixed>
	 */
	private array $query = array();

	/**
	 * A public page, with no size-hint keys left from another test.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->query = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- test request state.
		foreach ( array( 'pv_kwp', 'annual_kwh', 'phase', 'backup', 'plz' ) as $key ) {
			unset( $_GET[ $key ] ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- test request state.
		}
	}

	/**
	 * Restores the request.
	 */
	public function tearDown(): void {
		$_GET = $this->query;
		parent::tearDown();
	}


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

	/**
	 * A size-hint address is carried onto the mount. phase=3 and backup=none
	 * equal the form defaults, so they are not attributes. The numbers use
	 * SizeHint's `(string) (float)` spelling.
	 */
	public function test_a_size_hint_address_is_printed_on_the_mount(): void {
		$this->front_page();
		$_GET['pv_kwp']     = '10.0';
		$_GET['annual_kwh'] = '4500';
		$_GET['phase']      = '3';
		$_GET['backup']     = 'needed';
		$_GET['plz']        = '80538';

		$html = ( new Mount() )->shortcode();

		$this->assertStringContainsString( 'data-pv-kwp="10"', $html );
		$this->assertStringContainsString( 'data-annual-kwh="4500"', $html );
		$this->assertStringContainsString( 'data-backup="needed"', $html );
		$this->assertStringContainsString( 'data-plz="80538"', $html );
		$this->assertStringNotContainsString( 'data-phase=', $html );
		$this->assertStringNotContainsString( 'style=', $html );
	}

	/**
	 * Phase 1 and the accessory backup differ from the empty defaults, so they are carried.
	 */
	public function test_phase_and_backup_are_carried_only_when_they_differ_from_the_form_defaults(): void {
		$this->front_page();
		$_GET['phase']  = '1';
		$_GET['backup'] = 'needed_accessory_ok';

		$html = ( new Mount() )->shortcode();

		$this->assertStringContainsString( 'data-phase="1"', $html );
		$this->assertStringContainsString( 'data-backup="needed_accessory_ok"', $html );
	}

	/**
	 * A value SizeHint would not write is not a field, so the mount stays bare.
	 */
	public function test_invalid_size_hint_values_add_no_fields(): void {
		$this->front_page();
		$_GET['pv_kwp']     = '0';
		$_GET['annual_kwh'] = 'no';
		$_GET['phase']      = '2';
		$_GET['backup']     = 'none';
		$_GET['plz']        = '8053';
		$_GET['lang']       = 'de';

		$html = ( new Mount() )->shortcode();

		$this->assertStringNotContainsString( 'data-pv-kwp', $html );
		$this->assertStringNotContainsString( 'data-annual-kwh', $html );
		$this->assertStringNotContainsString( 'data-phase', $html );
		$this->assertStringNotContainsString( 'data-backup', $html );
		$this->assertStringNotContainsString( 'data-plz', $html );
		$this->assertStringNotContainsString( 'data-lang', $html );
		$this->assertSame(
			'<div data-linker-app="configurator" data-engine-url="http://127.0.0.1:8975/wp-json/linker-ai/v1/engine" data-rest-url="http://127.0.0.1:8975/wp-json/" data-rest-nonce="abc123"></div>',
			$html
		);
	}

	/**
	 * An array query value is not text SizeHint wrote.
	 */
	public function test_a_non_string_query_value_is_ignored(): void {
		$this->front_page();
		$_GET['pv_kwp'] = array( '10' );
		$_GET['plz']    = '10115';

		$html = ( new Mount() )->shortcode();

		$this->assertStringNotContainsString( 'data-pv-kwp', $html );
		$this->assertStringContainsString( 'data-plz="10115"', $html );
	}

	/**
	 * The stubs a front-end shortcode needs, including the query readers.
	 */
	private function front_page(): void {
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
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_enqueue_style', array( 'return' => true ) );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
	}
}

<?php
/**
 * Public native build metadata for the isolated workbench.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Application;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The public build-metadata boundary.
 *
 * @covers \Linker\Tools\Planner\Application
 */
final class PlannerApplicationTest extends TestCase {

	/**
	 * The native mount and entry use the same reviewed build.
	 *
	 * @throws \RuntimeException If the native configuration is absent.
	 */
	public function test_native_mount_exposes_the_current_reviewed_view_modules(): void {
		$root     = dirname( __DIR__, 3 ) . '/';
		$base     = 'https://fixture.invalid/wp-content/plugins/linker-tools/';
		$manifest = json_decode( (string) file_get_contents( $root . 'build/planner/vite-manifest.json' ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- actual read-only build fixture.
		$this->assertIsArray( $manifest );
		$entry = $manifest['src/main.tsx']['file'];
		$scene = $manifest['src/components/design/SceneViewport.tsx']['file'];
		$map   = $manifest['src/components/design/MapViewport.tsx']['file'];
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => $root ) );
		WP_Mock::userFunction( 'plugin_dir_url', array( 'return' => $base ) );
		WP_Mock::userFunction(
			'wp_register_script_module',
			array(
				'times' => 1,
				'args'  => array( Application::HANDLE, $base . 'build/planner/' . $entry, array(), hash_file( 'sha256', $root . 'build/planner/' . $entry ) ),
			)
		);
		WP_Mock::userFunction( 'wp_set_script_module_translations', array( 'times' => 1 ) );
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'args'  => array( 'wp-i18n' ),
				'times' => 1,
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_script_module',
			array(
				'args'  => array( Application::HANDLE ),
				'times' => 1,
			)
		);
		WP_Mock::userFunction(
			'WC',
			array(
				'return' => (object) array(
					'countries' => new class() {
						/**
						 * Native countries boundary.
						 *
						 * @return array<string,string>
						 */
						public function get_countries(): array {
							return array( 'FR' => 'France' );
						}
					},
				),
			)
		);
		WP_Mock::userFunction( 'rest_url', array( 'return' => 'https://fixture.invalid/wp-json/linker/v1/planner/' ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'https://fixture.invalid/wp-admin/admin-ajax.php' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => 'https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce' ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_GB' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( mixed $data ): string|false => json_encode( $data ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- implements the mocked encoder without recursion.
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( string $value ): string => htmlspecialchars( $value, ENT_QUOTES ) ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn( string $value ): string => $value ) );
		$app = new Application( $root . 'linker-tools.php' );
		$app->assets();
		$html = $app->mount();
		$this->assertSame( 1, preg_match( '/data-planner-config="([^"]+)"/', $html, $matches ) );
		$config = json_decode( html_entity_decode( $matches[1] ?? throw new \RuntimeException( 'Native planner configuration was not rendered.' ), ENT_QUOTES ), true );
		$this->assertSame( $base . 'build/planner/' . $scene, $config['scene_module_url'] );
		$this->assertSame( $base . 'build/planner/' . $map, $config['map_module_url'] );
		$this->assertSame( array( 'FR' => 'France' ), $config['countries'] );
		$this->assertStringNotContainsString( '<script', $html );
		$this->assertSame( '', $app->mount() );
		$this->assertConditionsMet();
	}
}

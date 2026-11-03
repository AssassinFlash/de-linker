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

	/**
	 * The 272 KB planner catalog is split into a compact inline shell subset
	 * plus a versioned on-demand catalog loader for the full dictionary.
	 */
	public function test_script_module_translations_inline_shell_subset_and_load_full_catalog_on_demand(): void {
		$root = dirname( __DIR__, 3 ) . '/';
		$base = 'https://fixture.invalid/wp-content/plugins/linker-tools/';
		$file = $root . 'languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json';
		$raw  = (string) file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local test fixture.
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => $root ) );
		WP_Mock::userFunction( 'plugin_dir_url', array( 'return' => $base ) );
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				'return' => static fn( mixed $data, int $flags = 0 ): string|false => json_encode( $data, $flags ), // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- mocked encoder.
			)
		);

		$app = new Application( $root . 'linker-tools.php' );
		$this->assertSame( $raw, $app->filter_translations( $raw, $file, 'other-handle', 'linker-tools' ) );

		$filtered = $app->filter_translations( $raw, $file, Application::HANDLE, 'linker-tools' );
		$this->assertIsString( $filtered );
		// The 42-message shell subset is ~4.9 KB (versus 272 KB for the full 2,028-entry catalog).
		$this->assertLessThan( 10000, strlen( $filtered ) );
		$decoded  = json_decode( $filtered, true );
		$messages = $decoded['locale_data']['messages'] ?? array();
		$this->assertSame( array( 'Ihr Arbeitsbereich wird geöffnet…' ), $messages['Opening your workspace…'] ?? null );
		$this->assertSame( array( 'Lösungskonfigurator' ), $messages['Solution Configurator'] ?? null );
		$this->assertSame( array( 'Ihre Projekte' ), $messages['Your projects'] ?? null );

		$inline_tag = '<script id="wp-script-module-translation-data-linker-planner">wp.i18n.setLocaleData({}, "linker-tools");</script>';
		$unchanged  = $app->inline_translation_loader( $inline_tag, '', array( 'id' => 'other-script' ) );
		$this->assertSame( $inline_tag, $unchanged );

		$augmented    = $app->inline_translation_loader(
			$inline_tag,
			'',
			array( 'id' => 'wp-script-module-translation-data-' . Application::HANDLE )
		);
		$expected_ver = substr( (string) hash_file( 'sha256', $file ), 0, 12 );
		$this->assertStringContainsString(
			$base . 'languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json?ver=' . $expected_ver,
			$augmented
		);
		$this->assertStringContainsString( 'window.wp.i18n.setLocaleData', $augmented );
	}
}

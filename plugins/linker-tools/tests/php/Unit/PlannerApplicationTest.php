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

	/** A restored homepage revision containing the old shortcode cannot enqueue the workspace. */
	public function test_retired_homepage_shortcode_outputs_nothing_and_enqueues_no_planner(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Presentation/PageUrls.php';
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_front_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => new \WP_Post( (object) array( 'ID' => 73 ) ) ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://fixture.invalid/solution-configurator/' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_enqueue_script_module', array( 'times' => 0 ) );
		$app = new Application( dirname( __DIR__, 3 ) . '/linker-tools.php' );
		$this->assertSame( '', $app->mount( array( 'mode' => 'home' ) ) );
		$this->assertConditionsMet();
	}

	/** The pre-PHP cache rule covers both public routes and the private-cookie families checked by the mount. */
	public function test_cache_rules_bypass_the_warm_page_for_private_requests(): void {
		$app = new Application( dirname( __DIR__, 3 ) . '/linker-tools.php' );
		$raw = $app->cache_rules( "RewriteEngine On\nRewriteRule . /index.php [L]" );
		$this->assertStringContainsString( 'RewriteCond %{QUERY_STRING} !^$ [OR]', $raw );
		$this->assertSame( 1, preg_match( '/^RewriteCond %\{HTTP_COOKIE\} (.+)$/m', $raw, $cookies ) );
		$this->assertSame( 1, preg_match( '/^RewriteRule (.+) - \[E=Cache-Control:no-cache\]$/m', $raw, $routes ) );
		foreach ( array( 'wp_woocommerce_session_site', 'woocommerce_items_in_cart', 'linker_planner_transition_id', 'wordpress_logged_in_site' ) as $name ) {
			$this->assertMatchesRegularExpression( '~' . $cookies[1] . '~', 'ordinary=value; ' . $name . '=value' );
		}
		$this->assertDoesNotMatchRegularExpression( '~' . $cookies[1] . '~', 'cookieyes-consent=analytics:yes' );
		$this->assertMatchesRegularExpression( '~' . $routes[1] . '~', 'solution-configurator/' );
		$this->assertMatchesRegularExpression( '~' . $routes[1] . '~', 'de/loesungskonfigurator/' );
		$this->assertDoesNotMatchRegularExpression( '~' . $routes[1] . '~', 'products/' );
	}

	/**
	 * Public and private requests to the same landing page.
	 *
	 * @return array<string,array{bool,array<string,string>,array<string,string>,bool}>
	 */
	public static function signed_in_visitor(): array {
		return array(
			'guest'          => array( false, array(), array(), false ),
			'consent'        => array( false, array(), array( 'cookieyes-consent' => 'consent' ), false ),
			'signed in'      => array( true, array(), array(), true ),
			'login cookie'   => array( false, array(), array( 'wordpress_logged_in_site' => '' ), true ),
			'Woo session'    => array( false, array(), array( 'wp_woocommerce_session_site' => 'session' ), true ),
			'Woo cart'       => array( false, array(), array( 'woocommerce_items_in_cart' => '1' ), true ),
			'planner ticket' => array( false, array(), array( 'linker_planner_transition_123' => 'ticket' ), true ),
			'project'        => array( false, array( 'project' => '' ), array(), true ),
			'PV input'       => array( false, array( 'pv_kwp' => '5' ), array(), true ),
			'other query'    => array( false, array( 'campaign' => 'spring' ), array(), true ),
		);
	}

	/**
	 * The native mount and entry use the same reviewed build.
	 *
	 * @param bool                 $signed_in Whether WordPress authenticated the visitor.
	 * @param array<string,string> $query Request query.
	 * @param array<string,string> $cookies Request cookies.
	 * @param bool                 $expect_private Expected private response.
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 * @throws \RuntimeException If the native configuration is absent.
	 * @dataProvider signed_in_visitor
	 */
	public function test_native_mount_exposes_the_current_reviewed_view_modules( bool $signed_in, array $query, array $cookies, bool $expect_private ): void {
		$_GET                   = $query;
		$_COOKIE                = $cookies;
		$_SERVER['REQUEST_URI'] = '/solution-configurator/';

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
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $signed_in ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'https://fixture.invalid/wp-admin/admin-ajax.php' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => 'https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce' ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_GB' ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'linker_google_maps_api_key', '' ),
				'return' => '',
			)
		);
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( mixed $data ): string|false => json_encode( $data ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- implements the mocked encoder without recursion.
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( string $value ): string => htmlspecialchars( $value, ENT_QUOTES ) ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn( string $value ): string => $value ) );
		$app = new Application( $root . 'linker-tools.php' );
		$app->assets();
		$html = $app->mount();
		$this->assertSame( $expect_private, defined( 'DONOTCACHEPAGE' ) && DONOTCACHEPAGE );
		$this->assertSame( 1, substr_count( $html, '<h1>Solution Configurator</h1>' ) );
		$this->assertSame( 1, preg_match( '/data-planner-config="([^"]+)"/', $html, $matches ) );
		$config = json_decode( html_entity_decode( $matches[1] ?? throw new \RuntimeException( 'Native planner configuration was not rendered.' ), ENT_QUOTES ), true );
		$this->assertSame( $base . 'build/planner/' . $scene, $config['scene_module_url'] );
		$this->assertSame( $base . 'build/planner/' . $map, $config['map_module_url'] );
		$this->assertNull( $config['google_maps_api_key'] );
		$this->assertSame( array( 'FR' => 'France' ), $config['countries'] );
		// A guest is never offered the nonce endpoint: it answers only a
		// signed-in cookie, so the browser would spend a round trip on a
		// request that can only return 400/0 (measured 2026-11-15: 700ms).
		if ( $signed_in ) {
			$this->assertSame( 'https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce', $config['nonce_url'] );
		} else {
			$this->assertArrayHasKey( 'nonce_url', $config );
			$this->assertNull( $config['nonce_url'] );
		}
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
		// The form strings are deliberately not in the inline subset: they
		// arrive through the on-demand catalog loader.
		$this->assertArrayNotHasKey( 'Create project', $messages );

		// Without a recorded catalog URL (translations never loaded for this
		// page) no loader is printed at all.
		$fresh = new Application( $root . 'linker-tools.php' );
		WP_Mock::userFunction(
			'wp_print_inline_script_tag',
			array(
				'times' => 0,
			)
		);
		$fresh->print_translation_loader();

		// With the catalog URL recorded by filter_translations(), the loader
		// is printed as its own inline script — core offers no tag-level
		// filter to append it to the translation data tag.
		$captured = null;
		WP_Mock::userFunction(
			'wp_print_inline_script_tag',
			array(
				'times'  => 1,
				'args'   => array( \WP_Mock\Functions::type( 'string' ), array( 'id' => 'linker-planner-translation-loader' ) ),
				'return' => static function ( string $javascript ) use ( &$captured ): string {
					$captured = $javascript;
					return '';
				},
			)
		);
		$app->print_translation_loader();
		$this->assertIsString( $captured );
		$expected_ver = substr( (string) hash_file( 'sha256', $file ), 0, 12 );
		$this->assertStringContainsString(
			$base . 'languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json?ver=' . $expected_ver,
			$captured
		);
		$this->assertStringContainsString( 'window.wp.i18n.setLocaleData', $captured );
		$this->assertStringContainsString( 'window.linkerToolsCatalog', $captured );
		$this->assertStringContainsString( 'new Promise', $captured );
		// The catalog settles on the request's own outcome: no timer may paint
		// an untranslated first frame on a slow network, and the shared fetch
		// must stay untouched for the rest of the page.
		$this->assertStringNotContainsString( 'setTimeout', $captured );
		$this->assertStringNotContainsString( 'window.fetch =', $captured );
		$this->assertStringContainsString( '.catch( () => {} ).finally( done )', $captured );
		$this->assertConditionsMet();
	}
}

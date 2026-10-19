<?php
/**
 * A save drops Genie's cached page through the real HTTP chain (#405).
 *
 * The chain is wp_update_post, wp_after_insert_post, get_permalink,
 * wp_remote_post, the service gate, PageReader.invalidate, and the next
 * read of that page. The read and the invalidation share one Genie process,
 * started here. PageCacheTest injects the HTTP call; this test does not.
 *
 * Case ids: services/genie/tests/fixtures/405/page-cache.json (#339).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\PageCache;
use Linker\Tools\Genie\Proxy;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- the test starts the Genie probe and copies a render mu-plugin.

/**
 * Edited product and blog post, English and German, are read anew without a restart.
 *
 * @coversNothing
 */
final class PageCacheChainTest extends TestCase {

	/**
	 * Case ids registered for #339.
	 */
	private const CASES = array(
		'405-product-en',
		'405-product-de',
		'405-blog-en',
		'405-blog-de',
	);

	/**
	 * Posts this test created.
	 *
	 * @var list<int>
	 */
	private array $posts = array();

	/**
	 * The service address this test replaced, restored in tearDown.
	 *
	 * @var string
	 */
	private string $previous_service = '';

	/**
	 * Whether tearDown must write the service address back.
	 *
	 * @var bool
	 */
	private bool $replaced = false;

	/**
	 * Probe process.
	 *
	 * @var resource|null
	 */
	private $process = null;

	/**
	 * Probe stdout and stderr.
	 *
	 * @var array<int, resource>
	 */
	private array $pipes = array();

	/**
	 * Mu-plugin copied into the instance. Removed in tearDown.
	 *
	 * @var string
	 */
	private string $render = '';

	/**
	 * Shared service token.
	 *
	 * @var string
	 */
	private string $token = '';

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just page-cache-chain); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Restores the instance: service address, probe posts, render, process.
	 */
	protected function tearDown(): void {
		$this->restore_service();
		$this->drop_translation_jobs();
		foreach ( $this->posts as $id ) {
			wp_delete_post( $id, true );
		}
		if ( '' !== $this->render && is_file( $this->render ) ) {
			unlink( $this->render );
		}
		$this->stop_probe();
		parent::tearDown();
	}

	/**
	 * An edited product, an edited blog post, and each German twin.
	 *
	 * The next read of each path contains the new title and sentence. The
	 * Genie process is the one that accepted the invalidation; it is not restarted.
	 */
	public function test_an_edited_product_and_post_are_read_anew_in_both_languages(): void {
		$this->assertSame(
			array( '405-product-en', '405-product-de', '405-blog-en', '405-blog-de' ),
			self::CASES
		);
		if ( ! function_exists( 'pll_set_post_language' ) || ! function_exists( 'PLL' ) || ! PLL()->model->get_language( 'en' ) || ! PLL()->model->get_language( 'de' ) ) {
			self::markTestSkipped( 'Polylang needs en and de. Run: wp linker-i18n setup --user=local-admin' );
		}
		if ( ! defined( Proxy::TOKEN_CONSTANT ) || '' === (string) constant( Proxy::TOKEN_CONSTANT ) ) {
			self::markTestSkipped( 'LINKER_GENIE_SERVICE_TOKEN is not set on this instance.' );
		}
		$this->token = (string) constant( Proxy::TOKEN_CONSTANT );
		$this->install_render();
		$probe                  = $this->start_probe();
		$this->previous_service = (string) get_option( Proxy::OPTION, '' );
		update_option( Proxy::OPTION, $probe );
		$this->replaced = true;

		$mark = 'c405' . strtolower( wp_generate_password( 6, false, false ) );
		$ids  = array(
			'405-product-en' => $this->publish( 'product', 'en', "OLD {$mark} product en" ),
			'405-product-de' => $this->publish( 'product', 'de', "OLD {$mark} product de" ),
			'405-blog-en'    => $this->publish( 'post', 'en', "OLD {$mark} blog en" ),
			'405-blog-de'    => $this->publish( 'post', 'de', "OLD {$mark} blog de" ),
		);
		if ( function_exists( 'pll_save_post_translations' ) ) {
			pll_save_post_translations(
				array(
					'en' => $ids['405-product-en'],
					'de' => $ids['405-product-de'],
				)
			);
			pll_save_post_translations(
				array(
					'en' => $ids['405-blog-en'],
					'de' => $ids['405-blog-de'],
				)
			);
		}
		$this->drop_translation_jobs();
		// WordPress writes the GUID with get_permalink before the language term
		// exists. Polylang's front-end link cache keeps that address. A later
		// get_permalink, including the one PageCache sends on the edit, would
		// repeat it. Clearing the cache makes the path the public one.
		$this->forget_cached_permalinks();

		$paths = array();
		foreach ( $ids as $case => $id ) {
			$paths[ $case ] = $this->path_of( (string) get_permalink( $id ) );
		}
		$this->assertStringContainsString( '/de/', $paths['405-product-de'] );
		$this->assertStringContainsString( '/de/', $paths['405-blog-de'] );
		$this->assertNotSame( $paths['405-product-en'], $paths['405-product-de'] );
		$this->assertNotSame( $paths['405-blog-en'], $paths['405-blog-de'] );

		foreach ( $ids as $case => $id ) {
			$old = "OLD {$mark} " . $this->label( $case );
			$this->assertStringContainsString( $old, $this->read( $case, $paths[ $case ], $id ) );
		}

		foreach ( $ids as $case => $id ) {
			$this->edit( $id, "NEW {$mark} " . $this->label( $case ) );
		}
		$this->drop_translation_jobs();
		$this->deliver_saved_pages();

		foreach ( $ids as $case => $id ) {
			$body = $this->read( $case, $paths[ $case ], $id );
			$this->assertStringContainsString( "NEW {$mark} " . $this->label( $case ), $body, $case );
			$this->assertStringNotContainsString( "OLD {$mark} " . $this->label( $case ), $body, $case );
		}
	}

	/**
	 * The short label embedded in a case's old and new text.
	 *
	 * @param string $case_id Case id.
	 */
	private function label( string $case_id ): string {
		return match ( $case_id ) {
			'405-product-en' => 'product en',
			'405-product-de' => 'product de',
			'405-blog-en' => 'blog en',
			'405-blog-de' => 'blog de',
			default => $case_id,
		};
	}

	/**
	 * A published probe post. The mu-plugin renders it with `<main>`.
	 *
	 * @param string $type     product or post.
	 * @param string $language en or de.
	 * @param string $text     Title and sentence.
	 */
	private function publish( string $type, string $language, string $text ): int {
		$assign = static function ( int $post_id ) use ( $language ): void {
			if ( function_exists( 'pll_set_post_language' ) ) {
				pll_set_post_language( $post_id, $language );
			}
		};
		add_action( 'save_post', $assign, 0, 1 );
		$id = wp_insert_post(
			array(
				'post_type'    => $type,
				'post_status'  => 'publish',
				'post_title'   => $text,
				'post_content' => $text,
				'post_name'    => sanitize_title( $text ),
			),
			true
		);
		remove_action( 'save_post', $assign, 0 );
		$this->assertIsInt( $id, is_wp_error( $id ) ? $id->get_error_message() : '' );
		$this->posts[] = $id;
		update_post_meta( $id, '_linker_page_cache_probe', '1' );
		return $id;
	}

	/**
	 * Drops Polylang's cached permalinks so the next get_permalink is rebuilt.
	 */
	private function forget_cached_permalinks(): void {
		if ( ! function_exists( 'PLL' ) ) {
			return;
		}
		$polylang = PLL();
		if ( ! is_object( $polylang ) || ! isset( $polylang->filters_links ) || ! is_object( $polylang->filters_links ) ) {
			return;
		}
		$links = $polylang->filters_links;
		if ( ! isset( $links->cache ) || ! is_object( $links->cache ) || ! method_exists( $links->cache, 'clean' ) ) {
			return;
		}
		$links->cache->clean();
	}

	/**
	 * The edit the shell hears: wp_update_post, which fires wp_after_insert_post.
	 *
	 * @param int    $id   Post ID.
	 * @param string $text New title and sentence.
	 */
	private function edit( int $id, string $text ): void {
		$updated = wp_update_post(
			array(
				'ID'           => $id,
				'post_title'   => $text,
				'post_content' => $text,
			),
			true
		);
		$this->assertIsInt( $updated, is_wp_error( $updated ) ? $updated->get_error_message() : '' );
	}

	/**
	 * The path PageCache would send and PageReader would fetch.
	 *
	 * @param string $url Permalink.
	 */
	private function path_of( string $url ): string {
		$parts = wp_parse_url( $url );
		$this->assertIsArray( $parts, $url );
		$path = (string) ( $parts['path'] ?? '' );
		$this->assertNotSame( '', $path, $url );
		$this->assertStringNotContainsString( '?', $url, 'a query permalink would not match the read key' );
		return $path;
	}

	/**
	 * The next read-page, against the probe process.
	 *
	 * @param string $case_id Case id, for the failure message.
	 * @param string $path    Site path.
	 * @param int    $post_id Post ID.
	 */
	private function read( string $case_id, string $path, int $post_id ): string {
		$type     = str_contains( $case_id, 'product' ) ? 'product' : 'blog';
		$response = wp_remote_post(
			$this->probe_url() . '/__page_cache_test/read',
			array(
				'headers' => array(
					'Content-Type'      => 'application/json',
					Proxy::TOKEN_HEADER => $this->token,
				),
				'body'    => (string) wp_json_encode(
					array(
						'type'    => $type,
						'url'     => $path,
						'post_id' => $post_id,
					)
				),
				'timeout' => 30,
			)
		);
		$this->assertIsArray( $response, is_wp_error( $response ) ? $response->get_error_message() : '' );
		$code = (int) wp_remote_retrieve_response_code( $response );
		$body = (string) wp_remote_retrieve_body( $response );
		$this->assertSame( 200, $code, $case_id . ' ' . $body );
		return $body;
	}

	/**
	 * Runs the PageCache shutdown callback the plugin registered.
	 *
	 * Firing every shutdown handler would close the object cache mid-test.
	 * This is the callback WordPress calls for that hook.
	 */
	private function deliver_saved_pages(): void {
		global $wp_filter;
		$hook = $wp_filter['shutdown'] ?? null;
		$this->assertInstanceOf( \WP_Hook::class, $hook );
		$found = false;
		foreach ( $hook->callbacks as $group ) {
			foreach ( $group as $callback ) {
				$function = $callback['function'];
				if ( is_array( $function ) && $function[0] instanceof PageCache && 'send' === $function[1] ) {
					$function[0]->send();
					$found = true;
				}
			}
		}
		$this->assertTrue( $found, 'PageCache::send is not on shutdown' );
	}

	/**
	 * Drops translation jobs for these posts so a later page view does not run them.
	 */
	private function drop_translation_jobs(): void {
		if ( ! function_exists( 'as_unschedule_all_actions' ) || array() === $this->posts ) {
			return;
		}
		foreach ( $this->posts as $id ) {
			as_unschedule_all_actions( 'linker_i18n_translate', array( 'post', $id, false, 1 ), 'linker-i18n' );
		}
	}

	/**
	 * Copies the probe render into mu-plugins. The next HTTP GET of a probe post uses it.
	 */
	private function install_render(): void {
		$source = __DIR__ . '/fixtures/page-cache-probe-render.php';
		$this->assertFileExists( $source );
		$this->render = WPMU_PLUGIN_DIR . '/linker-405-page-cache-probe.php';
		$this->assertTrue( copy( $source, $this->render ) );
	}

	/**
	 * Starts the real app plus the test read route. Returns its base URL.
	 */
	private function start_probe(): string {
		$repo   = dirname( __DIR__, 5 );
		$script = $repo . '/services/genie/tests/page_cache_probe.py';
		$this->assertFileExists( $script );
		$env                        = getenv();
		$env['GENIE_WP_URL']        = untrailingslashit( home_url() );
		$env['GENIE_SERVICE_TOKEN'] = $this->token;
		$env['GENIE_LOG']           = sys_get_temp_dir() . '/linker-405-' . (string) getmypid() . '.sqlite';
		unset( $env['GENIE_INDEX'] );
		$pipes   = array();
		$process = proc_open(
			array( 'uv', 'run', '--locked', '--project', $repo . '/services/genie', 'python', $script ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes,
			$repo,
			$env
		);
		$this->assertIsResource( $process );
		$this->process = $process;
		fclose( $pipes[0] );
		stream_set_blocking( $pipes[1], false );
		stream_set_blocking( $pipes[2], false );
		$this->pipes = array(
			1 => $pipes[1],
			2 => $pipes[2],
		);
		$stdout      = '';
		$stderr      = '';
		$deadline    = microtime( true ) + 90;
		$port        = 0;
		while ( microtime( true ) < $deadline ) {
			$stdout .= (string) stream_get_contents( $pipes[1] );
			$stderr .= (string) stream_get_contents( $pipes[2] );
			if ( 1 === preg_match( '/READY (\d+)/', $stdout, $found ) ) {
				$port = (int) $found[1];
				break;
			}
			$status = proc_get_status( $process );
			if ( ! $status['running'] ) {
				break;
			}
			usleep( 100000 );
		}
		$this->assertGreaterThan( 0, $port, $stderr . $stdout );
		return 'http://127.0.0.1:' . (string) $port;
	}

	/**
	 * The probe base URL currently configured as the Genie service.
	 */
	private function probe_url(): string {
		return rtrim( (string) get_option( Proxy::OPTION, '' ), '/' );
	}

	/**
	 * Writes the previous Genie address back.
	 */
	private function restore_service(): void {
		if ( $this->replaced ) {
			update_option( Proxy::OPTION, $this->previous_service );
			$this->replaced = false;
		}
	}

	/**
	 * Stops the probe process.
	 */
	private function stop_probe(): void {
		foreach ( $this->pipes as $pipe ) {
			if ( is_resource( $pipe ) ) {
				stream_get_contents( $pipe );
				fclose( $pipe );
			}
		}
		$this->pipes = array();
		if ( is_resource( $this->process ) ) {
			proc_terminate( $this->process );
			proc_close( $this->process );
			$this->process = null;
		}
	}
}

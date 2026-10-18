<?php
/**
 * Base of the integration tests.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- these tests run outside WordPress: HTTP, files, JSON and WP-CLI through PHP itself.

/**
 * The integration tests drive a local WordPress with WooCommerce, Polylang
 * and this plugin, loaded with the live fixture (tests/fixtures/seed.php) and
 * migrated (tools/migrate/9-i18n.py), over HTTP and through WP-CLI:
 *
 *     LINKER_I18N_SITE=http://127.0.0.1:8897 \
 *     LINKER_I18N_WP=/tmp/t9-wp.sh \
 *     LINKER_I18N_STUB=http://127.0.0.1:8119/ \
 *     vendor/bin/phpunit --testsuite integration
 *
 * The site is a `linker-local` instance (tools/local, `just up t9`);
 * LINKER_I18N_WP is a WP-CLI command for that site (a wrapper around
 * `linker-local wp t9`), LINKER_I18N_STUB the DeepSeek stand-in
 * (`php -S 127.0.0.1:8119 tests/php/Integration/stub/deepseek.php`).
 * The instance runs with DISABLE_WP_CRON, so that a translation runs only
 * when a test runs it. Without LINKER_I18N_SITE the tests are skipped.
 * DEEPSEEK_API_KEY of the calling shell never reaches WP-CLI: a test that
 * translates passes the stand-in's key itself.
 */
abstract class SiteTestCase extends TestCase {

	/**
	 * The site's root URL, without a trailing slash.
	 *
	 * @var string
	 */
	protected static string $site = '';

	/**
	 * The WP-CLI command.
	 *
	 * @var string
	 */
	private static string $wp = '';

	/**
	 * Skips the tests without a site; fails when the site runs WP-Cron.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$site = getenv( 'LINKER_I18N_SITE' );
		$wp   = getenv( 'LINKER_I18N_WP' );
		if ( ! is_string( $site ) || '' === $site || ! is_string( $wp ) || '' === $wp ) {
			self::markTestSkipped( 'LINKER_I18N_SITE and LINKER_I18N_WP name no local site.' );
		}
		self::$site = rtrim( $site, '/' );
		self::$wp   = $wp;
		self::assertTrue( self::php( 'return defined( "DISABLE_WP_CRON" ) && DISABLE_WP_CRON;' ), 'The site must run with DISABLE_WP_CRON: WP-Cron would run the translation queue in parallel with the tests.' );
	}

	/**
	 * A request to the site; redirects are not followed.
	 *
	 * @param string                $method  HTTP method.
	 * @param string                $path    Path and query from the site root.
	 * @param array<string, string> $headers Request headers.
	 * @param string|null           $body    Request body.
	 * @return array{status: int, headers: array<string, string>, body: string} Header names in lower case.
	 * @phpstan-impure HTTP observes the site's current database state.
	 */
	protected static function request( string $method, string $path, array $headers = array(), ?string $body = null ): array {
		$lines = array();
		foreach ( $headers as $name => $value ) {
			$lines[] = $name . ': ' . $value;
		}
		$context = stream_context_create(
			array(
				'http' => array(
					'method'          => $method,
					'header'          => implode( "\r\n", $lines ),
					'content'         => $body ?? '',
					'follow_location' => 0,
					'ignore_errors'   => true,
					'timeout'         => 120,
				),
			)
		);
		$content = file_get_contents( self::$site . $path, false, $context );
		$status  = 0;
		$fields  = array();
		foreach ( $http_response_header as $line ) {
			if ( 1 === preg_match( '#^HTTP/\S+ (\d{3})#', $line, $match ) ) {
				$status = (int) $match[1];
				$fields = array();
			} elseif ( str_contains( $line, ':' ) ) {
				list( $name, $value )          = explode( ':', $line, 2 );
				$fields[ strtolower( $name ) ] = trim( $value );
			}
		}
		return array(
			'status'  => $status,
			'headers' => $fields,
			'body'    => false === $content ? '' : $content,
		);
	}

	/**
	 * A GET. A local site has no page cache, so the URL is the page's own
	 * (Polylang carries a query string into the hreflang links of archives).
	 *
	 * @param string                $path    Path and query from the site root.
	 * @param array<string, string> $headers Request headers.
	 * @return array{status: int, headers: array<string, string>, body: string}
	 * @phpstan-impure HTTP observes the site's current database state.
	 */
	protected static function get( string $path, array $headers = array() ): array {
		return self::request( 'GET', $path, $headers );
	}

	/**
	 * A REST GET, decoded.
	 *
	 * @param string $route Route and query, e.g. /wc/store/v1/products?lang=de.
	 * @return mixed
	 */
	protected static function rest( string $route ) {
		$response = self::get( '/wp-json' . $route );
		self::assertSame( 200, $response['status'], $route . ': ' . substr( $response['body'], 0, 300 ) );
		return json_decode( $response['body'], true );
	}

	/**
	 * Runs WP-CLI as the administrator and returns its output.
	 *
	 * @param array<int, string>    $args Arguments.
	 * @param array<string, string> $env  Environment beyond the calling shell's.
	 */
	protected static function wp( array $args, array $env = array() ): string {
		$environment = getenv();
		unset( $environment['DEEPSEEK_API_KEY'] );
		$process = proc_open(
			// Shadow getenv only inside the translator's namespace: integration
			// fixtures cannot discover the real HOME credential file. The fake key
			// supplied by php(..., true) still reaches the stand-in normally.
			array_merge( array( self::$wp, '--exec=namespace Linker\I18n\Translation; function getenv( string $name ): string|false { return "HOME" === $name ? false : \getenv( $name ); }' ), $args, array( '--user=1' ) ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes,
			null,
			$env + $environment
		);
		self::assertIsResource( $process );
		$output = (string) stream_get_contents( $pipes[1] );
		$errors = (string) stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), 'wp ' . implode( ' ', $args ) . ":\n" . $output . $errors );
		return $output;
	}

	/**
	 * Runs PHP inside WordPress: the body of a function that gets $input and
	 * whose return value comes back (both JSON-encoded on the way).
	 *
	 * @param string               $body       Function body.
	 * @param array<string, mixed> $input      Values for the body, as $input.
	 * @param bool                 $translator Whether DEEPSEEK_API_KEY is set, for the stand-in.
	 * @return mixed
	 */
	protected static function php( string $body, array $input = array(), bool $translator = false ) {
		// Native fixture deletes trigger SEOPress redirect suggestions. Restore
		// its option too, so repeated tests leave the refreshed admin clean.
		$script = '$notices = get_option( "seopress_can_post_redirect", null ); try { echo "\nLINKER_I18N_RESULT ", wp_json_encode( ( static function ( array $input ) { ' . $body . ' } )( json_decode( (string) getenv( "LINKER_I18N_INPUT" ), true ) ) ), "\n"; } finally { if ( null === $notices ) { delete_option( "seopress_can_post_redirect" ); } else { update_option( "seopress_can_post_redirect", $notices ); } }';
		$args   = array( 'eval', $script );
		$env    = array( 'LINKER_I18N_INPUT' => (string) json_encode( (object) $input ) );
		if ( $translator ) {
			self::stub();
			array_unshift( $args, '--exec=define( "LINKER_I18N_DEEPSEEK_ENDPOINT", getenv( "LINKER_I18N_STUB" ) );' );
			$env['DEEPSEEK_API_KEY'] = 'stand-in';
		}
		$output = self::wp( $args, $env );
		if ( 1 !== preg_match( '/^LINKER_I18N_RESULT (.*)$/m', $output, $match ) ) {
			self::fail( 'No result: ' . $output );
		}
		return json_decode( $match[1], true );
	}

	/**
	 * Runs the queued translations of one object, as Action Scheduler's
	 * runner would, and returns how many ran.
	 *
	 * @param string $kind       post or term.
	 * @param int    $id         English object ID.
	 * @param bool   $translator Whether DEEPSEEK_API_KEY is set, for the stand-in.
	 */
	protected static function run_jobs( string $kind, int $id, bool $translator ): int {
		$ran = self::php(
			'
			$ran = 0;
			foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "status" => ActionScheduler_Store::STATUS_PENDING, "per_page" => -1 ), "ids" ) as $action_id ) {
				$args = ActionScheduler::store()->fetch_action( $action_id )->get_args();
				if ( $input["kind"] === $args[0] && $input["id"] === (int) $args[1] ) {
					ActionScheduler_QueueRunner::instance()->process_action( $action_id, "WP CLI" );
					++$ran;
				}
			}
			return $ran;
			',
			array(
				'kind' => $kind,
				'id'   => $id,
			),
			$translator
		);
		self::assertIsInt( $ran );
		return $ran;
	}

	/**
	 * The DeepSeek stand-in's URL; skips the test without one.
	 */
	protected static function stub(): string {
		$stub = getenv( 'LINKER_I18N_STUB' );
		if ( ! is_string( $stub ) || '' === $stub ) {
			self::markTestSkipped( 'LINKER_I18N_STUB names no DeepSeek stand-in.' );
		}
		return $stub;
	}

	/**
	 * The attributes of the first tag of a name, or null.
	 *
	 * @param string $html HTML.
	 * @param string $tag  Tag name.
	 * @param string $has  Text the tag must contain.
	 */
	protected static function tag( string $html, string $tag, string $has = '' ): ?string {
		preg_match_all( '/<' . $tag . '\b[^>]*>/i', $html, $matches );
		foreach ( $matches[0] as $found ) {
			if ( '' === $has || str_contains( $found, $has ) ) {
				return $found;
			}
		}
		return null;
	}

	/**
	 * The hreflang links of a page: language => URL.
	 *
	 * @param string $html HTML.
	 * @return array<string, string>
	 */
	protected static function hreflangs( string $html ): array {
		preg_match_all( '/<link rel="alternate" href="([^"]+)" hreflang="([^"]+)"/', $html, $matches, PREG_SET_ORDER );
		$out = array();
		foreach ( $matches as $match ) {
			$out[ $match[2] ] = html_entity_decode( $match[1] );
		}
		return $out;
	}
}

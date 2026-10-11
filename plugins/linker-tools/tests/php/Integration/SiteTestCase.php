<?php
/**
 * Base of the integration tests.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- these tests run outside WordPress: HTTP and WP-CLI through PHP itself.

/**
 * The integration tests drive a local WordPress with WooCommerce, Polylang
 * and this plugin, loaded with the live fixture (a `linker-pull` snapshot, the
 * live catalogue's withdrawn products and retired shelves included), over
 * HTTP and through WP-CLI:
 *
 *     LINKER_TOOLS_SITE=http://127.0.0.1:8942 \
 *     LINKER_TOOLS_WP=~/de-linker-local/t80/wp.sh \
 *     vendor/bin/phpunit --testsuite integration
 *
 * The site is a `linker-local` instance (`tools/local`, `just up t80`) with
 * the snapshot loaded; LINKER_TOOLS_WP is a WP-CLI command for that site.
 * Without LINKER_TOOLS_SITE the tests are skipped.
 */
abstract class SiteTestCase extends TestCase {

	/**
	 * The site's root URL, without a trailing slash.
	 *
	 * @var string
	 */
	protected static string $site = '';

	/**
	 * The WP-CLI command for the site.
	 *
	 * @var string
	 */
	private static string $wp = '';

	/**
	 * Skips the tests without a site.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$site = getenv( 'LINKER_TOOLS_SITE' );
		$wp   = getenv( 'LINKER_TOOLS_WP' );
		if ( ! is_string( $site ) || '' === $site || ! is_string( $wp ) || '' === $wp ) {
			self::markTestSkipped( 'LINKER_TOOLS_SITE and LINKER_TOOLS_WP name no local site.' );
		}
		self::$site = rtrim( $site, '/' );
		self::$wp   = $wp;
	}

	/**
	 * A request to the site; redirects are not followed.
	 *
	 * @param string $path Path and query from the site root.
	 * @return array{status: int, headers: array<string, string>, body: string} Header names in lower case.
	 */
	protected static function get( string $path ): array {
		$context = stream_context_create(
			array(
				'http' => array(
					'method'          => 'GET',
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
	 * The status and Location of a request, as the redirect tests read them.
	 *
	 * @param string $path Path from the site root.
	 * @return array{status: int, location: string}
	 */
	protected static function redirect( string $path ): array {
		$response = self::get( $path );

		return array(
			'status'   => $response['status'],
			'location' => $response['headers']['location'] ?? '',
		);
	}

	/**
	 * Asserts that a path answers with a permanent redirect to a path of this
	 * site.
	 *
	 * @param string $path   Requested path.
	 * @param string $target Expected Location, from the site root.
	 */
	protected static function assertRedirects( string $path, string $target ): void {
		$response = self::redirect( $path );
		self::assertSame( 301, $response['status'], $path . ' answers ' . $response['status'] . ' -> ' . $response['location'] );
		self::assertSame( self::$site . $target, $response['location'] );
	}

	/**
	 * Asserts that nothing redirects a path: the site answers it itself.
	 *
	 * @param string $path     Requested path.
	 * @param int    $expected Status the path itself answers with.
	 */
	protected static function assertStays( string $path, int $expected ): void {
		$response = self::redirect( $path );
		self::assertSame( $expected, $response['status'], $path . ' answers ' . $response['status'] . ' -> ' . $response['location'] );
		self::assertSame( '', $response['location'], $path . ' redirects to ' . $response['location'] );
	}

	/**
	 * Runs WP-CLI against the site and returns its output.
	 *
	 * @param array<int, string> $args Arguments.
	 */
	protected static function wp( array $args ): string {
		$process = proc_open(
			array_merge( array( self::$wp ), $args, array( '--user=1' ) ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		$output = (string) stream_get_contents( $pipes[1] );
		$errors = (string) stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), 'wp ' . implode( ' ', $args ) . ":\n" . $output . $errors );

		return $output;
	}
}

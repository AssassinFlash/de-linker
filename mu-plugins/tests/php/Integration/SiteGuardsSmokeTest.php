<?php
/**
 * The site guards and the engine pin on a real WordPress.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Integration;

use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- this test drives WP-CLI and asks the site over HTTP, from outside WordPress.

/**
 * The smoke test of the public site's security baseline against a real site:
 * linker-site-guards.php is installed the way the cutover installs it (a file
 * in wp-content/mu-plugins), and anonymous requests are asked for what the
 * file promises — the four response headers on a page, and the closed REST
 * user list. The site's previous guards file, if any, is put back afterwards.
 *
 * The engine pin is asserted as an installation, not as a behaviour: see the
 * test itself.
 *
 *     LINKER_MU_WP=~/de-linker-local/<instance>/wp.sh vendor/bin/phpunit --testsuite integration
 *
 * Without LINKER_MU_WP the tests are skipped.
 */
final class SiteGuardsSmokeTest extends TestCase {

	/**
	 * The WP-CLI command for the site.
	 *
	 * @var string
	 */
	private static string $wp = '';

	/**
	 * The site's wp-content directory.
	 *
	 * @var string
	 */
	private static string $content = '';

	/**
	 * The address the site answers on.
	 *
	 * @var string
	 */
	private static string $url = '';

	/**
	 * The guards file the site had, or '' when it had none.
	 *
	 * @var string
	 */
	private static string $installed = '';

	/**
	 * Skips the tests without a site; finds the site's wp-content and address.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$wp = getenv( 'LINKER_MU_WP' );
		if ( ! is_string( $wp ) || '' === $wp ) {
			self::markTestSkipped( 'LINKER_MU_WP names no local site.' );
		}
		self::$wp      = $wp;
		self::$content = trim( self::wp( array( 'eval', 'echo WP_CONTENT_DIR;' ) ) );
		self::$url     = trim( self::wp( array( 'eval', 'echo home_url();' ) ) );
		self::assertDirectoryExists( self::$content );
		self::assertNotSame( '', self::$url );
	}

	/**
	 * Installs the guards under the name the cutover deploys it as.
	 */
	protected function setUp(): void {
		parent::setUp();
		$target          = self::$content . '/mu-plugins/linker-site-guards.php';
		self::$installed = is_file( $target ) ? (string) file_get_contents( $target ) : '';
		self::assertTrue( copy( dirname( __DIR__, 3 ) . '/linker-site-guards.php', $target ) );
	}

	/**
	 * Puts the site's own guards file back.
	 */
	protected function tearDown(): void {
		$target = self::$content . '/mu-plugins/linker-site-guards.php';
		if ( '' === self::$installed ) {
			unlink( $target );
		} else {
			file_put_contents( $target, self::$installed );
		}
		self::$installed = '';
		parent::tearDown();
	}

	/**
	 * An anonymous page carries the four headers the guards declare, with the
	 * values the site's policy states.
	 */
	public function test_an_anonymous_page_carries_the_security_headers(): void {
		$response = self::fetch( self::$url . '/' );

		self::assertSame( 200, $response['status'], 'the home page answers' );
		self::assertSame(
			'max-age=31536000; includeSubDomains',
			$response['headers']['strict-transport-security'] ?? ''
		);
		self::assertSame( 'SAMEORIGIN', $response['headers']['x-frame-options'] ?? '' );
		self::assertSame( 'nosniff', $response['headers']['x-content-type-options'] ?? '' );
		self::assertSame(
			'strict-origin-when-cross-origin',
			$response['headers']['referrer-policy'] ?? ''
		);
	}

	/**
	 * An anonymous `/wp/v2/users` is refused with the guard's own error, not
	 * enumerated: the login names are the first half of a password attack.
	 */
	public function test_the_rest_user_list_is_closed_to_anonymous_requests(): void {
		$response = self::fetch( self::$url . '/wp-json/wp/v2/users' );

		self::assertSame( 403, $response['status'] );
		self::assertStringContainsString( '"code":"rest_forbidden"', $response['body'] );
	}

	/**
	 * The engine pin is asserted as what it is on this machine: an installed
	 * mu-plugin. What it does — hand WordPress's HTTP layer the pinned
	 * certificate before a call to the services VPS — is the services side's
	 * half of the contract (the engine serves that certificate), so there is
	 * no behaviour here to smoke without a second host. What the test holds is
	 * the installation: the file is in the site's mu-plugins, where every
	 * request loads it, and it guards on ABSPATH like the rest of them.
	 *
	 * The certificate beside it is not asserted: a local instance has none
	 * (the local stack copies `mu-plugins/*.php` only, and the pin's own first
	 * check steps aside when the pem is unreadable), while production receives
	 * the engine host's own `/etc/linker-engine/engine.crt` at the deployment.
	 */
	public function test_the_engine_pin_is_installed_as_a_mu_plugin(): void {
		$pin = self::$content . '/mu-plugins/linker-engine-pin.php';
		self::assertFileExists( $pin );
		self::assertStringContainsString(
			"defined( 'ABSPATH' ) || exit;",
			(string) file_get_contents( $pin )
		);
	}

	/**
	 * One anonymous request: its status, its headers lower-cased, and its body.
	 *
	 * The context refuses redirects, so the status and headers asserted above
	 * are the first response's, not the end of a redirect chain.
	 *
	 * @param string $url The address to ask.
	 *
	 * @return array{status: int, headers: array<string, string>, body: string}
	 */
	private static function fetch( string $url ): array {
		$context = stream_context_create(
			array(
				'http' => array(
					'method'          => 'GET',
					'ignore_errors'   => true,
					'follow_location' => 0,
					'timeout'         => 10,
				),
			)
		);
		$body    = (string) file_get_contents( $url, false, $context );
		$lines   = get_headers( $url, true, $context );
		self::assertIsArray( $lines, $url . ' did not answer' );

		$status  = 0;
		$headers = array();
		foreach ( $lines as $name => $value ) {
			// A repeated header arrives as a list; its first value is the one
			// the assertions above name.
			$first = is_array( $value ) ? (string) ( $value[0] ?? '' ) : $value;
			if ( is_int( $name ) ) {
				if ( preg_match( '#^HTTP/\S+\s+(\d+)#', $first, $match ) ) {
					$status = (int) $match[1];
				}
				continue;
			}
			$headers[ strtolower( (string) $name ) ] = $first;
		}

		return array(
			'status'  => $status,
			'headers' => $headers,
			'body'    => $body,
		);
	}

	/**
	 * Runs WP-CLI against the site and returns its output.
	 *
	 * @param array<int, string> $args Arguments.
	 */
	private static function wp( array $args ): string {
		$process = proc_open(
			array_merge( array( self::$wp ), $args ),
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

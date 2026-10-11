<?php
/**
 * The recorder on a real WordPress.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Integration;

use Linker\Mu\ErrorRecorder;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- this test drives WP-CLI and the filesystem from outside WordPress.

/**
 * The smoke test of the recorder against a real site: it is installed the way
 * the cutover installs it (a file in wp-content/mu-plugins), a real WP-CLI
 * request that raises an error runs, and the error is read back from the
 * recorder's own file. The site's previous recorder file, if any, is put back
 * afterwards.
 *
 *     LINKER_MU_WP=~/de-linker-local/t80/wp.sh vendor/bin/phpunit --testsuite integration
 *
 * Without LINKER_MU_WP the tests are skipped.
 */
final class RecorderSmokeTest extends TestCase {

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
	 * The recorder file the site had, or '' when it had none.
	 *
	 * @var string
	 */
	private static string $installed = '';

	/**
	 * Skips the tests without a site; finds the site's wp-content.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$wp = getenv( 'LINKER_MU_WP' );
		if ( ! is_string( $wp ) || '' === $wp ) {
			self::markTestSkipped( 'LINKER_MU_WP names no local site.' );
		}
		self::$wp      = $wp;
		self::$content = trim( self::wp( array( 'eval', 'echo WP_CONTENT_DIR;' ) ) );
		self::assertDirectoryExists( self::$content );
	}

	/**
	 * Installs the recorder under the name the cutover deploys it as.
	 */
	protected function setUp(): void {
		parent::setUp();
		$target          = self::$content . '/mu-plugins/linker-error-recorder.php';
		self::$installed = is_file( $target ) ? (string) file_get_contents( $target ) : '';
		self::assertTrue( copy( dirname( __DIR__, 3 ) . '/linker-error-recorder.php', $target ) );
	}

	/**
	 * Puts the site's own recorder file back.
	 */
	protected function tearDown(): void {
		$target = self::$content . '/mu-plugins/linker-error-recorder.php';
		if ( '' === self::$installed ) {
			unlink( $target );
		} else {
			file_put_contents( $target, self::$installed );
		}
		self::$installed = '';
		parent::tearDown();
	}

	/**
	 * An error raised in a real request is read back from the recorder's file,
	 * and the directory that holds it refuses web requests.
	 */
	public function test_a_real_request_writes_its_error_to_the_recorders_file(): void {
		$marker = 'linker recorder smoke ' . bin2hex( random_bytes( 4 ) );
		self::wp(
			array(
				'eval',
				// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- a quoted PHP literal for the eval; the marker is random bytes.
				sprintf( 'trigger_error( %s, E_USER_WARNING );', var_export( $marker, true ) ),
			)
		);

		$log = ErrorRecorder::path( self::$content );
		$this->assertFileExists( $log );
		$this->assertStringContainsString( $marker, (string) file_get_contents( $log ) );

		$directory = dirname( $log );
		$this->assertStringContainsString( 'Require all denied', (string) file_get_contents( $directory . '/.htaccess' ) );
		$this->assertFileExists( $directory . '/index.html' );
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

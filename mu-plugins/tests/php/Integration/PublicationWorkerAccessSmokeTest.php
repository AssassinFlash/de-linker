<?php
/**
 * Native application-password authentication, HTTP scope and concurrency.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Integration;

use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- external local WordPress fixture driver, matching the MU smoke entry point.

/** Restores the instance's exact MU files after an owned synthetic fixture. */
final class PublicationWorkerAccessSmokeTest extends TestCase {

	/**
	 * A real server must verify the key before its purpose scope can apply.
	 */
	public function test_native_credentials_and_cookie_scope_with_zero_non_job_canaries(): void {
		$command = getenv( 'LINKER_MU_WP' );
		if ( ! is_string( $command ) || '' === trim( $command ) ) {
			self::markTestSkipped( 'LINKER_MU_WP names no owned local instance.' );
		}
		$wp      = array_values( array_filter( array_map( 'strval', (array) preg_split( '/\s+/', trim( $command ) ) ) ) );
		$context = json_decode( self::wp( $wp, array( 'eval', 'echo wp_json_encode(array("content"=>WP_CONTENT_DIR,"local"=>defined("LINKER_LOCAL_MAIL_DIR") && "local"===wp_get_environment_type() && "127.0.0.1"===wp_parse_url(home_url(),PHP_URL_HOST)));' ) ), true, 512, JSON_THROW_ON_ERROR );
		self::assertTrue( $context['local'] ?? false, 'Native scope tests refuse a non-local instance.' );
		$directory = $context['content'] . '/mu-plugins/';
		$files     = array(
			'linker-publication-worker-access.php'      => dirname( __DIR__, 3 ) . '/linker-publication-worker-access.php',
			'000-linker-publication-worker-fixture.php' => dirname( __DIR__ ) . '/fixtures/publication-worker-loader.php',
		);
		$originals = array();
		try {
			foreach ( $files as $name => $source ) {
				$originals[ $name ] = is_file( $directory . $name ) ? file_get_contents( $directory . $name ) : null;
				self::assertTrue( copy( $source, $directory . $name ) );
			}
			// Include preserves the file's leading strict-types declaration.
			$output = self::wp( $wp, array( 'eval-file', dirname( __DIR__ ) . '/fixtures/publication-worker-access.php', '--use-include' ) );
			$result = json_decode( trim( $output ), true, 512, JSON_THROW_ON_ERROR );
			self::assertSame( 52, $result['checks'] ?? 0 );
			self::assertSame( 0, $result['purpose_non_job_reads'] ?? null );
			self::assertSame( 0, $result['purpose_non_job_writes'] ?? null );
			self::assertTrue( $result['synthetic_only'] ?? false );
		} finally {
			foreach ( $originals as $name => $original ) {
				if ( null === $original ) {
					unlink( $directory . $name );
				} else {
					file_put_contents( $directory . $name, $original );
				}
			}
		}
	}

	/**
	 * Executes without a shell; synthetic credentials never enter process arguments.
	 *
	 * @param array<int, string> $command Local WP-CLI command.
	 * @param array<int, string> $arguments WP-CLI arguments.
	 */
	private static function wp( array $command, array $arguments ): string {
		$pipes   = array();
		$process = proc_open(
			array_merge( $command, $arguments ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		$output = stream_get_contents( $pipes[1] );
		$error  = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), $error );
		return $output;
	}
}

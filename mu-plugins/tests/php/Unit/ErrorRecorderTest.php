<?php
/**
 * Tests for the error recorder.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Unit;

use Linker\Mu\ErrorRecorder;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.NoSilencedErrors.Discouraged, WordPress.PHP.DevelopmentFunctions, WordPress.PHP.IniSet -- this test runs outside WordPress: it writes, reads and rotates real files, and it reads and restores the logging settings under test.

/**
 * The recorder's own work, against real files in a temporary wp-content: what
 * it changes about PHP's logging, what it writes beside the log, and that the
 * log rotates.
 *
 * @covers \Linker\Mu\ErrorRecorder
 */
final class ErrorRecorderTest extends TestCase {

	/**
	 * A temporary wp-content directory of this test.
	 *
	 * @var string
	 */
	private string $content = '';

	/**
	 * A fresh directory per test, and the logging settings put back.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->content = sys_get_temp_dir() . '/linker-mu-recorder-' . bin2hex( random_bytes( 4 ) );
		self::assertTrue( mkdir( $this->content, 0755, true ) );
	}

	/**
	 * The settings restore after the test, so a test cannot leak into the run.
	 */
	protected function tearDown(): void {
		ini_set( 'error_log', (string) $this->original( 'error_log' ) );
		ini_set( 'log_errors', (string) $this->original( 'log_errors' ) );
		$this->remove( $this->content );
		parent::tearDown();
	}

	/**
	 * Recording points PHP's error log at the plugin's own file, turns error
	 * logging on, and keeps errors off the visitor's screen.
	 */
	public function test_recording_points_php_at_its_own_file(): void {
		ErrorRecorder::start( $this->content );

		$this->assertSame( '1', (string) ini_get( 'log_errors' ) );
		$this->assertSame( '0', (string) ini_get( 'display_errors' ) );
		$this->assertSame( ErrorRecorder::path( $this->content ), (string) ini_get( 'error_log' ) );
		$this->assertDirectoryExists( $this->content . '/' . ErrorRecorder::DIRECTORY );
	}

	/**
	 * PHP's error logging writes to the file the recorder names — the property
	 * the host is missing (its log_errors is off, so nothing is written). That
	 * a raised PHP error lands there is the smoke test's job, in a real
	 * request; here it is error_log(), which writes to the same configured
	 * file.
	 */
	public function test_error_logging_writes_to_the_file(): void {
		ErrorRecorder::start( $this->content );
		error_log( 'linker recorder test' );

		$log = ErrorRecorder::path( $this->content );
		$this->assertFileExists( $log );
		$this->assertStringContainsString( 'linker recorder test', (string) file_get_contents( $log ) );
	}

	/**
	 * The directory refuses web requests: the same deny file and empty index
	 * the private upload directories carry.
	 */
	public function test_the_directory_refuses_web_requests(): void {
		ErrorRecorder::start( $this->content );
		$directory = $this->content . '/' . ErrorRecorder::DIRECTORY;

		$this->assertStringContainsString( 'Require all denied', (string) file_get_contents( $directory . '/.htaccess' ) );
		$this->assertFileExists( $directory . '/index.html' );
		$this->assertSame( '', (string) file_get_contents( $directory . '/index.html' ) );
	}

	/**
	 * A full log is moved aside before PHP writes again, and one previous file
	 * is all that is kept.
	 */
	public function test_a_full_log_rotates_to_one_previous_file(): void {
		$directory = $this->content . '/' . ErrorRecorder::DIRECTORY;
		self::assertTrue( mkdir( $directory, 0755, true ) );
		file_put_contents( $directory . '/' . ErrorRecorder::PREVIOUS, 'older' );
		file_put_contents( $directory . '/' . ErrorRecorder::FILE, str_repeat( 'x', ErrorRecorder::MAX_BYTES ) );

		ErrorRecorder::start( $this->content );

		$previous = $directory . '/' . ErrorRecorder::PREVIOUS;
		$this->assertFileDoesNotExist( $directory . '/' . ErrorRecorder::FILE );
		$this->assertSame( ErrorRecorder::MAX_BYTES, filesize( $previous ) );
		$this->assertStringStartsWith( 'x', (string) file_get_contents( $previous ) );
	}

	/**
	 * A log under the limit stays where it is.
	 */
	public function test_a_small_log_is_left_alone(): void {
		$directory = $this->content . '/' . ErrorRecorder::DIRECTORY;
		self::assertTrue( mkdir( $directory, 0755, true ) );
		file_put_contents( $directory . '/' . ErrorRecorder::FILE, 'a line' );

		ErrorRecorder::start( $this->content );

		$this->assertSame( 'a line', (string) file_get_contents( $directory . '/' . ErrorRecorder::FILE ) );
		$this->assertFileDoesNotExist( $directory . '/' . ErrorRecorder::PREVIOUS );
	}

	/**
	 * A wp-content that cannot be written leaves PHP exactly as it was: the
	 * recorder never makes the site's state worse.
	 */
	public function test_an_unwritable_content_directory_is_left_alone(): void {
		ini_set( 'error_log', '/dev/null' );

		ErrorRecorder::start( $this->content . '/' . str_repeat( 'nested/', 200 ) . 'deep' );

		$this->assertSame( '/dev/null', (string) ini_get( 'error_log' ) );
	}

	/**
	 * An ini value as it was before setUp ran.
	 *
	 * @param string $name Setting name.
	 */
	private function original( string $name ): string {
		$value = ini_get( $name );

		return is_string( $value ) ? $value : '';
	}

	/**
	 * Removes a directory with its files.
	 *
	 * @param string $directory Directory.
	 */
	private function remove( string $directory ): void {
		if ( ! is_dir( $directory ) ) {
			return;
		}
		foreach ( (array) scandir( $directory ) as $entry ) {
			if ( '.' === $entry || '..' === $entry ) {
				continue;
			}
			$path = $directory . '/' . $entry;
			is_dir( $path ) ? $this->remove( $path ) : unlink( $path );
		}
		rmdir( $directory );
	}
}

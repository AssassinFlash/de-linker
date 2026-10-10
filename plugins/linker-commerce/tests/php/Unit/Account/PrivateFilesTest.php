<?php
/**
 * Tests for customer documents out of the web server's reach.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for PrivateFiles, on a real temporary directory.
 *
 * @covers \Linker\Commerce\Account\PrivateFiles
 */
final class PrivateFilesTest extends TestCase {

	/**
	 * Uploads directory of the test.
	 *
	 * @var string
	 */
	private string $uploads;

	/**
	 * A temporary uploads directory and WordPress's file helpers.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->uploads = sys_get_temp_dir() . '/linker-files-' . bin2hex( random_bytes( 4 ) );
		mkdir( $this->uploads );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $this->uploads ) ) );
		WP_Mock::userFunction( 'wp_mkdir_p', array( 'return' => static fn ( string $dir ): bool => is_dir( $dir ) || mkdir( $dir, 0777, true ) ) );
		WP_Mock::userFunction( 'sanitize_file_name', array( 'return' => static fn ( string $name ): string => (string) preg_replace( '/[^A-Za-z0-9.\-]/', '', $name ) ) );
		WP_Mock::userFunction( 'wp_delete_file', array( 'return' => static fn ( string $file ): bool => unlink( $file ) ) );
	}

	/**
	 * Removes the temporary directory.
	 */
	public function tearDown(): void {
		$files = new \RecursiveIteratorIterator( new \RecursiveDirectoryIterator( $this->uploads, \FilesystemIterator::SKIP_DOTS ), \RecursiveIteratorIterator::CHILD_FIRST );
		foreach ( $files as $file ) {
			$file->isDir() ? rmdir( $file->getPathname() ) : unlink( $file->getPathname() );
		}
		rmdir( $this->uploads );
		parent::tearDown();
	}

	/**
	 * A file lands in its owner's directory under a name with a random part, behind a deny-all .htaccess.
	 */
	public function test_write_read_delete(): void {
		$files    = new PrivateFiles( 'proforma' );
		$relative = $files->write( 20, 'PI-2026-0001', '%PDF-1.7 test' );

		$this->assertMatchesRegularExpression( '#^20/PI-2026-0001-[0-9a-f]{16}\.pdf$#', $relative );
		$this->assertSame( '%PDF-1.7 test', file_get_contents( $files->path( $relative ) ) );
		$this->assertSame( "Require all denied\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n", file_get_contents( $this->uploads . '/proforma/.htaccess' ) );
		$this->assertFileExists( $this->uploads . '/proforma/index.html' );

		$files->delete( $relative );
		$this->assertSame( '', $files->path( $relative ) );
	}

	/**
	 * A path that climbs out of the directory, or an empty one, is no file.
	 */
	public function test_path_stays_inside(): void {
		$files = new PrivateFiles( 'proforma' );
		file_put_contents( $this->uploads . '/secret.txt', 'x' );

		$this->assertSame( '', $files->path( '../secret.txt' ) );
		$this->assertSame( '', $files->path( '' ) );
	}
}

<?php
/**
 * Tests for reading the engineering data files.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\EngineeringData;
use WP_Mock\Tools\TestCase;

/**
 * Tests for EngineeringData: the shipped files read, their versions, and a
 * broken file fails as absent (never as half-read).
 *
 * @covers \Linker\Commerce\Products\EngineeringData
 */
final class EngineeringDataTest extends TestCase {

	/**
	 * Both shipped files read as JSON objects.
	 */
	public function test_the_shipped_files_read(): void {
		$compatibility = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		$overlay       = EngineeringData::json( EngineeringData::OVERLAY_FILE );

		$this->assertIsArray( $compatibility );
		$this->assertSame( 1, $compatibility['schema_version'] );
		$this->assertIsArray( $overlay );
		$this->assertArrayHasKey( 'overlay', $overlay );
	}

	/**
	 * An empty current Woo set yields its own version without shipped pairs.
	 */
	public function test_the_compatibility_version_is_the_woo_projections_own(): void {
		\WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) );
		$manifest = array(
			'products'  => array(),
			'documents' => array(),
		);
		$version  = EngineeringData::compatibility_version( $manifest );
		$data     = EngineeringData::compatibility( $manifest );

		$this->assertIsArray( $data );
		$this->assertSame( $data['version'], $version );
		$this->assertSame( array(), $data['pairs'] );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{64}$/', $version );
	}

	/**
	 * A broken file fails as absent: unreadable, not JSON, or not an object
	 * all read as null.
	 */
	public function test_a_broken_file_reads_as_null(): void {
		$directory = sys_get_temp_dir() . '/linker-engineering-data-' . uniqid();
		mkdir( $directory ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_mkdir -- a test fixture directory outside WordPress.
		$broken = $directory . '/broken.json';
		$a_list = $directory . '/list.json';
		file_put_contents( $broken, '{"pairs": [' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a test fixture outside the repository.
		file_put_contents( $a_list, '[1, 2]' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a test fixture outside the repository.

		$this->assertNull( EngineeringData::json_from( $broken ) );
		$this->assertNull( EngineeringData::json_from( $a_list ) );
		$this->assertNull( EngineeringData::json_from( $directory . '/absent.json' ) );

		unlink( $broken ); // phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- a test fixture outside WordPress.
		unlink( $a_list ); // phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- a test fixture outside WordPress.
		rmdir( $directory ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_rmdir -- a test fixture directory outside WordPress.
	}
}

<?php
/**
 * Account navigation reads the current native owner's project index.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\AccountProjects;
use Linker\Tools\Planner\Transport;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Current account identity and transport failures remain distinct.
 *
 * @covers \Linker\Tools\Planner\AccountProjects
 */
final class AccountProjectsTest extends TestCase {

	/**
	 * Owner is server derived; a failed/malformed read never becomes an empty list.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_native_owner_read_and_failure_are_distinct_from_no_projects(): void {
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'unit-test-only' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Existing native service constant; a synthetic unit-test value only.
		}
		$user  = 66;
		$items = array(
			array(
				'id'         => str_repeat( 'a', 32 ),
				'title'      => 'Owned project',
				'updated_at' => 1793040000,
			),
		);
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => static function () use ( &$user ): int {
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'get_current_blog_id', array( 'return' => 1 ) );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $message ): string => $message ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'https://engine.test/planning' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value ): string|false => json_encode( $value ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- This is the native encoder's unit double.
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( mixed $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => 200 ) );
		WP_Mock::userFunction(
			'wp_remote_retrieve_body',
			array(
				'return' => static function () use ( &$items ): string {
					return (string) wp_json_encode( array( 'items' => $items ) );
				},
			)
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_header', array( 'return' => 'application/json' ) );
		$calls   = 0;
		$adapter = new AccountProjects(
			new Transport(
				function ( string $url, array $args ) use ( &$calls ): array {
					++$calls;
					$this->assertSame( 'https://engine.test/planning/projects/list', $url );
					$this->assertSame( 'user', $args['headers']['X-Linker-Planner-Principal-Kind'] );
					$this->assertSame( 'wp:1:user:66', $args['headers']['X-Linker-Planner-Principal-Subject'] );
					$this->assertSame(
						array(
							'schema_version' => 1,
							'page_size'      => 10,
							'after'          => null,
						),
						json_decode( $args['body'], true )
					);
					return array();
				}
			)
		);
		$this->assertSame( $items, $adapter->read( null ) );
		$items = array();
		$this->assertSame( array(), $adapter->read( null ) );
		$items = array( array( 'id' => '../other-project' ) );
		$this->assertInstanceOf( WP_Error::class, $adapter->read( null ) );
		$items = array(
			array(
				'id'         => str_repeat( 'a', 32 ),
				'title'      => '',
				'updated_at' => 1793040000,
			),
		);
		$this->assertInstanceOf( WP_Error::class, $adapter->read( null ) );
		$user = 0;
		$this->assertInstanceOf( WP_Error::class, $adapter->read( null ) );
		$this->assertSame( 4, $calls, 'The guest does not contact the engine.' );
	}
}

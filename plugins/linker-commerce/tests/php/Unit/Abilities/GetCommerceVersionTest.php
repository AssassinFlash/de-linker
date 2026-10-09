<?php
/**
 * Tests for the linker/get-commerce-version ability.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\GetCommerceVersion;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for GetCommerceVersion.
 *
 * @covers \Linker\Commerce\Abilities\GetCommerceVersion
 */
final class GetCommerceVersionTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * Translation calls return their source string.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * The ability is read-only, takes no input and is exposed to REST.
	 */
	public function test_args_describe_a_read_only_rest_ability(): void {
		$ability = new GetCommerceVersion( self::FILE );
		$args    = $ability->args();

		$this->assertSame( 'Get Linker Commerce version', $args['label'] );
		$this->assertSame( array( $ability, 'execute' ), $args['execute_callback'] );
		$this->assertSame( array( $ability, 'can_execute' ), $args['permission_callback'] );
		$this->assertSame(
			array(
				'annotations'  => array(
					'readonly'    => true,
					'destructive' => false,
					'idempotent'  => true,
				),
				'show_in_rest' => true,
			),
			$args['meta']
		);
		$this->assertArrayNotHasKey( 'input_schema', $args );
	}

	/**
	 * The output schema describes exactly what execute() returns.
	 */
	public function test_output_schema_matches_the_result(): void {
		WP_Mock::userFunction(
			'get_file_data',
			array(
				'args'   => array( self::FILE, array( 'version' => 'Version' ) ),
				'return' => array( 'version' => '0.1.0' ),
			)
		);
		$ability = new GetCommerceVersion( self::FILE );
		$schema  = $ability->args()['output_schema'];
		$result  = $ability->execute();

		$this->assertSame( array( 'version' => '0.1.0' ), $result );
		$this->assertSame( 'object', $schema['type'] );
		$this->assertSame( array_keys( $result ), array_keys( $schema['properties'] ) );
		$this->assertSame( array_keys( $result ), $schema['required'] );
		$this->assertFalse( $schema['additionalProperties'] );
	}

	/**
	 * Only users who can manage options may run the ability.
	 *
	 * @testWith [true]
	 *           [false]
	 *
	 * @param bool $can_manage_options Whether the current user has manage_options.
	 */
	public function test_permission_follows_manage_options( bool $can_manage_options ): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => $can_manage_options,
			)
		);

		$this->assertSame( $can_manage_options, ( new GetCommerceVersion( self::FILE ) )->can_execute() );
	}
}

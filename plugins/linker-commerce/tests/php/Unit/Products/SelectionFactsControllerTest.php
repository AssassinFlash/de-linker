<?php
/**
 * Tests for the REST route of the selection facts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Products\SelectionFactsController;
use Linker\Commerce\Tests\Support\MocksProducts;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;

/**
 * Tests for SelectionFactsController without WordPress. Its HTTP behaviour on a
 * real site (anonymous answers, the 400 for 101 IDs, unpublished products left
 * out, the OPTIONS schema) is SelectionFactsRestTest in tests/php/Integration.
 *
 * @covers \Linker\Commerce\Products\SelectionFactsController
 * @covers \Linker\Commerce\Products\SelectionFactSet::schema
 */
final class SelectionFactsControllerTest extends TestCase {

	use MocksProducts;

	/**
	 * The route is a public GET of 1 to 100 positive product IDs, with its schema.
	 */
	public function test_registers_a_public_route_for_up_to_100_ids(): void {
		WP_Mock::passthruFunction( '__' );
		$controller = new SelectionFactsController();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times' => 1,
				'args'  => array(
					'linker/v1',
					'/selection-facts',
					array(
						array(
							'methods'             => 'GET',
							'callback'            => array( $controller, 'get_items' ),
							'permission_callback' => array( $controller, 'get_items_permissions_check' ),
							'args'                => array(
								'ids' => array(
									'description' => 'Product IDs, at most 100.',
									'type'        => 'array',
									'items'       => array(
										'type'    => 'integer',
										'minimum' => 1,
									),
									'maxItems'    => 100,
									'required'    => true,
								),
							),
						),
						'schema' => array( $controller, 'get_public_item_schema' ),
					),
				),
			)
		);

		$controller->register_routes();

		$this->assertConditionsMet();
	}

	/**
	 * The schema is an object of SelectionFactSet schemas: what OPTIONS shows.
	 */
	public function test_schema_maps_ids_to_fact_sets(): void {
		WP_Mock::passthruFunction( '__' );
		$schema = ( new SelectionFactsController() )->get_public_item_schema();

		$this->assertSame( 'selection-facts', $schema['title'] );
		$this->assertSame( 'object', $schema['type'] );
		$this->assertSame( SelectionFactSet::schema(), $schema['additionalProperties'] );
	}

	/**
	 * Only published products are answered, once each.
	 */
	public function test_returns_only_the_published_products(): void {
		$this->mock_post( 6480, 'product', 'publish' );
		$this->mock_post( 3555, 'product', 'publish' );
		$this->mock_post( 7001, 'product', 'draft' );
		$this->mock_post( 42, 'page', 'publish' );
		$this->mock_post( 999999, false, false );
		WP_Mock::userFunction(
			'_prime_post_caches',
			array(
				'times' => 1,
				'args'  => array( array( 6480, 7001, 42, 3555, 999999 ) ),
			)
		);
		$this->mock_product( 6480, array( 449 => 'inverters' ), array(), array(), '' );
		$this->mock_product( 3555, array( 449 => 'inverters' ), array( 'home' ), array( 'three-phase' ), '' );

		$facts = ( new SelectionFactsController() )->get_items( self::request( array( 6480, 7001, 42, 3555, 6480, 999999 ) ) );

		$this->assertEqualsCanonicalizing( array( 3555, 6480 ), array_keys( (array) $facts ) );
		$this->assertSame( 'home', ( (array) $facts )[3555]['application'] );
		$this->assertSame( 'unknown', ( (array) $facts )[6480]['application'] );
	}

	/**
	 * Without a published product the answer is an empty JSON object, not a list.
	 */
	public function test_an_empty_answer_is_an_object(): void {
		$this->mock_post( 7001, 'product', 'draft' );
		WP_Mock::userFunction( '_prime_post_caches' );

		$facts = ( new SelectionFactsController() )->get_items( self::request( array( 7001 ) ) );

		// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WordPress is not loaded in unit tests.
		$this->assertSame( '{}', json_encode( $facts ) );
	}

	/**
	 * Mocks the post type and status of one ID.
	 *
	 * @param int          $id     Post ID.
	 * @param string|false $type   Post type, false when there is no post.
	 * @param string|false $status Post status, false when there is no post.
	 */
	private function mock_post( int $id, string|false $type, string|false $status ): void {
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( $id ),
				'return' => $type,
			)
		);
		WP_Mock::userFunction(
			'get_post_status',
			array(
				'args'   => array( $id ),
				'return' => $status,
			)
		);
	}

	/**
	 * A request whose validated ids parameter holds the given IDs.
	 *
	 * @param int[] $ids Product IDs.
	 * @return WP_REST_Request<array<string, mixed>>
	 */
	private static function request( array $ids ): WP_REST_Request {
		$request = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_param' )->with( 'ids' )->andReturns( $ids );

		return $request;
	}
}

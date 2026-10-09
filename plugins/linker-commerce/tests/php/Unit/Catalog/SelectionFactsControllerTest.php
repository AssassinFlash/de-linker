<?php
/**
 * Tests for the REST route of the selection facts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\SelectionFactsController;
use Linker\Commerce\Tests\Support\MocksProducts;
use LogicException;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;

/**
 * Tests for SelectionFactsController. The HTTP behaviour (anonymous 200, the
 * 400 for 101 IDs) is WordPress's handling of these arguments, checked on a
 * local WordPress in the pull request.
 *
 * @covers \Linker\Commerce\Catalog\SelectionFactsController
 */
final class SelectionFactsControllerTest extends TestCase {

	use MocksProducts;

	/**
	 * The route is a public GET whose ids are 1 to 100 positive integers.
	 */
	public function test_registers_a_public_route_for_up_to_100_ids(): void {
		$controller = new SelectionFactsController();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times' => 1,
				'args'  => array(
					'linker/v1',
					'/selection-facts',
					array(
						'methods'             => 'GET',
						'callback'            => array( $controller, 'get_items' ),
						'permission_callback' => '__return_true',
						'args'                => array(
							'ids' => array(
								'type'     => 'array',
								'items'    => array(
									'type'    => 'integer',
									'minimum' => 1,
								),
								'maxItems' => 100,
								'required' => true,
							),
						),
					),
				),
			)
		);

		$controller->register_routes();

		$this->assertConditionsMet();
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
	 * @throws LogicException When the mock is not a WP_REST_Request.
	 */
	private static function request( array $ids ): WP_REST_Request {
		$request = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_param' )->with( 'ids' )->andReturns( $ids );
		if ( ! $request instanceof WP_REST_Request ) {
			throw new LogicException( 'Mockery did not extend WP_REST_Request.' );
		}

		return $request;
	}
}

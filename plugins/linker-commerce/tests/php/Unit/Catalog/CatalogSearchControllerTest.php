<?php
/**
 * Tests for the catalogue search route.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\CatalogSearch;
use Linker\Commerce\Catalog\CatalogSearchController;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_REST_Request;

/**
 * Tests for CatalogSearchController without WordPress: the route's shape and
 * the answer's items. Its behaviour over HTTP on a real site is
 * CatalogSearchRestTest in tests/php/Integration.
 *
 * @covers \Linker\Commerce\Catalog\CatalogSearchController
 */
final class CatalogSearchControllerTest extends TestCase {


	/**
	 * The route is a public GET of a query of at least two characters, a
	 * bounded limit and a language, with its schema.
	 */
	public function test_registers_a_public_route(): void {
		$this->plain_text();
		$controller = new CatalogSearchController();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times' => 1,
				'args'  => array(
					'linker/v1',
					'/catalog-search',
					array(
						array(
							'methods'             => 'GET',
							'callback'            => array( $controller, 'get_items' ),
							'permission_callback' => array( $controller, 'get_items_permissions_check' ),
							'args'                => array(
								'q'     => array(
									'description' => 'A model or item number.',
									'type'        => 'string',
									'required'    => true,
									'minLength'   => 2,
								),
								'limit' => array(
									'description' => 'Most products to answer with, at most 12.',
									'type'        => 'integer',
									'minimum'     => 1,
									'maximum'     => 12,
									'default'     => 8,
								),
								'lang'  => array(
									'description' => 'Language of the products and their addresses.',
									'type'        => 'string',
									'enum'        => array( 'en', 'de' ),
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
	 * The answer holds one item per hit, in shop order.
	 */
	public function test_answer_lists_the_hits(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 12, 11 ) ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'http://site/product/x/' ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ): \WC_Product {
					$product = \Mockery::mock( \WC_Product::class );
					$product->allows( 'get_name' )->andReturn( 'GoodWe ' . $id );
					$product->allows( 'get_sku' )->andReturn( 'SKU-' . $id );
					return $product;
				},
			)
		);
		$this->mock_facts( 12 );
		$this->mock_facts( 11 );

		$request = new WP_REST_Request();
		$request->set_param( 'q', 'GoodWe' );
		$request->set_param( 'limit', 8 );

		/** The answer's body, as the REST route returns it.
		 *
		 * @var array{query: string, items: list<array<string, mixed>>} $answer
		 */
		$answer = (array) ( new CatalogSearchController() )->get_items( $request );

		$this->assertSame( 'GoodWe', $answer['query'] );
		$this->assertCount( 2, $answer['items'] );
		$this->assertSame( 12, $answer['items'][0]['id'] );
		$this->assertSame( 'SKU-12', $answer['items'][0]['sku'] );
		$this->assertArrayHasKey( 'facts', $answer['items'][0] );
		$this->assertConditionsMet();
	}

	/**
	 * SelectionFacts for one product, as the catalogue tests mock it: no
	 * categories, no figures — every fact unknown.
	 *
	 * @param int $id Product ID.
	 */
	private function mock_facts( int $id ): void {
		WP_Mock::userFunction( 'has_filter', array( 'return' => 1 ) );
		// The @var narrows WP_Mock's union of responder doc types to the Filter responder its code defines.
		/**
	* The filter responder WP_Mock's with() returns.
		 *
		 * @var \WP_Mock\Filter_Responder $responder
		 */
		$responder = WP_Mock::onFilter( 'linker_commerce_facts_product_id' )->with( $id );
		$responder->reply( $id );
		WP_Mock::userFunction( 'get_the_terms', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
	}
}

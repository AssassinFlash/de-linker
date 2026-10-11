<?php
/**
 * Tests for the stock push route.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\BatchLog;
use Linker\Commerce\Stock\PushKey;
use Linker\Commerce\Stock\StockController;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Error;
use WP_Mock;
use WP_REST_Request;

/**
 * Tests for StockController.
 *
 * @covers \Linker\Commerce\Stock\StockController
 */
final class StockControllerTest extends TestCase {

	private const KEY = 'the-erp-push-key';

	/**
	 * The hash the site currently stores; '' for none.
	 *
	 * @var string
	 */
	private string $stored = '';

	/**
	 * A stored push key.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->stored = hash( 'sha256', self::KEY );
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( PushKey::OPTION, '' ),
				'return' => fn (): string => $this->stored,
			)
		);
	}

	/**
	 * The route registers as POST under linker/v1 with its schema.
	 */
	public function test_registers_the_post_route(): void {
		$controller = new StockController( new BatchLog() );
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times' => 1,
				'args'  => array(
					'linker/v1',
					'/stock',
					Mockery::on(
						static function ( array $routes ) use ( $controller ): bool {
							$route = $routes[0];
							return 'POST' === $route['methods']
							&& array( $controller, 'push' ) === $route['callback']
							&& array( $controller, 'push_permissions_check' ) === $route['permission_callback']
							&& isset( $route['args']['items'] );
						}
					),
				),
			)
		);

		$controller->register_routes();
		$this->assertConditionsMet();
	}

	/**
	 * Only the holder of the push key pushes; anything else is a 401.
	 */
	public function test_permission_needs_the_push_key(): void {
		$controller = new StockController( new BatchLog() );

		$no_header = $controller->push_permissions_check( $this->request( null ) );
		$wrong_key = $controller->push_permissions_check( $this->request( 'another-key' ) );
		$allowed   = $controller->push_permissions_check( $this->request( self::KEY ) );

		$this->assertInstanceOf( WP_Error::class, $no_header );
		$this->assertSame( 401, $no_header->get_error_data()['status'] );
		$this->assertSame( 'linker_stock_unauthorized', $no_header->get_error_code() );
		$this->assertInstanceOf( WP_Error::class, $wrong_key );
		$this->assertSame( 401, $wrong_key->get_error_data()['status'] );
		$this->assertTrue( $allowed );
	}

	/**
	 * A request without a key still fails when no key is stored: the route
	 * rejects everything until a key is set.
	 */
	public function test_permission_fails_without_any_stored_key(): void {
		$this->stored = '';
		$controller   = new StockController( new BatchLog() );

		$answer = $controller->push_permissions_check( $this->request( 'the-erp-push-key' ) );

		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( 401, $answer->get_error_data()['status'] );
	}

	/**
	 * A batch without items is a 400, before anything is applied or audited.
	 */
	public function test_push_without_items_is_a_400(): void {
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		$controller = new StockController( new BatchLog() );
		$request    = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_header' )->andReturn( self::KEY );
		$request->allows( 'get_param' )->with( 'items' )->andReturn( array() );

		$answer = $controller->push( $request );

		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( 400, $answer->get_error_data()['status'] );
		$this->assertSame( 'linker_stock_no_items', $answer->get_error_code() );
	}

	/**
	 * A batch applies row by row and leaves one audit row; the answer carries
	 * the rows and the audit row's id.
	 */
	public function test_push_applies_and_audits(): void {
		WP_Mock::userFunction(
			'wc_get_product_id_by_sku',
			array(
				'times'  => 1,
				'return' => 41,
			)
		);
		$product = Mockery::mock( \WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 41 );
		$product->allows( 'managing_stock' )->andReturn( true );
		$product->allows( 'get_stock_quantity' )->andReturn( 2 );
		$product->allows( 'get_stock_status' )->andReturn( 'instock' );
		$product->allows( 'set_stock_quantity' );
		$product->allows( 'validate_props' );
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => $product ) );
		WP_Mock::userFunction(
			'wc_update_product_stock',
			array(
				'times' => 1,
			)
		);
		WP_Mock::userFunction(
			'current_time',
			array(
				'args'   => array( 'mysql', true ),
				'return' => '2026-10-11 08:00:00',
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => 55,
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times' => 1,
			)
		);
		WP_Mock::userFunction(
			'rest_ensure_response',
			array(
				'return' => static fn ( array $data ): \WP_REST_Response => new \WP_REST_Response( $data ),
			)
		);

		$controller = new StockController( new BatchLog() );
		$request    = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_header' )->andReturn( self::KEY );
		$request->allows( 'get_param' )->with( 'items' )->andReturn(
			array(
				array(
					'sku' => 'A-SKU',
					'qty' => 5,
				),
			)
		);

		$answer = $controller->push( $request );

		$this->assertInstanceOf( \WP_REST_Response::class, $answer );
		$data = $answer->get_data();
		$this->assertIsArray( $data );
		$this->assertSame( 55, $data['batch'] );
		$this->assertSame( 1, $data['applied'] );
		$this->assertSame( 'applied', $data['results'][0]['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * When the audit row cannot be written the push fails loudly (500): the
	 * contract is one audit row per accepted batch.
	 */
	public function test_push_fails_when_the_audit_row_cannot_be_written(): void {
		WP_Mock::userFunction(
			'wc_get_product_id_by_sku',
			array(
				'times'  => 1,
				'return' => 41,
			)
		);
		$product = Mockery::mock( \WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 41 );
		$product->allows( 'managing_stock' )->andReturn( true );
		$product->allows( 'get_stock_quantity' )->andReturn( 2 );
		$product->allows( 'get_stock_status' )->andReturn( 'instock' );
		$product->allows( 'set_stock_quantity' );
		$product->allows( 'validate_props' );
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => $product ) );
		WP_Mock::userFunction( 'wc_update_product_stock' );
		WP_Mock::userFunction( 'current_time', array( 'return' => '2026-10-11 08:00:00' ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => new WP_Error( 'db', 'no' ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );

		$controller = new StockController( new BatchLog() );
		$request    = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_header' )->andReturn( self::KEY );
		$request->allows( 'get_param' )->with( 'items' )->andReturn(
			array(
				array(
					'sku' => 'A-SKU',
					'qty' => 5,
				),
			)
		);

		$answer = $controller->push( $request );

		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( 'linker_stock_audit_failed', $answer->get_error_code() );
		$this->assertSame( 500, $answer->get_error_data()['status'] );
	}

	/**
	 * The schema names the row statuses and error codes.
	 */
	public function test_schema(): void {
		$schema = ( new StockController( new BatchLog() ) )->get_item_schema();

		$this->assertSame( 'stock-push', $schema['title'] );
		$results = $schema['properties']['results']['items']['properties'];
		$this->assertSame( array( 'applied', 'unchanged', 'error' ), $results['status']['enum'] );
		$this->assertArrayHasKey( 'code', $results );
	}

	/**
	 * A request double: the push key header carrying the given key (null: no
	 * header at all).
	 *
	 * @param string|null $sent The key the request sent.
	 * @return WP_REST_Request
	 */
	private function request( ?string $sent ): WP_REST_Request {
		$request = Mockery::mock( WP_REST_Request::class );
		$request->allows( 'get_header' )
			->with( PushKey::HEADER )
			->andReturn( $sent );
		return $request;
	}
}

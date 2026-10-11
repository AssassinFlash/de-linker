<?php
/**
 * Tests for the applied stock batches.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\Batch;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use Mockery\MockInterface;
use WC_Product;
use WP_Mock;

/**
 * Tests for Batch: rows answer in order, errors stay per row, an equal
 * push is a no-op.
 *
 * @covers \Linker\Commerce\Stock\Batch
 */
final class BatchTest extends TestCase {

	/**
	 * A product with managed stock, as WooCommerce answers wc_get_product().
	 *
	 * @param int      $id     Product ID.
	 * @param int|null $qty    Stock quantity.
	 * @param string   $status Stock status.
	 */
	private function product( int $id, ?int $qty, string $status ): WC_Product&MockInterface {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( $id );
		$product->allows( 'managing_stock' )->andReturn( true );
		$product->allows( 'get_stock_quantity' )->andReturn( $qty );
		$product->allows( 'get_stock_status' )->andReturn( $status );
		return $product;
	}

	/**
	 * Mocks the WooCommerce reads for one SKU-bound product: apply_row reads
	 * the current product, then (for a quantity without explicit state) the
	 * throwaway probe, then the product as it reads after the writes.
	 *
	 * @param WC_Product  $current       The product as it is now.
	 * @param WC_Product  $after         The product read back after the writes.
	 * @param WC_Product  $probe         The throwaway copy of the unchanged check (null: the row carries an explicit state).
	 * @param int|null    $written_qty   What wc_update_product_stock() is asked for (null: never called).
	 * @param string|null $set_status    What wc_update_product_stock_status() is asked for (null: never called).
	 * @param int|null    $product_id    The ID wc_get_product_id_by_sku() answers (null: the caller registers it).
	 */
	private function bind_sku(
		WC_Product $current,
		WC_Product $after,
		?WC_Product $probe = null,
		?int $written_qty = null,
		?string $set_status = null,
		?int $product_id = 41
	): void {
		if ( null !== $product_id ) {
			WP_Mock::userFunction(
				'wc_get_product_id_by_sku',
				array(
					'times'  => '0+',
					'return' => $product_id,
				)
			);
		}
		$loads = array( $current );
		if ( null !== $probe ) {
			$loads[] = $probe;
		}
		$loads[] = $after;
		$index   = 0;
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'times'  => '0+',
				'return' => static function () use ( &$index, $loads ): WC_Product {
					return $loads[ $index++ ];
				},
			)
		);
		WP_Mock::userFunction(
			'wc_update_product_stock',
			array(
				'times' => null === $written_qty ? 0 : 1,
			)
		);
		WP_Mock::userFunction(
			'wc_update_product_stock_status',
			array(
				'times' => null === $set_status ? 0 : 1,
			)
		);
	}

	/**
	 * Rows that do not parse are error rows of their own, in request order.
	 */
	public function test_broken_rows_error_individually(): void {
		$result = Batch::apply(
			array(
				'not-an-array',
				array( 'qty' => 5 ),
				array(
					'sku' => 'X',
					'qty' => '5',
				),
				array(
					'sku' => 'X',
					'qty' => -1,
				),
				array(
					'sku'   => 'X',
					'state' => 'onbackorder',
				),
				array( 'sku' => 'X' ),
			)
		);

		$this->assertSame(
			array( 'invalid_item', 'invalid_sku', 'invalid_qty', 'invalid_qty', 'invalid_state', 'missing_target' ),
			array_column( $result['results'], 'code' )
		);
		$this->assertSame( 0, $result['applied'] );
		$this->assertSame( 6, $result['errors'] );
	}

	/**
	 * An unknown SKU is an error row; a good SKU in the same batch still applies.
	 */
	public function test_unknown_sku_errors_without_rolling_the_batch_back(): void {
		$product = $this->product( 41, 3, 'instock' );
		$probe   = $this->product( 41, 3, 'instock' );
		$probe->allows( 'set_stock_quantity' )->with( 7 );
		$probe->allows( 'validate_props' );
		$after = $this->product( 41, 7, 'instock' );
		$this->bind_sku( $product, $after, $probe, 7, null, null );
		WP_Mock::userFunction(
			'wc_get_product_id_by_sku',
			array(
				'times'  => '0+',
				'return' => static fn ( string $sku ): ?int => 'GOOD-SKU' === $sku ? 41 : null,
			)
		);

		$result = Batch::apply(
			array(
				array(
					'sku' => 'GOOD-SKU',
					'qty' => 7,
				),
				array(
					'sku' => 'MISSING-SKU',
					'qty' => 2,
				),
			)
		);

		$this->assertSame( 'applied', $result['results'][0]['status'] );
		$this->assertSame( 'unknown_sku', $result['results'][1]['code'] );
		$this->assertSame( 7, $result['results'][0]['qty'] );
		$this->assertSame( 1, $result['applied'] );
		$this->assertSame( 1, $result['errors'] );
	}

	/**
	 * A quantity for a product that does not manage stock is refused per row;
	 * a state-only push to the same product works.
	 */
	public function test_quantity_needs_managed_stock(): void {
		$unmanaged = Mockery::mock( WC_Product::class );
		$unmanaged->allows( 'get_id' )->andReturn( 9 );
		$unmanaged->allows( 'managing_stock' )->andReturn( false );
		$unmanaged->allows( 'get_stock_status' )->andReturn( 'instock' );
		$unmanaged->allows( 'get_stock_quantity' )->andReturn( null );
		WP_Mock::userFunction( 'wc_get_product_id_by_sku', array( 'return' => 9 ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'times'  => '0+',
				'return' => static fn (): WC_Product => $unmanaged,
			)
		);
		WP_Mock::userFunction( 'wc_update_product_stock', array( 'times' => 0 ) );
		WP_Mock::userFunction(
			'wc_update_product_stock_status',
			array(
				'times' => 1,
				'args'  => array( 9, 'outofstock' ),
			)
		);

		$result = Batch::apply(
			array(
				array(
					'sku' => 'UNMANAGED',
					'qty' => 5,
				),
				array(
					'sku'   => 'UNMANAGED',
					'state' => 'outofstock',
				),
			)
		);

		$this->assertSame( 'not_stock_managed', $result['results'][0]['code'] );
		$this->assertSame( 'applied', $result['results'][1]['status'] );
	}

	/**
	 * Pushing the values already in place is a no-op row: nothing is written.
	 */
	public function test_equal_push_is_unchanged_and_writes_nothing(): void {
		$product = $this->product( 41, 5, 'instock' );
		$probe   = $this->product( 41, 5, 'instock' );
		$probe->allows( 'set_stock_quantity' )->with( 5 );
		$probe->allows( 'validate_props' );
		$this->bind_sku( $product, $product, $probe );

		$result = Batch::apply(
			array(
				array(
					'sku' => 'A-SKU',
					'qty' => 5,
				),
			)
		);

		$this->assertSame( 'unchanged', $result['results'][0]['status'] );
		$this->assertSame( 5, $result['results'][0]['qty'] );
		$this->assertSame( 'instock', $result['results'][0]['stock_status'] );
		$this->assertSame( 1, $result['unchanged'] );
		$this->assertSame( 0, $result['applied'] );
		$this->assertConditionsMet();
	}

	/**
	 * A changed quantity is written through wc_update_product_stock and read
	 * back; a zero quantity also turns the status (WooCommerce's own
	 * alignment, seen through validate_props on the probe).
	 */
	public function test_changed_quantity_applies_and_syncs_the_status(): void {
		$product = $this->product( 41, 5, 'instock' );
		$probe   = $this->product( 41, 0, 'outofstock' );
		$probe->allows( 'set_stock_quantity' )->with( 0 );
		$probe->allows( 'validate_props' );
		$after = $this->product( 41, 0, 'outofstock' );
		$this->bind_sku( $product, $after, $probe, 0 );

		$result = Batch::apply(
			array(
				array(
					'sku' => 'A-SKU',
					'qty' => 0,
				),
			)
		);

		$this->assertSame( 'applied', $result['results'][0]['status'] );
		$this->assertSame( 0, $result['results'][0]['qty'] );
		$this->assertSame( 'outofstock', $result['results'][0]['stock_status'] );
		$this->assertConditionsMet();
	}

	/**
	 * WooCommerce's own rule: a product that manages stock carries the
	 * status its quantity derives. A state that contradicts it is a per-row
	 * error, never a silent no-op — the ERP pulling a product the shop
	 * would still list is the failure this channel must not make.
	 */
	public function test_state_on_managed_product_must_match_the_derived_status(): void {
		$product = $this->product( 41, 5, 'instock' );
		$probe   = $this->product( 41, 5, 'instock' );
		$probe->allows( 'set_stock_quantity' );
		$probe->allows( 'validate_props' );
		$this->bind_sku( $product, $product, $probe, null, null );

		$result = Batch::apply(
			array(
				array(
					'sku'   => 'A-SKU',
					'state' => 'outofstock',
				),
			)
		);

		$this->assertSame( 'error', $result['results'][0]['status'] );
		$this->assertSame( 'state_overridden', $result['results'][0]['code'] );
		$this->assertConditionsMet();
	}

	/**
	 * A state that only confirms what the quantity derives is a no-op row.
	 */
	public function test_state_matching_the_derivation_is_unchanged(): void {
		$product = $this->product( 41, 5, 'instock' );
		$probe   = $this->product( 41, 5, 'instock' );
		$probe->allows( 'set_stock_quantity' );
		$probe->allows( 'validate_props' );
		$this->bind_sku( $product, $product, $probe );

		$result = Batch::apply(
			array(
				array(
					'sku'   => 'A-SKU',
					'qty'   => 5,
					'state' => 'instock',
				),
			)
		);

		$this->assertSame( 'unchanged', $result['results'][0]['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * On a product without managed stock the state is the word: it applies.
	 */
	public function test_state_applies_on_a_product_without_managed_stock(): void {
		$unmanaged = Mockery::mock( WC_Product::class );
		$unmanaged->allows( 'get_id' )->andReturn( 9 );
		$unmanaged->allows( 'managing_stock' )->andReturn( false );
		$unmanaged->allows( 'get_stock_status' )->andReturn( 'instock' );
		$unmanaged->allows( 'get_stock_quantity' )->andReturn( null );
		$after = Mockery::mock( WC_Product::class );
		$after->allows( 'get_stock_quantity' )->andReturn( null );
		$after->allows( 'get_stock_status' )->andReturn( 'outofstock' );
		WP_Mock::userFunction( 'wc_get_product_id_by_sku', array( 'return' => 9 ) );
		$loads = array( $unmanaged, $after );
		$index = 0;
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'times'  => '0+',
				'return' => static function () use ( &$index, $loads ): WC_Product {
					return $loads[ $index++ ];
				},
			)
		);
		WP_Mock::userFunction( 'wc_update_product_stock', array( 'times' => 0 ) );
		WP_Mock::userFunction(
			'wc_update_product_stock_status',
			array(
				'times' => 1,
				'args'  => array( 9, 'outofstock' ),
			)
		);

		$result = Batch::apply(
			array(
				array(
					'sku'   => 'UNMANAGED',
					'state' => 'outofstock',
				),
			)
		);

		$this->assertSame( 'applied', $result['results'][0]['status'] );
		$this->assertSame( 'outofstock', $result['results'][0]['stock_status'] );
		$this->assertConditionsMet();
	}
}

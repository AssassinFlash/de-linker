<?php
/**
 * The stock push channel in a real WooCommerce.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Stock\BatchLog;
use Linker\Commerce\Stock\PushKey;
use Linker\Commerce\Stock\Retention;
use WC_Product_Simple;
use WP_REST_Request;
use WP_REST_Server;

/**
 * A pushed batch lands on WooCommerce's own stock: the quantity and the
 * status the storefront and the inquiry chain read. Real products, a real
 * REST round trip and real audit rows; the key is a real option.
 *
 * @coversNothing
 */
final class StockTest extends IntegrationTestCase {

	/**
	 * The audit rows' post type.
	 *
	 * @var BatchLog
	 */
	private BatchLog $log;

	/**
	 * The key this test set, removed again afterwards.
	 *
	 * @var string
	 */
	private string $key = '';

	/**
	 * Sets the test's push key and the audit reader.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->log = new BatchLog();
		$this->key = 'integration-push-' . self::tag();
		PushKey::set( $this->key );
		$this->later( static fn () => PushKey::clear() );
	}

	/**
	 * A published simple product with managed stock and a SKU.
	 *
	 * @param int $qty The stock quantity the product starts with.
	 */
	private function skued_product( int $qty ): WC_Product_Simple {
		$product = $this->product( '1480' );
		$sku     = 'IT-' . self::tag();
		$product->set_sku( $sku );
		$product->set_manage_stock( true );
		$product->set_stock_quantity( $qty );
		$product->save();
		return $product;
	}

	/**
	 * The endpoint's answer to a push.
	 *
	 * @param mixed[]           $items The pushed rows.
	 * @param string|false|null $key   The key to send; null sends the test's key, false sends no header.
	 * @return array{status: int, body: mixed}
	 */
	private function push( array $items, $key = null ): array {
		$request = new WP_REST_Request( WP_REST_Server::CREATABLE, '/linker/v1/stock' );
		$request->set_param( 'items', $items );
		$sent = false === $key ? null : ( $key ?? $this->key );
		if ( null !== $sent ) {
			$request->add_header( PushKey::HEADER, $sent );
		}
		$response = rest_do_request( $request );
		return array(
			'status' => $response->get_status(),
			'body'   => $response->get_data(),
		);
	}

	/**
	 * The rows of the product as the storefront reads them.
	 *
	 * @param WC_Product_Simple $product The product.
	 * @return array{qty: int|null, status: string}
	 */
	private function stock_of( WC_Product_Simple $product ): array {
		$fresh = wc_get_product( $product->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $fresh );
		return array(
			'qty'    => $fresh->get_stock_quantity(),
			'status' => (string) $fresh->get_stock_status(),
		);
	}

	/**
	 * A batch applies row by row and leaves one audit row with what was
	 * asked and what each SKU got.
	 */
	public function test_batch_applies_and_audits(): void {
		$first  = $this->skued_product( 10 );
		$second = $this->skued_product( 10 );

		$answer = $this->push(
			array(
				array(
					'sku' => $first->get_sku(),
					'qty' => 4,
				),
				array(
					'sku' => $second->get_sku(),
					'qty' => 0,
				),
			)
		);

		$this->assertSame( 200, $answer['status'] );
		$body = $answer['body'];
		$this->assertIsArray( $body );
		$this->assertSame( 2, $body['applied'] );
		$this->assertSame( 0, $body['errors'] );
		$this->assertSame( 'applied', $body['results'][0]['status'] );
		$this->assertSame( 4, $this->stock_of( $first )['qty'] );
		// A zero quantity is out of stock by WooCommerce's own alignment.
		$this->assertSame( 'outofstock', $this->stock_of( $second )['status'] );

		// One audit row carries the batch.
		$rows = get_posts(
			array(
				'post_type'      => BatchLog::POST_TYPE,
				'post_status'    => 'private',
				'posts_per_page' => 1,
				'fields'         => 'ids',
				'orderby'        => 'ID',
				'order'          => 'DESC',
			)
		);
		$this->assertNotEmpty( $rows );
		$row = $this->log->load( (int) $rows[0] );
		$this->assertIsArray( $row );
		$this->assertSame( 2, $row['applied'] );
		$this->assertSame( 2, count( $row['items'] ) );
		$this->assertArrayHasKey( 'received_at', $row );
		$this->assertSame( substr( hash( 'sha256', $this->key ), 0, 12 ), $row['key'] );
		$this->later(
			static function () use ( $rows ): void {
				wp_delete_post( (int) $rows[0], true );
			}
		);
	}

	/**
	 * The audit rows have a retention: the daily sweep is on the schedule, and
	 * firing its hook deletes the rows past their retention days while the
	 * young ones stay.
	 */
	public function test_audit_rows_are_swept_once_past_their_retention(): void {
		$this->assertNotFalse( wp_next_scheduled( Retention::HOOK ), 'The daily sweep is on the schedule.' );

		$expired = $this->audit_row( gmdate( 'Y-m-d H:i:s', time() - ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS ) );
		$fresh   = $this->audit_row( gmdate( 'Y-m-d H:i:s', time() - DAY_IN_SECONDS ) );

		/** This hook is the retention's own daily event (Retention::HOOK), delivered by WP-Cron.
		 *
		 * @since 0.2.0
		 */
		do_action( Retention::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the retention's own hook constant.

		$this->assertNull( get_post( $expired ), 'A row past its retention days is gone.' );
		$this->assertInstanceOf( \WP_Post::class, get_post( $fresh ), 'A row inside its retention days stays.' );
	}

	/**
	 * An audit row written at the given time (UTC), the way BatchLog writes
	 * rows; removed again after the test.
	 *
	 * @param string $date_gmt The row's creation time (UTC).
	 */
	private function audit_row( string $date_gmt ): int {
		$id = wp_insert_post(
			array(
				'post_type'     => BatchLog::POST_TYPE,
				'post_status'   => 'private',
				'post_title'    => 'Stock push ' . $date_gmt,
				'post_date'     => $date_gmt,
				'post_date_gmt' => $date_gmt,
			),
			true
		);
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		return $id;
	}

	/**
	 * An unknown SKU is an error row; the known SKUs of the same batch still
	 * apply — the batch is never rolled back.
	 */
	public function test_unknown_sku_errors_per_row(): void {
		$product = $this->skued_product( 10 );

		$answer = $this->push(
			array(
				array(
					'sku' => 'NO-SUCH-SKU-' . self::tag(),
					'qty' => 3,
				),
				array(
					'sku' => $product->get_sku(),
					'qty' => 6,
				),
			)
		);

		$this->assertSame( 200, $answer['status'] );
		$body = $answer['body'];
		$this->assertSame( 1, $body['applied'] );
		$this->assertSame( 1, $body['errors'] );
		$this->assertSame( 'error', $body['results'][0]['status'] );
		$this->assertSame( 'unknown_sku', $body['results'][0]['code'] );
		$this->assertSame( 6, $this->stock_of( $product )['qty'] );
	}

	/**
	 * Re-pushing the values in place is a no-op: unchanged rows, no write,
	 * no stock change fired.
	 */
	public function test_repush_of_equal_values_is_a_noop(): void {
		$product = $this->skued_product( 10 );
		$this->push(
			array(
				array(
					'sku' => $product->get_sku(),
					'qty' => 5,
				),
			)
		);

		$fired = 0;
		$watch = static function () use ( &$fired ): void {
			++$fired;
		};
		add_action( 'woocommerce_product_set_stock', $watch );
		$this->later(
			static function () use ( $watch ): void {
				remove_action( 'woocommerce_product_set_stock', $watch );
			}
		);

		$answer = $this->push(
			array(
				array(
					'sku' => $product->get_sku(),
					'qty' => 5,
				),
			)
		);

		$this->assertSame( 200, $answer['status'] );
		$body = $answer['body'];
		$this->assertSame( 1, $body['unchanged'] );
		$this->assertSame( 0, $body['applied'] );
		$this->assertSame( 'unchanged', $body['results'][0]['status'] );
		$this->assertSame( 0, $fired, 'A no-op push must not fire WooCommerce stock actions.' );
	}

	/**
	 * Out of stock blocks the inquiry chain; recovery opens it again. The
	 * chain here is WooCommerce's own gate: the product cannot be added to
	 * the solution draft, so no inquiry can carry it.
	 */
	public function test_out_of_stock_blocks_and_recovery_reopens_the_inquiry_chain(): void {
		$product = $this->skued_product( 10 );
		$sku     = (string) $product->get_sku();

		$this->push(
			array(
				array(
					'sku' => $sku,
					'qty' => 0,
				),
			)
		);
		$this->assertSame( 'outofstock', $this->stock_of( $product )['status'] );
		$pushed = wc_get_product( $product->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $pushed );
		$this->assertFalse( $pushed->is_in_stock() );
		$this->assertFalse( $pushed->is_visible(), 'The shop hides what the ERP pushed out of stock.' );

		$this->as_user( $this->customer()->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->assertFalse( WC()->cart->add_to_cart( $product->get_id(), 1 ), 'Out of stock: the draft gate stays shut.' );

		$this->push(
			array(
				array(
					'sku' => $sku,
					'qty' => 7,
				),
			)
		);
		$this->assertSame( 'instock', $this->stock_of( $product )['status'] );
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 1 ), 'Recovered: the draft accepts the product again.' );
	}

	/**
	 * The quantity is the authority on a stock-managed product: a contradicting
	 * state is refused per row, the state word only applies where no quantity
	 * derives a status. Broken rows error without touching the others.
	 */
	public function test_explicit_state_and_broken_rows(): void {
		$product   = $this->skued_product( 10 );
		$unmanaged = $this->product( '990' );
		$unmanaged->set_sku( 'NU-' . self::tag() );
		$unmanaged->set_manage_stock( false );
		$unmanaged->save();

		$answer = $this->push(
			array(
				array(
					'sku'   => $product->get_sku(),
					'qty'   => 9,
					'state' => 'outofstock',
				),
				array(
					'sku' => $unmanaged->get_sku(),
					'qty' => 3,
				),
				array(
					'sku'   => $product->get_sku(),
					'state' => 'onbackorder',
				),
				array( 'sku' => $product->get_sku() ),
				array(
					'sku'   => $unmanaged->get_sku(),
					'state' => 'outofstock',
				),
			)
		);

		$this->assertSame( 200, $answer['status'] );
		$body = $answer['body'];
		$this->assertSame( 1, $body['applied'] );
		$this->assertSame( 4, $body['errors'] );
		// WooCommerce's own rule: a managed product carries the status its
		// quantity derives, so a contradicting state is refused per row.
		$this->assertSame( 'state_overridden', $body['results'][0]['code'] );
		$this->assertSame( 10, $this->stock_of( $product )['qty'], 'The refused row wrote nothing.' );
		$this->assertSame( 'instock', $this->stock_of( $product )['status'] );
		$this->assertSame( 'not_stock_managed', $body['results'][1]['code'] );
		$this->assertSame( 'invalid_state', $body['results'][2]['code'] );
		$this->assertSame( 'missing_target', $body['results'][3]['code'] );
		$this->assertSame( 'applied', $body['results'][4]['status'], 'On a product without managed stock the state applies.' );
		$pulled = wc_get_product( $unmanaged->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $pulled );
		$this->assertSame( 'outofstock', (string) $pulled->get_stock_status() );
	}

	/**
	 * The key decides: no header, a wrong key, and a cleared key all get 401.
	 */
	public function test_the_key_gates_the_route(): void {
		$no_header = $this->push(
			array(
				array(
					'sku' => 'X',
					'qty' => 1,
				),
			),
			false
		);
		$this->assertSame( 401, $no_header['status'] );
		$this->assertSame( 'linker_stock_unauthorized', $no_header['body']['code'] );

		$wrong = $this->push(
			array(
				array(
					'sku' => 'X',
					'qty' => 1,
				),
			),
			'not-the-key'
		);
		$this->assertSame( 401, $wrong['status'] );

		PushKey::clear();
		$closed = $this->push(
			array(
				array(
					'sku' => 'X',
					'qty' => 1,
				),
			),
			$this->key
		);
		$this->assertSame( 401, $closed['status'], 'No key set: the route rejects everything.' );
	}
}

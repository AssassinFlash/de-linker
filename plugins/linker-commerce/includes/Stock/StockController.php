<?php
/**
 * REST route of the stock push.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

use WP_REST_Controller;
use WP_REST_Request;

/**
 * POST /wp-json/linker/v1/stock is the channel an ERP pushes stock through
 * (ticket #69): a batch of {sku, qty, state?} rows, answered row by row.
 * It is the only write surface: authenticated with the push key set from
 * WP-CLI (PushKey; no key set rejects everything), idempotent (a push of
 * the values already in place answers unchanged and writes nothing), and
 * every accepted batch leaves one audit row (BatchLog). A SKU the site
 * does not know is an error row of its own — the batch is never rolled
 * back — so 200 means "accepted and applied row by row"; read results[].
 * An OPTIONS request shows the schema.
 */
final class StockController extends WP_REST_Controller {

	/**
	 * REST namespace.
	 */
	public const NAMESPACE = 'linker/v1';

	/**
	 * Route within the namespace.
	 */
	public const REST_BASE = 'stock';

	/**
	 * Sets the route: linker/v1/stock.
	 *
	 * @param BatchLog|null $log The audit rows; created when not given.
	 */
	public function __construct( private readonly ?BatchLog $log = null ) {
		$this->namespace = self::NAMESPACE;
		$this->rest_base = self::REST_BASE;
	}

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register_routes(): void {
		register_rest_route(
			self::NAMESPACE,
			'/' . self::REST_BASE,
			array(
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'push' ),
					'permission_callback' => array( $this, 'push_permissions_check' ),
					'args'                => $this->get_collection_params(),
				),
				'schema' => array( $this, 'get_public_item_schema' ),
			)
		);
	}

	/**
	 * The one parameter: the pushed rows.
	 *
	 * @return array<string, array<string, mixed>>
	 */
	public function get_collection_params(): array {
		return array(
			'items' => array(
				'description'       => __( 'The pushed stock rows. Each is an object with a string sku and a qty (integer, 0 or more), a state (instock or outofstock), or both; rows that do not parse, or name an unknown SKU, are answered as error rows of their own.', 'linker-commerce' ),
				'type'              => 'array',
				'required'          => true,
				'minItems'          => 1,
				'items'             => array( 'type' => 'object' ),
				'validate_callback' => static function ( $value ): bool {
					return \is_array( $value );
				},
			),
		);
	}

	/**
	 * Only the holder of the push key pushes; without a key set the route
	 * rejects everything.
	 *
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return true|\WP_Error
	 */
	public function push_permissions_check( $request ) {
		$provided = $request->get_header( PushKey::HEADER );
		if ( \is_string( $provided ) && '' !== $provided && PushKey::verify( $provided ) ) {
			return true;
		}
		return new \WP_Error(
			'linker_stock_unauthorized',
			__( 'A valid stock push key is required.', 'linker-commerce' ),
			array( 'status' => 401 )
		);
	}

	/**
	 * Applies the batch, records the audit row, answers the rows.
	 *
	 * @param WP_REST_Request $request Request with the validated `items`.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return \WP_REST_Response|\WP_Error
	 */
	public function push( $request ) {
		$items = $request->get_param( 'items' );
		if ( ! \is_array( $items ) || array() === $items ) {
			return new \WP_Error(
				'linker_stock_no_items',
				__( 'The batch has no items.', 'linker-commerce' ),
				array( 'status' => 400 )
			);
		}

		$result = Batch::apply( $items );

		$log   = $this->log ?? new BatchLog();
		$batch = $log->record(
			array(
				'key'       => PushKey::fingerprint(),
				'items'     => $items,
				'results'   => $result['results'],
				'applied'   => $result['applied'],
				'unchanged' => $result['unchanged'],
				'errors'    => $result['errors'],
			)
		);
		if ( 0 === $batch ) {
			return new \WP_Error(
				'linker_stock_audit_failed',
				__( 'The batch was applied but its audit row could not be written; retry the push (it is idempotent).', 'linker-commerce' ),
				array( 'status' => 500 )
			);
		}

		return rest_ensure_response(
			array(
				'batch'     => $batch,
				'applied'   => $result['applied'],
				'unchanged' => $result['unchanged'],
				'errors'    => $result['errors'],
				'results'   => $result['results'],
			)
		);
	}

	/**
	 * The answer's schema.
	 *
	 * @return array<string, mixed>
	 */
	public function get_item_schema(): array {
		if ( null === $this->schema ) {
			$this->schema = array(
				'$schema'     => 'http://json-schema.org/draft-04/schema#',
				'title'       => 'stock-push',
				'description' => __( 'The answer to one stock push (ticket #69).', 'linker-commerce' ),
				'type'        => 'object',
				'properties'  => array(
					'batch'     => array(
						'type'        => 'integer',
						'description' => __( 'The audit row the batch left.', 'linker-commerce' ),
					),
					'applied'   => array(
						'type'        => 'integer',
						'description' => __( 'Rows written.', 'linker-commerce' ),
					),
					'unchanged' => array(
						'type'        => 'integer',
						'description' => __( 'Rows already in place: no-op.', 'linker-commerce' ),
					),
					'errors'    => array(
						'type'        => 'integer',
						'description' => __( 'Rows refused; the rest of the batch still applied.', 'linker-commerce' ),
					),
					'results'   => array(
						'type'        => 'array',
						'description' => __( 'One row per pushed item, in request order.', 'linker-commerce' ),
						'items'       => array(
							'type'       => 'object',
							'properties' => array(
								'sku'          => array( 'type' => 'string' ),
								'status'       => array(
									'type' => 'string',
									'enum' => array( Batch::APPLIED, Batch::UNCHANGED, Batch::ERROR ),
								),
								'code'         => array(
									'type'        => 'string',
									'description' => __( 'On error rows: invalid_item, invalid_sku, invalid_qty, invalid_state, missing_target, unknown_sku, not_stock_managed or state_overridden (a state that contradicts what the quantity derives on a stock-managed product).', 'linker-commerce' ),
								),
								'qty'          => array(
									'type'        => array( 'integer', 'null' ),
									'description' => __( 'The product\'s quantity after the push.', 'linker-commerce' ),
								),
								'stock_status' => array(
									'type'        => array( 'string', 'null' ),
									'description' => __( 'The product\'s stock status after the push.', 'linker-commerce' ),
								),
							),
						),
					),
				),
			);
		}

		return $this->schema;
	}
}

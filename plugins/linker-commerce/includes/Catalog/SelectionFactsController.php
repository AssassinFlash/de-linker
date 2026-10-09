<?php
/**
 * REST route of the selection facts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

use WP_REST_Controller;
use WP_REST_Request;

/**
 * GET /wp-json/linker/v1/selection-facts?ids=1,2,3 returns
 * { "<id>": SelectionFactSet } for the published products among the IDs; an
 * OPTIONS request shows the schema. It is public and the same for every
 * visitor: no login, nonce or cookie, so a page cache may keep it
 * (docs/specs/7-selection-facts.md).
 */
final class SelectionFactsController extends WP_REST_Controller {

	/**
	 * REST namespace.
	 */
	public const NAMESPACE = 'linker/v1';

	/**
	 * Route within the namespace.
	 */
	public const REST_BASE = 'selection-facts';

	/**
	 * Most IDs one request may ask for (docs/specs/7-selection-facts.md); more
	 * are a 400 from WordPress's schema validation, before the callback runs.
	 */
	public const MAX_IDS = 100;

	/**
	 * Sets the route: linker/v1/selection-facts.
	 */
	public function __construct() {
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
					'methods'             => 'GET',
					'callback'            => array( $this, 'get_items' ),
					'permission_callback' => array( $this, 'get_items_permissions_check' ),
					'args'                => $this->get_collection_params(),
				),
				'schema' => array( $this, 'get_public_item_schema' ),
			)
		);
	}

	/**
	 * The one parameter: 1 to MAX_IDS product IDs, comma-separated or as a list.
	 *
	 * @return array<string, array<string, mixed>>
	 */
	public function get_collection_params(): array {
		return array(
			'ids' => array(
				/* translators: %d: most product IDs per request. */
				'description' => sprintf( __( 'Product IDs, at most %d.', 'linker-commerce' ), self::MAX_IDS ),
				'type'        => 'array',
				'items'       => array(
					'type'    => 'integer',
					'minimum' => 1,
				),
				'maxItems'    => self::MAX_IDS,
				'required'    => true,
			),
		);
	}

	/**
	 * Anyone may read the facts: they are the same for every visitor.
	 *
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 */
	public function get_items_permissions_check( $request ): bool {
		return true;
	}

	/**
	 * The facts of the published products among the requested IDs.
	 *
	 * @param WP_REST_Request $request Request with the validated `ids`.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return object A JSON object: product ID => facts.
	 */
	public function get_items( $request ): object {
		$ids = array_values( array_unique( array_map( 'intval', (array) $request->get_param( 'ids' ) ) ) );
		// One query each for the posts, their meta and their terms instead of several per product.
		_prime_post_caches( $ids );

		$facts = array();
		foreach ( $ids as $id ) {
			if ( 'product' === get_post_type( $id ) && 'publish' === get_post_status( $id ) ) {
				$facts[ $id ] = SelectionFacts::for_product( $id )->to_array();
			}
		}

		return (object) $facts;
	}

	/**
	 * The answer's schema: an object whose values are SelectionFactSet::schema().
	 *
	 * @return array<string, mixed>
	 */
	public function get_item_schema(): array {
		if ( null === $this->schema ) {
			$this->schema = array(
				'$schema'              => 'http://json-schema.org/draft-04/schema#',
				'title'                => 'selection-facts',
				'description'          => __( 'Selection facts of the requested published products, by product ID.', 'linker-commerce' ),
				'type'                 => 'object',
				'additionalProperties' => SelectionFactSet::schema(),
			);
		}

		return $this->schema;
	}
}

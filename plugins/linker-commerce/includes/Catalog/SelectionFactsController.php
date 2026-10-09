<?php
/**
 * REST route of the selection facts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

use WP_REST_Request;

/**
 * GET /wp-json/linker/v1/selection-facts?ids=1,2,3 returns
 * { "<id>": SelectionFactSet } for the published products among the IDs, in
 * the order asked. It is public and the same for every visitor: no login,
 * nonce or cookie, so a page cache may keep it (docs/specs/7-selection-facts.md).
 */
final class SelectionFactsController {

	/**
	 * REST namespace.
	 */
	public const NAMESPACE = 'linker/v1';

	/**
	 * Route within the namespace.
	 */
	public const ROUTE = '/selection-facts';

	/**
	 * Most IDs one request may ask for (docs/specs/7-selection-facts.md); more
	 * are a 400 from WordPress's schema validation, before the callback runs.
	 */
	public const MAX_IDS = 100;

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register_routes(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_items' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'ids' => array(
						'type'     => 'array',
						'items'    => array(
							'type'    => 'integer',
							'minimum' => 1,
						),
						'maxItems' => self::MAX_IDS,
						'required' => true,
					),
				),
			)
		);
	}

	/**
	 * The facts of the published products among the requested IDs.
	 *
	 * @param WP_REST_Request $request Request with the validated `ids`.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return object A JSON object: product ID => facts.
	 */
	public function get_items( WP_REST_Request $request ): object {
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
}

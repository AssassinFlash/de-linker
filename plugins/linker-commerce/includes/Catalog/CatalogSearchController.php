<?php
/**
 * REST route of the catalogue search.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

use WP_REST_Controller;
use WP_REST_Request;

/**
 * GET /wp-json/linker/v1/catalog-search?q=<model or item number>&limit=<n>
 * answers the products of the catalogue whose name or SKU holds the query
 * (catalog-search, ticket #68): `{ "items": [{ id, title, sku, url, facts }] }`.
 *
 * It is the reader behind the catalogue's search box — the instant resolution
 * of a model or item number — and it answers for every visitor the same way:
 * no login, nonce or cookie, so a page cache may keep it (the same contract
 * as the selection facts). Products hidden from the catalogue are not
 * answered (CatalogSearch).
 *
 * `?lang=en|de` picks the language of the products and their addresses, the
 * same parameter every REST list of the site reads (linker-i18n's RestLang).
 */
final class CatalogSearchController extends WP_REST_Controller {


	/**
	 * REST namespace.
	 */
	public const NAMESPACE = 'linker/v1';

	/**
	 * Route within the namespace.
	 */
	public const REST_BASE = 'catalog-search';

	/**
	 * The search itself.
	 *
	 * @var CatalogSearch
	 */
	private CatalogSearch $search;

	/**
	 * Sets the route.
	 *
	 * @param CatalogSearch|null $search The search (tests).
	 */
	public function __construct( ?CatalogSearch $search = null ) {
		$this->namespace = self::NAMESPACE;
		$this->rest_base = self::REST_BASE;
		$this->search    = $search ?? new CatalogSearch();
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
	 * The parameters: the query, at most how many hits, and the language.
	 *
	 * @return array<string, array<string, mixed>>
	 */
	public function get_collection_params(): array {
		return array(
			'q'     => array(
				'description' => __( 'A model or item number.', 'linker-commerce' ),
				'type'        => 'string',
				'required'    => true,
				'minLength'   => CatalogSearch::MIN_LENGTH,
			),
			'limit' => array(
				/* translators: %d: most products per answer. */
				'description' => sprintf( __( 'Most products to answer with, at most %d.', 'linker-commerce' ), CatalogSearch::MAX_LIMIT ),
				'type'        => 'integer',
				'minimum'     => 1,
				'maximum'     => CatalogSearch::MAX_LIMIT,
				'default'     => CatalogSearch::DEFAULT_LIMIT,
			),
			'lang'  => array(
				'description' => __( 'Language of the products and their addresses.', 'linker-commerce' ),
				'type'        => 'string',
				'enum'        => array( 'en', 'de' ),
			),
		);
	}

	/**
	 * Anyone may search: the answer is the same for every visitor.
	 *
	 * @param         WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 */
	public function get_items_permissions_check( $request ): bool {
		return true;
	}

	/**
	 * The products the query names.
	 *
	 * @param         WP_REST_Request $request Request with the validated `q` and `limit`.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return        object A JSON object: the hits in catalogue order.
	 */
	public function get_items( $request ): object {
		$query = (string) $request->get_param( 'q' );
		$limit = (int) $request->get_param( 'limit' );
		$items = array();
		foreach ( $this->search->matching_ids( $query, $limit ) as $product_id ) {
			$items[] = $this->search->payload( $product_id );
		}
		return (object) array(
			'query' => $query,
			'items' => $items,
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
				'title'       => 'catalog-search',
				'description' => __( 'The products of the catalogue whose name or item number holds the query.', 'linker-commerce' ),
				'type'        => 'object',
				'properties'  => array(
					'query' => array(
						'description' => __( 'What was searched for.', 'linker-commerce' ),
						'type'        => 'string',
					),
					'items' => array(
						'description' => __( 'The hits, in catalogue order.', 'linker-commerce' ),
						'type'        => 'array',
						'items'       => array(
							'type'       => 'object',
							'properties' => array(
								'id'    => array(
									'description' => __( 'Product ID.', 'linker-commerce' ),
									'type'        => 'integer',
								),
								'title' => array(
									'description' => __( 'Product name.', 'linker-commerce' ),
									'type'        => 'string',
								),
								'sku'   => array(
									'description' => __( 'Item number.', 'linker-commerce' ),
									'type'        => 'string',
								),
								'url'   => array(
									'description' => __( 'The product page.', 'linker-commerce' ),
									'type'        => 'string',
								),
								'facts' => array(
									'description' => __( 'Selection facts of the product.', 'linker-commerce' ),
									'type'        => 'object',
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

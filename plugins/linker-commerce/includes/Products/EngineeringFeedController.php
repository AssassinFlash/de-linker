<?php
/**
 * REST route of the engineering feed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use WP_REST_Controller;
use WP_REST_Request;

/**
 * GET /wp-json/linker/v1/engineering-feed returns the feed of docs/specs/
 * 8-engineering-data.md: every published product's engineering data, the
 * overlay, the compatibility contract and its version. With ?since= only the
 * products modified after that moment. It is public and the same for every
 * visitor: no login, nonce or cookie. Responses disable caching; consumers
 * must also validate current dependencies. An OPTIONS request shows the schema.
 */
final class EngineeringFeedController extends WP_REST_Controller {

	/**
	 * REST namespace.
	 */
	public const NAMESPACE = 'linker/v1';

	/**
	 * Route within the namespace.
	 */
	public const REST_BASE = 'engineering-feed';

	/**
	 * Sets the route: linker/v1/engineering-feed.
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
	 * The one parameter: the moment to read from, if only the changed products
	 * are wanted. A value strtotime() cannot read is rejected by the
	 * validation, not answered with an empty feed.
	 *
	 * @return array<string, array<string, mixed>>
	 */
	public function get_collection_params(): array {
		return array(
			'since' => array(
				'description'       => __( 'GMT timestamp or ISO-8601 moment; only products modified after it are returned.', 'linker-commerce' ),
				'type'              => 'string',
				'required'          => false,
				'validate_callback' => static function ( $value ): bool {
					return '' === $value || ( is_string( $value ) && false !== strtotime( $value ) );
				},
			),
		);
	}

	/**
	 * Anyone may read the feed: it is the same for every visitor.
	 *
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 */
	public function get_items_permissions_check( $request ): bool {
		return true;
	}

	/**
	 * The feed. `since` has passed the validation, so strtotime() reads it.
	 *
	 * @param WP_REST_Request $request Request with the validated `since`.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return object The feed as a JSON object.
	 */
	public function get_items( $request ): object {
		$since = $request->get_param( 'since' );

		nocache_headers();
		try {
			return (object) EngineeringFeed::feed( is_string( $since ) && '' !== $since ? $since : null );
		} catch ( \RuntimeException $error ) {
			return new \WP_Error( 'publication_unavailable', 'Current product permission could not be checked.', array( 'status' => 503 ) );
		}
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
				'title'       => 'engineering-feed',
				'description' => __( 'The engineering data of every published product, the overlay components, the compatibility contract and its version (docs/specs/8-engineering-data.md, target shape 5; the binding contract is services/engine/schemas/feed.schema.json).', 'linker-commerce' ),
				'type'        => 'object',
				'properties'  => array(
					'schema_version'        => array(
						'type'        => 'integer',
						'description' => __( 'The feed schema version, the contract with the engine (#14).', 'linker-commerce' ),
					),
					'generated_at'          => array(
						'type'   => 'string',
						'format' => 'date-time',
					),
					'compatibility_version' => array(
						'type'        => 'string',
						'description' => __( 'The version stated by data/compatibility.json.', 'linker-commerce' ),
					),
					'compatibility'         => array(
						'type'        => 'object',
						'description' => __( 'The compatibility contract itself (data/compatibility.json), so the engine\'s sync refreshes its copy from the same fetch; its version equals compatibility_version. Absent when the site cannot read the file.', 'linker-commerce' ),
					),
					'overlay'               => array(
						'type'        => 'array',
						'description' => __( 'Current Woo engineering reference records with bound document evidence.', 'linker-commerce' ),
						'items'       => array(
							'type'       => 'object',
							'properties' => array(
								'id'        => array( 'type' => 'string' ),
								'kind'      => array(
									'type' => 'string',
									'enum' => array( 'pv_module' ),
								),
								'brand'     => array( 'type' => 'string' ),
								'model'     => array( 'type' => 'string' ),
								'figures'   => array(
									'type'                 => 'object',
									'additionalProperties' => true,
								),
								'documents' => array(
									'type'  => 'array',
									'items' => array(
										'type'       => 'object',
										'properties' => array(
											'url'   => array(
												'type'   => 'string',
												'format' => 'uri',
											),
											'title' => array( 'type' => 'string' ),
											'type'  => array( 'type' => 'string' ),
											'lang'  => array( 'type' => 'string' ),
										),
									),
								),
							),
						),
					),
					'products'              => array(
						'type'        => 'array',
						'description' => __( 'One entry per published product.', 'linker-commerce' ),
						'items'       => array(
							'type'       => 'object',
							'properties' => array(
								'id'           => array( 'type' => 'integer' ),
								'sku'          => array( 'type' => 'string' ),
								'model'        => array( 'type' => array( 'string', 'null' ) ),
								'brand'        => array( 'type' => array( 'string', 'null' ) ),
								'series'       => array( 'type' => array( 'string', 'null' ) ),
								'device_class' => array( 'type' => 'string' ),
								'application'  => array( 'type' => 'string' ),
								'phase'        => array( 'type' => array( 'integer', 'string' ) ),
								'ac_power_kw'  => array(
									'type'        => array( 'number', 'string' ),
									'description' => __( 'Rated AC power in kW, or unknown (#7 SelectionFactSet).', 'linker-commerce' ),
								),
								'pv_input_kw'  => array(
									'type'        => array( 'number', 'string' ),
									'description' => __( 'Maximum PV input power in kW, or unknown.', 'linker-commerce' ),
								),
								'usable_kwh'   => array(
									'type'        => array( 'number', 'string' ),
									'description' => __( 'Usable energy in kWh, or unknown.', 'linker-commerce' ),
								),
								'nominal_kwh'  => array(
									'type'        => array( 'number', 'string' ),
									'description' => __( 'Nominal energy in kWh, or unknown.', 'linker-commerce' ),
								),
								'kwh_range'    => array(
									'type'        => array( 'object', 'null' ),
									'description' => __( 'Energy range in kWh the product data states; null when it states none.', 'linker-commerce' ),
								),
								'figures'      => array(
									'type'                 => 'object',
									'description'          => __( 'Figure entries with a citation of a hosted document; a value without one is not in the feed.', 'linker-commerce' ),
									'additionalProperties' => true,
								),
								'documents'    => array(
									'type'  => 'array',
									'items' => array(
										'type'       => 'object',
										'properties' => array(
											'url'   => array(
												'type'   => 'string',
												'format' => 'uri',
											),
											'title' => array( 'type' => 'string' ),
											'type'  => array( 'type' => 'string' ),
											'lang'  => array( 'type' => 'string' ),
										),
									),
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

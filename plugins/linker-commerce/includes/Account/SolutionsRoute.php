<?php
/**
 * The REST route that saves a solution.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * POST linker/v1/solutions: "Save solution" in the Solution Configurator
 * (docs/specs/14-solution-configurator.md). The body is the configurator's
 * kind and input, which reproduce the design, the products and quantities the
 * customer saw, and optionally the design report as a base64 PDF. A logged-in
 * customer's solution is saved at once (201); a guest's waits in their
 * WooCommerce session until they log in (202, SavedSolutions::claim()), without
 * the report, which is too large for the session.
 */
final class SolutionsRoute {

	/**
	 * Namespace and route.
	 */
	public const NAMESPACE = 'linker/v1';
	public const ROUTE     = '/solutions';

	/**
	 * Configurator results that can be saved: the residential and the
	 * commercial design (the utility segment is an inquiry form).
	 */
	public const KINDS = array( 'residential', 'commercial' );

	/**
	 * Sets up the route.
	 *
	 * @param SavedSolutions $solutions The store of saved solutions.
	 */
	public function __construct( private readonly SavedSolutions $solutions ) {}

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'create' ),
				// Guests may save too: their solution waits in their session until they log in.
				'permission_callback' => '__return_true',
				'args'                => array(
					'kind'       => array(
						'type'     => 'string',
						'enum'     => self::KINDS,
						'required' => true,
					),
					'title'      => array(
						'type'      => 'string',
						'minLength' => 1,
						'required'  => true,
					),
					'input'      => array(
						'type'     => 'object',
						'required' => true,
					),
					'lines'      => array(
						'type'     => 'array',
						'minItems' => 1,
						'required' => true,
						'items'    => array(
							'type'                 => 'object',
							'properties'           => array(
								'product_id' => array(
									'type'    => 'integer',
									'minimum' => 1,
								),
								'quantity'   => array(
									'type'    => 'integer',
									'minimum' => 1,
								),
							),
							'required'             => array( 'product_id', 'quantity' ),
							'additionalProperties' => false,
						),
					),
					'report_pdf' => array(
						'type' => 'string',
					),
				),
			)
		);
	}

	/**
	 * Saves the solution.
	 *
	 * @param WP_REST_Request $request The request, validated against the arguments above.
	 * @return WP_REST_Response|WP_Error
	 */
	public function create( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$items = array();
		foreach ( (array) $request->get_param( 'lines' ) as $line ) {
			$line       = (array) $line;
			$product_id = (int) ( $line['product_id'] ?? 0 );
			$product    = wc_get_product( $product_id );
			if ( ! $product instanceof \WC_Product || 'publish' !== $product->get_status() ) {
				return new WP_Error(
					'linker_solution_product',
					/* translators: %d: product ID. */
					sprintf( __( 'Product %d is not available.', 'linker-commerce' ), $product_id ),
					array( 'status' => 400 )
				);
			}
			$items[] = array(
				'product_id' => $product_id,
				'quantity'   => (int) ( $line['quantity'] ?? 0 ),
			);
		}
		$report = self::report( (string) $request->get_param( 'report_pdf' ) );
		if ( $report instanceof WP_Error ) {
			return $report;
		}
		$title  = sanitize_text_field( (string) $request->get_param( 'title' ) );
		$design = array(
			'kind'  => (string) $request->get_param( 'kind' ),
			'input' => (array) $request->get_param( 'input' ),
		);

		$customer_id = get_current_user_id();
		if ( 0 === $customer_id ) {
			$this->solutions->keep_for_guest( $title, $items, $design );
			return new WP_REST_Response(
				array(
					'id'  => 0,
					'url' => SavedSolutions::url( 0 ),
				),
				202
			);
		}
		$id = $this->solutions->save( $customer_id, $title, $items, $design, $report );
		if ( 0 === $id ) {
			return new WP_Error( 'linker_solution_not_saved', __( 'The solution could not be saved.', 'linker-commerce' ), array( 'status' => 500 ) );
		}
		return new WP_REST_Response(
			array(
				'id'  => $id,
				'url' => SavedSolutions::url( $id ),
			),
			201
		);
	}

	/**
	 * The design report PDF from its base64 text, '' for none. It must be a
	 * PDF no larger than the site's upload limit (wp_max_upload_size()).
	 *
	 * @param string $encoded Base64 text of the PDF.
	 * @return string|WP_Error
	 */
	private static function report( string $encoded ): string|WP_Error {
		if ( '' === $encoded ) {
			return '';
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- the report travels as base64 inside the JSON body.
		$pdf = base64_decode( $encoded, true );
		if ( false === $pdf || ! str_starts_with( $pdf, '%PDF-' ) || strlen( $pdf ) > wp_max_upload_size() ) {
			return new WP_Error( 'linker_solution_report', __( 'The design report must be a PDF file within the upload size limit.', 'linker-commerce' ), array( 'status' => 400 ) );
		}
		return $pdf;
	}
}

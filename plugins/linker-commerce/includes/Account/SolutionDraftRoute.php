<?php
/**
 * One server-validated operation for the complete solution draft.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Product lines supplied by a browser never define the trusted complete BOM. */
final class SolutionDraftRoute {

	/** Registers the action alongside the saved-solution route. */
	public function register(): void {
		register_rest_route(
			SolutionsRoute::NAMESPACE,
			'/solutions/draft',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'create' ),
				'permission_callback' => array( $this, 'permission' ),
				'args'                => array(
					'kind'                  => array(
						'type'     => 'string',
						'enum'     => SolutionsRoute::KINDS,
						'required' => true,
					),
					'input'                 => array(
						'type'     => 'object',
						'required' => true,
					),
					'selection_fingerprint' => array(
						'type'     => 'string',
						'pattern'  => '^[a-f0-9]{64}$',
						'required' => true,
					),
				),
			)
		);
	}

	/**
	 * Native Store API nonce binds the operation to the Woo customer session.
	 *
	 * @param WP_REST_Request $request Request.
	 */
	public function permission( WP_REST_Request $request ): bool|WP_Error {
		$nonce = $request->get_header( 'Nonce' );
		return is_string( $nonce ) && wp_verify_nonce( $nonce, 'wc_store_api' ) ? true : new WP_Error( 'woocommerce_rest_invalid_nonce', __( 'Please refresh your solution draft and try again.', 'linker-commerce' ), array( 'status' => 403 ) );
	}

	/**
	 * Adds the trusted complete design or leaves the draft as it was.
	 *
	 * @param WP_REST_Request $request Request.
	 */
	public function create( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$result = ( new DesignProof() )->verify(
			(string) $request->get_param( 'kind' ),
			(array) $request->get_param( 'input' ),
			(string) $request->get_param( 'selection_fingerprint' )
		);
		if ( $result instanceof WP_Error ) {
			return $result;
		}
		$items = ( new AtomicSolutionDraft() )->add( $result );
		return $items instanceof WP_Error ? $items : new WP_REST_Response( array( 'items' => $items ), 200 );
	}
}

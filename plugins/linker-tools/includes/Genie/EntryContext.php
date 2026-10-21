<?php
/**
 * Current identity comparison for the marketing composer's small recovery record.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_REST_Request;
use WP_REST_Response;

/** No text, cookie, identity or token is exposed by this auxiliary read. */
final class EntryContext {
	/** Registers the same-origin auxiliary route, using native REST authentication. */
	public function register(): void {
		register_rest_route(
			Proxy::NAMESPACE,
			'/genie/entry-context',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'read' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'tab' => array(
						'type'     => 'string',
						'required' => true,
						'pattern'  => '^[0-9a-f-]{36}$',
					),
				),
			)
		);
	}

	/**
	 * Resolves the current server principal before cached text can be displayed.
	 *
	 * @param WP_REST_Request $request Current authenticated request.
	 */
	public function read( WP_REST_Request $request ): WP_REST_Response {
		$response = new WP_REST_Response( array( 'scope' => ( new Conversations() )->entry_scope( (string) $request->get_param( 'tab' ) ) ) );
		$response->header( 'Cache-Control', 'private, no-store' );
		$response->header( 'Vary', 'Cookie' );
		return $response;
	}
}

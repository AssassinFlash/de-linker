<?php
/**
 * Server-cache policy for current Woo publication authority.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Cache\DynamicHtml;
use WP_REST_Request;
use WP_REST_Response;

/** Keep the current authority and preparation protocol out of page caches. */
final class FreshRest {
	/** Install before REST responses are sent, including validation errors. */
	public function register(): void {
		add_filter( 'rest_post_dispatch', array( $this, 'response' ), 20, 3 );
	}

	/**
	 * Mark only the current-authority routes, regardless of response status.
	 * Existing cached entries must also be purged when this policy is deployed:
	 * a cache hit is served before WordPress can run this hook.
	 *
	 * @param mixed           $response Native response.
	 * @param mixed           $server Native REST server.
	 * @param WP_REST_Request $request Native request.
	 * @return mixed Unchanged response with cache controls where applicable.
	 */
	public function response( mixed $response, mixed $server, WP_REST_Request $request ): mixed {
		unset( $server );
		$route = rtrim( $request->get_route(), '/' );
		if ( ! in_array( $route, array( '/linker/v1/publication/manifest', '/linker/v1/publication/validate', '/linker/v1/publication/identify', '/linker/v1/publication/jobs/claim', '/linker/v1/publication/jobs/ack', '/linker/v1/engineering-feed' ), true ) ) {
			return $response;
		}
		DynamicHtml::forbid( 'current publication authority' );
		if ( $response instanceof WP_REST_Response ) {
			$response->header( 'Cache-Control', 'no-store, private, max-age=0' );
			$response->header( 'Pragma', 'no-cache' );
			// The server honours this independently of standard HTTP cache headers.
			$response->header( 'X-LiteSpeed-Cache-Control', 'no-cache' );
		}
		return $response;
	}
}

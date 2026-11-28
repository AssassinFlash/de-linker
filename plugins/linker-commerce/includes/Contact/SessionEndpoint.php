<?php
/**
 * Issue the private fields for an anonymous Contact page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Cache\DynamicHtml;
use Linker\Commerce\Protection\Identity;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Binds the public form to the browser on first interaction. */
final class SessionEndpoint {
	public const NAMESPACE = 'linker/v1';
	public const ROUTE     = '/contact-session';

	/** Register the same-origin session bootstrap. */
	public function register_routes(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'issue' ),
				'permission_callback' => '__return_true',
			)
		);
	}

	/**
	 * Issue the same fields as the native form.
	 *
	 * @param WP_REST_Request $request Browser request.
	 */
	public function issue( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$source = $request->get_header( 'origin' ) ?? $request->get_header( 'referer' );
		if ( ! is_string( $source ) || ! SelectionContext::same_origin( $source ) ) {
			return new WP_Error( 'linker_contact_origin', 'Invalid contact origin.', array( 'status' => 403 ) );
		}
		DynamicHtml::forbid( 'contact session' );
		if ( ! Identity::ensure_browser_cookie() ) {
			return new WP_Error( 'linker_contact_session_unavailable', 'Contact session unavailable.', array( 'status' => 503 ) );
		}
		$response = new WP_REST_Response(
			array(
				'nonce'     => wp_create_nonce( Form::NONCE_ACTION ),
				'requestId' => wp_generate_uuid4(),
			)
		);
		$response->header( 'Cache-Control', 'private, no-store, max-age=0' );
		$response->header( 'X-LiteSpeed-Cache-Control', 'no-cache' );
		$response->header( 'Vary', 'Origin, Cookie' );
		return $response;
	}
}

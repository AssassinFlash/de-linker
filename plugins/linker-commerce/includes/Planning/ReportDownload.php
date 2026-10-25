<?php
/**
 * Private inquiry report downloads, scoped to the stored native order.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use WC_Order;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** The order key grants this frozen report, never project ownership or editing. */
final class ReportDownload {
	/** Register read-only native order access and opaque PDF streaming. */
	public function register(): void {
		register_rest_route(
			'linker/v1',
			'/inquiries/(?P<id>[1-9][0-9]*)/planning-report/(?P<handoff>[a-f0-9]{32})',
			array(
				'methods'             => 'GET',
				'permission_callback' => array( $this, 'permission' ),
				'callback'            => array( $this, 'read' ),
			)
		);
		add_filter( 'rest_post_dispatch', array( $this, 'headers' ), 20, 3 );
		add_filter( 'rest_pre_serve_request', array( $this, 'serve' ), 100, 4 );
	}

	/**
	 * Staff, the signed-in native owner, or possession of this inquiry's key.
	 * These reports contain no prices; the Proforma price gate remains separate.
	 *
	 * @param WP_REST_Request $request Native read.
	 */
	public function permission( WP_REST_Request $request ): bool|WP_Error {
		$order   = wc_get_order( (int) $request['id'] );
		$key     = $request->get_param( 'key' );
		$user    = get_current_user_id();
		$allowed = $order instanceof WC_Order && ( current_user_can( 'manage_woocommerce' ) || ( $user > 0 && $order->get_customer_id() === $user ) || ( is_string( $key ) && '' !== $key && hash_equals( $order->get_order_key(), $key ) ) );
		return $allowed ? true : self::missing();
	}

	/**
	 * Read only a report named by the immutable context on that inquiry.
	 *
	 * @param WP_REST_Request $request Authorised read.
	 */
	public function read( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$access = $this->permission( $request );
		if ( is_wp_error( $access ) ) {
			return $access;
		}
		$order = wc_get_order( (int) $request['id'] );
		if ( ! $order instanceof WC_Order ) {
			return self::missing();
		}
		$contexts = Context::stored( $order );
		$entry    = $contexts[ (string) $request['handoff'] ] ?? null;
		if ( ! is_array( $entry ) ) {
			return self::missing();
		}
		/**
		 * The trusted Tools adapter reads only this stored, authorised report.
		 *
		 * @since 0.3.0
		 * @param string|WP_Error $bytes Private PDF, unavailable by default.
		 * @param array<string,mixed> $handoff Server-stored immutable context.
		 * @param int $order_id Authorised native inquiry.
		 */
		$content = apply_filters( 'linker_tools_planning_report_content', new WP_Error( 'planning_report_unavailable', '', array( 'status' => 503 ) ), $entry['handoff'], $order->get_id() ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Shared server-only Tools file-reader seam.
		if ( is_wp_error( $content ) ) {
			return $content;
		}
		$pdf = $entry['handoff']['snapshot']['pdf'];
		if ( ! self::matches( $content, $pdf['sha256'] ) ) {
			return new WP_Error( 'planning_report_unavailable', '', array( 'status' => 503 ) );
		}
		return new WP_REST_Response(
			$content,
			200,
			array(
				'Content-Type'        => 'application/pdf',
				'Content-Disposition' => 'attachment; filename="linker-planning-' . $order->get_id() . '.pdf"',
			)
		);
	}

	/**
	 * Errors and file bytes carry the same private cache/referrer policy.
	 *
	 * @param mixed           $response Native response.
	 * @param mixed           $server Native server.
	 * @param WP_REST_Request $request Native request.
	 * @return mixed
	 */
	public function headers( mixed $response, mixed $server, WP_REST_Request $request ): mixed {
		unset( $server );
		if ( self::in_scope( $request ) && $response instanceof WP_REST_Response ) {
			foreach ( array(
				'Cache-Control'          => 'no-store, private',
				'Pragma'                 => 'no-cache',
				'Referrer-Policy'        => 'no-referrer',
				'X-Content-Type-Options' => 'nosniff',
			) as $key => $value ) {
				$response->header( $key, $value );
			}
		}
		return $response;
	}

	/**
	 * Stream verified PDF bytes through the native REST lifecycle.
	 *
	 * @param mixed           $served Earlier handler.
	 * @param mixed           $response Native response.
	 * @param WP_REST_Request $request Native request.
	 * @param mixed           $server Native server.
	 */
	public function serve( mixed $served, mixed $response, WP_REST_Request $request, mixed $server ): bool {
		unset( $server );
		if ( ! self::in_scope( $request ) ) {
			return (bool) $served;
		}
		foreach ( array( 'Access-Control-Allow-Origin', 'Access-Control-Allow-Credentials', 'Access-Control-Allow-Headers', 'Access-Control-Expose-Headers' ) as $header ) {
			header_remove( $header );
		}
		if ( ! $served && $response instanceof WP_REST_Response && 'application/pdf' === ( $response->get_headers()['Content-Type'] ?? '' ) && is_string( $response->get_data() ) ) {
			echo $response->get_data(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Verified private PDF bytes, not HTML.
			return true;
		}
		return (bool) $served;
	}

	/**
	 * Match only this private native inquiry-report namespace.
	 *
	 * @param WP_REST_Request $request Native request.
	 */
	private static function in_scope( WP_REST_Request $request ): bool {
		return 1 === preg_match( '~\A/linker/v1/inquiries/[0-9]+/planning-report(?:/|\z)~', $request->get_route() );
	}

	/**
	 * Treat the external filter result as bytes only after magic and hash checks.
	 *
	 * @param mixed  $content Untrusted adapter output.
	 * @param string $sha256 Frozen private asset hash.
	 */
	private static function matches( mixed $content, string $sha256 ): bool {
		return is_string( $content ) && str_starts_with( $content, '%PDF-' ) && hash_equals( $sha256, hash( 'sha256', $content ) );
	}

	/** Do not disclose whether a stranger's inquiry or report exists. */
	private static function missing(): WP_Error {
		return new WP_Error( 'planning_report_not_found', __( 'This document is not available.', 'linker-commerce' ), array( 'status' => 404 ) );
	}
}

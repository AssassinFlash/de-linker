<?php
/**
 * Native public comment submissions and the unused pingback write transport.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_REST_Request;

/** Blog reading and native staff moderation keep their existing behavior. */
final class Comments {
	/**
	 * Current native comment admission.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $permit = null;

	/** Native hooks run before comment insertion or notification. */
	public function register(): void {
		add_action( 'comment_form_after_fields', array( $this, 'fields' ) );
		add_action( 'comment_form_logged_in_after', array( $this, 'fields' ) );
		add_filter( 'preprocess_comment', array( $this, 'native' ) );
		add_action( 'comment_post', array( $this, 'complete' ) );
		add_filter( 'rest_dispatch_request', array( $this, 'rest' ), 10, 4 );
		add_filter( 'xmlrpc_methods', array( $this, 'xmlrpc' ) );
	}

	/** Append within core's existing comment form. */
	public function fields(): void {
		if ( Business::enabled() && ! current_user_can( 'moderate_comments' ) ) {
			wp_nonce_field( 'linker_comment', 'linker_comment_nonce' );
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Shared escaped fields.
			echo FormFields::render( 'comment' );
		}
	}

	/**
	 * Core's public form calls this before insertion and all comment mail.
	 *
	 * @param array<string,mixed> $comment Native sanitized comment input.
	 * @return array<string,mixed> Unchanged comment on admission.
	 */
	public function native( array $comment ): array {
		if ( ! Business::enabled() || current_user_can( 'moderate_comments' ) || null !== $this->permit ) {
			return $comment;
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Additional native-form nonce checked immediately below.
		$post   = wp_unslash( $_POST );
		$nonce  = $post['linker_comment_nonce'] ?? '';
		$result = 'observe' === Configuration::current()->mode || ( is_string( $nonce ) && wp_verify_nonce( $nonce, 'linker_comment' ) )
			? $this->admit( $post, $comment )
			: new WP_Error( 'linker_comment_verification', __( 'Please verify your comment and try again.', 'linker-commerce' ) );
		if ( is_wp_error( $result ) ) {
			wp_die(
				esc_html( $result->get_error_message() ),
				'',
				array(
					'response'  => 400,
					'back_link' => true,
				)
			);
		}
		return $comment;
	}

	/**
	 * Native REST permissions are checked first; guest REST comments remain closed.
	 *
	 * @param mixed               $result Earlier override.
	 * @param WP_REST_Request     $request Native request.
	 * @param string              $route Matched route.
	 * @param array<string,mixed> $handler Native callback.
	 * @return mixed Native response or refusal.
	 */
	public function rest( mixed $result, WP_REST_Request $request, string $route, array $handler ): mixed {
		unset( $route );
		if ( null !== $result || ! Business::enabled() || current_user_can( 'moderate_comments' ) || 'POST' !== $request->get_method() || 0 !== strcasecmp( '/wp/v2/comments', $request->get_route() ) ) {
			return $result;
		}
		$params  = $request->get_params();
		$payload = $params;
		foreach ( array( 'linker_request_id', 'linker_proof', '_wpnonce', '_locale', 'rest_route' ) as $key ) {
			unset( $payload[ $key ] );
		}
		$allowed = $this->admit( $params, $payload );
		if ( is_wp_error( $allowed ) ) {
			return $allowed;
		}
		try {
			return call_user_func( $handler['callback'], $request );
		} finally {
			// Only the already-admitted native REST callback may reuse this proof.
			$this->permit = null;
		}
	}

	/**
	 * Fixed native input; no country, language or content classification rules.
	 *
	 * @param array<string,mixed> $post Proof transport.
	 * @param array<string,mixed> $payload Native comment input.
	 * @return true|WP_Error
	 */
	private function admit( array $post, array $payload ): true|WP_Error {
		$result = Operation::begin( 'comment', $post, $payload );
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		$this->permit = $result;
		return true;
	}

	/**
	 * Native insertion completed; notification routing stays native.
	 *
	 * @param int $id Comment id.
	 */
	public function complete( int $id ): void {
		if ( null !== $this->permit ) {
			Operation::finish( $this->permit, $id );
			$this->permit = null;
		}
	}

	/**
	 * B2B inquiries have no use for unauthenticated remote-site pingback writes.
	 * Keep authenticated XML-RPC consumers and other native methods available.
	 *
	 * @param array<string,mixed> $methods Native method map.
	 * @return array<string,mixed>
	 */
	public function xmlrpc( array $methods ): array {
		if ( 'enforce' === Configuration::current()->mode ) {
			unset( $methods['pingback.ping'] );
		}
		return $methods;
	}
}

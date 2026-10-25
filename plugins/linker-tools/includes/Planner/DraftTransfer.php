<?php
/**
 * Resolve a native owner's frozen report before Woo receives selected products.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;
use WP_REST_Response;

/** No browser product list or copied Woo field grants project access. */
final class DraftTransfer {
	/**
	 * Reuse the owned command and native write admission, then ask Commerce to write.
	 *
	 * @param Principal           $principal Native authenticated owner.
	 * @param array<string,mixed> $command Bounded intent.
	 * @param Admission           $admission Existing native resource journal.
	 * @param Transport           $transport Private engine transport.
	 * @param string              $mode Server-selected preview, apply or read operation.
	 */
	public function apply( Principal $principal, array $command, Admission $admission, Transport $transport, string $mode = 'apply' ): WP_REST_Response|WP_Error {
		$write          = 'read' !== $mode;
		$engine_command = $command;
		unset( $engine_command['expected_draft_sha256'] );
		$keys = array_keys( $engine_command );
		sort( $keys );
		if ( array( 'expected_revision', 'key', 'project_id', 'report_run_id', 'schema_version' ) !== $keys || 1 !== $command['schema_version'] || ! is_int( $command['expected_revision'] ) || $command['expected_revision'] < 1 || ! is_string( $command['key'] ) || ! wp_is_uuid( $command['key'], 4 ) ) {
			return Failure::make( 'input', 422 );
		}
		foreach ( array( 'project_id', 'report_run_id' ) as $field ) {
			if ( ! is_string( $command[ $field ] ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $command[ $field ] ) ) {
				return Failure::make( 'input', 422 );
			}
		}
		if ( 'preview' !== $mode && ( ! is_string( $command['expected_draft_sha256'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $command['expected_draft_sha256'] ) ) ) {
			return Failure::make( 'input', 422 );
		}
		if ( count( $command ) !== count( $engine_command ) + ( 'preview' === $mode ? 0 : 1 ) ) {
			return Failure::make( 'input', 422 );
		}
		$body = wp_json_encode( $engine_command );
		if ( ! is_string( $body ) ) {
			return Failure::make( 'input', 422 );
		}
		// This happens for replays too: a Woo receipt never substitutes for
		// current native ownership of the source project after login/logout.
		$reply = $write ? $admission->send( $principal, 'handoffs/prepare', $engine_command, $body, $transport ) : $transport->call( $principal, 'operations/replay/handoffs/prepare', $body );
		if ( is_wp_error( $reply ) ) {
			return $reply;
		}
		$data = json_decode( $reply['body'], true );
		if ( ! is_array( $data ) || ! str_starts_with( $reply['type'], 'application/json' ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		if ( $reply['status'] >= 400 ) {
			return new WP_REST_Response( $data, $reply['status'] );
		}
		if ( ! $write ) {
			if ( 'absent' === ( $data['status'] ?? null ) ) {
				return new WP_REST_Response(
					array(
						'schema_version' => 1,
						'state'          => 'not_applied',
					)
				);
			}
			if ( 'replayed' !== ( $data['status'] ?? null ) || ! is_array( $data['result'] ?? null ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$data = $data['result'];
		}
		try {
			/**
			 * Commerce applies current Woo product/account/stock rules and saves a receipt.
			 *
			 * @since 0.3.0
			 * @param array<string,mixed>|WP_Error $result Native result, absent by default.
			 * @param array<string,mixed>          $command Verified versioned intent.
			 * @param array<string,mixed>          $data Engine-owned immutable handoff.
			 */
			$result = apply_filters( 'linker_commerce_planning_draft_' . $mode, Failure::make( 'configuration', 503 ), $command, $data ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Shared server-only Commerce writer/reader seam.
		} catch ( \Throwable $error ) {
			return Failure::make( 'unavailable', 503 );
		}
		return is_wp_error( $result ) ? $result : ( is_array( $result ) ? new WP_REST_Response( $result ) : Failure::make( 'invalid_reply', 502 ) );
	}
}

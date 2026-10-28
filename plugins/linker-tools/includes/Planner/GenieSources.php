<?php
/**
 * Revalidate a stored planning-source card against its own native references.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_REST_Request;
use WP_REST_Response;
use WP_Error;

/** Historical cards never inherit the project currently open in the browser. */
final class GenieSources {

	/**
	 * Existing owner-verified read, or the same seam in a focused fixture.
	 *
	 * @param callable(WP_REST_Request,array<string,mixed>,string):?array<string,mixed>|null $read Native context reader.
	 */
	public function __construct( private $read = null ) {}

	/**
	 * Keep legacy events unchanged; a missing proof withholds this card's facts.
	 *
	 * @param string          $stream Stored completed SSE answer.
	 * @param WP_REST_Request $request Current native owner/session proof.
	 * @param string          $locale Current presentation language.
	 * @return string Revalidated stream, without writing the stored transcript.
	 */
	public function restore( string $stream, WP_REST_Request $request, string $locale ): string {
		return self::map( $stream, fn( array $block ): ?array => $this->verified( $block, $request, $locale ) );
	}

	/**
	 * Replayed resource receipts do not carry a fresh native project request.
	 *
	 * @param WP_REST_Response|WP_Error $reply Current permitted replay response.
	 * @param array<string,mixed>       $stored Existing immutable receipt.
	 * @return WP_REST_Response|WP_Error Narrative retained, source card withheld.
	 */
	public static function replayed( WP_REST_Response|WP_Error $reply, array $stored ): WP_REST_Response|WP_Error {
		unset( $stored );
		if ( $reply instanceof WP_Error ) {
			return $reply;
		}
		$data = $reply->get_data();
		if ( is_array( $data ) && is_string( $data['stream'] ?? null ) ) {
			$data['stream'] = self::map(
				$data['stream'],
				static function ( array $block ): ?array {
					unset( $block );
					return null;
				}
			);
			$reply->set_data( $data );
		}
		return $reply;
	}

	/**
	 * Map only this server-owned namespace, preserving all legacy events.
	 *
	 * @param string   $stream Completed SSE stream.
	 * @param callable $verify Exact proof check.
	 * @phpstan-param callable(array<string,mixed>):?array<string,mixed> $verify
	 * @return string Read-only presentation of the stored stream.
	 */
	private static function map( string $stream, callable $verify ): string {
		$events = explode( "\n\n", $stream );
		foreach ( $events as $index => $event ) {
			if ( 1 !== preg_match( '/\Aevent: block\ndata: (.+)\z/s', $event, $match ) ) {
				continue;
			}
			$block = json_decode( $match[1], true );
			if ( ! is_array( $block ) || 'planning_sources' !== ( $block['type'] ?? null ) ) {
				continue;
			}
			$verified         = $verify( $block );
			$events[ $index ] = "event: block\ndata: " . wp_json_encode(
				$verified ?? array(
					'type'           => 'planning_sources',
					'schema_version' => 1,
					'status'         => 'unavailable',
				),
				JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
			);
		}
		return implode( "\n\n", $events );
	}

	/**
	 * Bind every value to the exact stored source and current native owner.
	 *
	 * @param array<string,mixed> $block Original server-owned block.
	 * @param WP_REST_Request     $request Current native request.
	 * @param string              $locale Current presentation language.
	 * @return array<string,mixed>|null Original values with freshly resolved destination.
	 */
	private function verified( array $block, WP_REST_Request $request, string $locale ): ?array {
		$binding = $block['binding'] ?? null;
		if ( 1 !== ( $block['schema_version'] ?? null ) || 'available' !== ( $block['status'] ?? null ) || ! is_array( $binding ) ) {
			return null;
		}
		$reference = GenieContext::reference( $binding );
		if ( array() === $reference ) {
			return null;
		}
		try {
			$fresh = is_callable( $this->read ) ? ( $this->read )( $request, $reference, $locale ) : ( new GenieContext() )->read( $request, $reference, $locale );
		} catch ( \RuntimeException $error ) {
			return null;
		}
		if ( ! is_array( $fresh ) || 'available' !== ( $fresh['status'] ?? null ) || true === ( $fresh['truncated'] ?? false ) || ! is_array( $fresh['runs'] ?? null ) || ( $fresh['project']['id'] ?? null ) !== $reference['planning_project_id'] || ( $fresh['project']['revision'] ?? null ) !== $reference['planning_revision'] || array_column( $fresh['runs'], 'id' ) !== $reference['planning_run_ids'] ) {
			return null;
		}
		$bindings = array();
		$results  = array();
		foreach ( $fresh['runs'] as $run ) {
			if ( 'succeeded' !== ( $run['state'] ?? null ) || true === ( $run['truncated'] ?? false ) ) {
				return null;
			}
			$source = $run['calculation_sources'] ?? null;
			if ( null === $source ) {
				continue;
			}
			if ( ! is_array( $source ) || 1 !== ( $source['schema_version'] ?? null ) || ! is_array( $source['groups'] ?? null ) ) {
				return null;
			}
			$bindings[] = array_intersect_key( $run, array_flip( array( 'id', 'revision', 'manifest_sha256', 'result_sha256' ) ) );
			$results[]  = array(
				'revision' => $run['revision'],
				'groups'   => $source['groups'],
			);
		}
		if ( array() === $results || ( $binding['runs'] ?? null ) !== $bindings || ( $block['results'] ?? null ) !== $results || ! is_string( $fresh['workspace_url'] ?? null ) ) {
			return null;
		}
		$block['url'] = $fresh['workspace_url'];
		return $block;
	}
}

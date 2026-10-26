<?php
/**
 * Read a customer's original saved inputs, without reusing an old calculation.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Account\SavedSolutions;
use WP_Error;
use WP_Post;

/**
 * Native account records are user-input references, never product authority.
 */
final class SavedSolutionSource {


	/**
	 * Resolve only the current account's active saved solution.
	 *
	 * @param  Principal           $principal Verified gateway identity.
	 * @param  array<string,mixed> $command   Bounded source read.
	 * @return array<string,mixed>|WP_Error Original inputs or a private refusal.
	 */
	public function read( Principal $principal, array $command ): array|WP_Error {
		$keys = array_keys( $command );
		sort( $keys );
		if ( array( 'schema_version', 'solution_id' ) !== $keys || 1 !== $command['schema_version'] || ! is_int( $command['solution_id'] ) || $command['solution_id'] <= 0 ) {
			return Failure::make( 'saved_solution_input', 422 );
		}
		$user = get_current_user_id();
		if ( 'user' !== $principal->kind || $user <= 0 || ! class_exists( SavedSolutions::class ) ) {
			return Failure::make( 'saved_solution_unavailable', 404 );
		}
		$post = get_post( $command['solution_id'] );
		if ( ! $post instanceof WP_Post || SavedSolutions::POST_TYPE !== $post->post_type || 'private' !== $post->post_status || $user !== (int) $post->post_author ) {
			return Failure::make( 'saved_solution_unavailable', 404 );
		}
		$raw       = (string) get_post_meta( $post->ID, SavedSolutions::DESIGN_META, true );
		$raw_items = (string) get_post_meta( $post->ID, SavedSolutions::ITEMS_META, true );
		// Reuse the existing project transport budget before decoding old data.
		if ( strlen( $raw ) > Gateway::MAX_BODY_BYTES || strlen( $raw_items ) > Gateway::MAX_BODY_BYTES - strlen( $raw ) ) {
			return Failure::make( 'saved_solution_size', 413 );
		}
		$design = json_decode( $raw, false, Gateway::MAX_JSON_DEPTH );
		$items  = json_decode( $raw_items, false, Gateway::MAX_JSON_DEPTH );
		if ( ! $design instanceof \stdClass || ! is_string( $design->kind ?? null ) || ! ( ( $design->input ?? null ) instanceof \stdClass ) || ! JsonNumbers::supported( $design->input ) || ! is_array( $items ) || ! JsonNumbers::supported( $items ) ) {
			return Failure::make( 'saved_solution_unavailable', 404 );
		}
		// Only original customer inputs and recorded IDs/counts cross this seam.
		// Old snapshots, prices, formulas and product facts are never imported.
		$source  = array(
			'schema_version' => 1,
			'solution_id'    => $post->ID,
			'title'          => $post->post_title,
			'kind'           => $design->kind,
			'input'          => $design->input,
			'recorded_items' => $items,
			'source_sha256'  => hash( 'sha256', $raw ),
		);
		$encoded = wp_json_encode( $source );
		return ! is_string( $encoded ) || strlen( $encoded ) > Gateway::MAX_BODY_BYTES ? Failure::make( 'saved_solution_size', 413 ) : $source;
	}
}

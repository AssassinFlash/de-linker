<?php
/**
 * Current Woo permission at Genie's proxy and receipt boundaries.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Products\Publication;
use Linker\Tools\Protection\EnginePublication;
use WP_Error;
use WP_REST_Response;

/** History remains a snapshot; a replayed turn is a new current read. */
class PublicationGuard {
	/**
	 * Every current candidate/evidence dependency, never a browser-supplied list.
	 *
	 * @return array<string,mixed>|WP_Error
	 */
	public function dependencies(): array|WP_Error {
		if ( ! class_exists( Publication::class ) ) {
			return self::refused();
		}
		$manifest  = Publication::manifest();
		$products  = array();
		$documents = array();
		foreach ( $manifest['products'] as $product ) {
			$products[] = array(
				'product_id'       => $product['product_id'],
				'product_revision' => $product['product_revision'],
			);
		}
		foreach ( $manifest['documents'] as $document ) {
			foreach ( $document['product_ids'] as $product_id ) {
				$documents[] = array(
					'document_id'       => $document['document_id'],
					'document_revision' => $document['document_revision'],
					'product_id'        => $product_id,
				);
			}
		}
		return array(
			'products'               => $products,
			'documents'              => $documents,
			'compatibility_revision' => $manifest['compatibility_revision'],
		);
	}

	/**
	 * Recheck immediately before committing or reusing the current turn.
	 *
	 * @param array<string,mixed> $dependencies Server's original dependency set.
	 * @return true|WP_Error
	 */
	public function validate( array $dependencies ): true|WP_Error {
		if ( ! class_exists( Publication::class ) || true !== ( Publication::validate( $dependencies )['valid'] ?? false ) ) {
			return self::refused();
		}
		return true;
	}

	/**
	 * Keep permission as server-only receipt metadata.
	 *
	 * @param WP_REST_Response    $reply Response being stored.
	 * @param array<string,mixed> $dependencies Current dependency proof.
	 */
	public function remember( WP_REST_Response $reply, array $dependencies ): void {
		EnginePublication::remember( $reply, $dependencies );
	}

	/**
	 * Old Genie receipts contain no permission proof and cannot be replayed.
	 *
	 * @param WP_REST_Response|WP_Error $reply Restored response.
	 * @param array<string,mixed>       $stored Receipt payload.
	 * @return WP_REST_Response|WP_Error
	 */
	public static function restored( WP_REST_Response|WP_Error $reply, array $stored ): WP_REST_Response|WP_Error {
		$data = $stored['data'] ?? null;
		if ( is_array( $data ) && isset( $data['stream'] ) && ( ! is_array( $stored['publication'] ?? null ) || ! array_key_exists( 'products', $stored['publication'] ) || ! array_key_exists( 'documents', $stored['publication'] ) ) ) {
			return self::refused();
		}
		return $reply;
	}

	/** A protocol error; the shell uses its existing failed-turn UI. */
	private static function refused(): WP_Error {
		return new WP_Error( 'linker_genie_publication_changed', 'Current product permission could not be confirmed.', array( 'status' => 409 ) );
	}
}

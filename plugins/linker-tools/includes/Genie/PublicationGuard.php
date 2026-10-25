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
	 * Real current source readers or explicit fixture transports.
	 *
	 * @param callable():array<string,mixed>|null                    $read Current manifest.
	 * @param callable(array<string,mixed>):array<string,mixed>|null $check Fresh validation.
	 */
	public function __construct( private $read = null, private $check = null ) {}

	/**
	 * Every current candidate/evidence dependency, never a browser-supplied list.
	 *
	 * @return array<string,mixed>|WP_Error
	 */
	public function dependencies(): array|WP_Error {
		if ( ! class_exists( Publication::class ) ) {
			return self::refused( 503 );
		}
		try {
			$manifest = is_callable( $this->read ) ? ( $this->read )() : Publication::manifest();
		} catch ( \RuntimeException $error ) {
			return self::refused( 503 );
		}
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
		if ( ! class_exists( Publication::class ) ) {
			return self::refused( 503 );
		}
		try {
			$result = is_callable( $this->check ) ? ( $this->check )( $dependencies ) : Publication::validate( $dependencies );
		} catch ( \RuntimeException $error ) {
			return self::refused( 503 );
		}
		if ( true !== ( $result['valid'] ?? false ) ) {
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
		EnginePublication::remember( $reply, $dependencies, 'genie' );
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

	/** A typed refusal; the shell preserves the message and names the actual reason.
	 *
	 * @param int $status Revocation or unavailable authority.
	 */
	public static function refused( int $status = 409 ): WP_Error {
		return new WP_Error( 503 === $status ? 'linker_genie_publication_unavailable' : 'linker_genie_publication_changed', 503 === $status ? __( 'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.', 'linker-tools' ) : __( 'The product information changed while Genie was answering. Your message is still here.', 'linker-tools' ), array( 'status' => $status ) );
	}
}

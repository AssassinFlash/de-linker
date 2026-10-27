<?php
/**
 * Owned recorded certificate sources, with current native document access.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use WP_Error;
use WP_REST_Response;

/** A historical source identity never grants current product/document access. */
final class CertificateEvidence {

	/**
	 * Read only the selected owned result; native Woo supplies current access.
	 *
	 * @param Principal           $principal Native verified owner.
	 * @param array<string,mixed> $command Result/candidate reference.
	 * @param Transport           $transport Private read transport.
	 * @return WP_REST_Response|WP_Error Historical source view or a bounded failure.
	 */
	public function read( Principal $principal, array $command, Transport $transport ): WP_REST_Response|WP_Error {
		$value = $transport->object( $principal, 'equipment/certificates/read', $command );
		if ( is_wp_error( $value ) ) {
			return $value;
		}
		if ( 1 !== ( $value['schema_version'] ?? null ) || ( $value['run_id'] ?? null ) !== ( $command['run_id'] ?? null ) || ( $value['candidate_id'] ?? null ) !== ( $command['candidate_id'] ?? null ) || 'associated_product_documents' !== ( $value['scope'] ?? null ) || 'not_assessed' !== ( $value['applicability'] ?? null ) || ! is_array( $value['documents'] ?? null ) || ! is_array( $value['products'] ?? null ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		try {
			$manifest = Publication::manifest();
		} catch ( \RuntimeException $error ) {
			$manifest = null;
		}
		return new WP_REST_Response( self::current_access( $value, $manifest ) );
	}

	/**
	 * Compare one native authority read; recorded provenance remains unchanged.
	 *
	 * @param array<string,mixed>      $recorded Owned source projection.
	 * @param array<string,mixed>|null $current Current Woo manifest, null on failure.
	 * @return array<string,mixed> Source projection with separate current access.
	 */
	public static function current_access( array $recorded, ?array $current ): array {
		$products  = array_column( $current['products'] ?? array(), null, 'product_id' );
		$documents = array_column( $current['documents'] ?? array(), null, 'document_id' );
		foreach ( $recorded['documents'] as &$document ) {
			$document['access'] = array(
				'status' => 'unavailable',
				'url'    => null,
			);
			$now                = $documents[ $document['document_id'] ] ?? null;
			if ( ! is_array( $now ) ) {
				continue;
			}
			$members = array_intersect( $document['product_ids'], $now['product_ids'] ?? array() );
			$allowed = false;
			foreach ( $members as $id ) {
				if ( isset( $products[ $id ] ) && in_array( $document['document_id'], $products[ $id ]['documents'] ?? array(), true ) ) {
					$allowed = true;
					break;
				}
			}
			if ( ! $allowed || ! is_string( $now['blob_sha256'] ?? null ) ) {
				continue;
			}
			if ( $now['blob_sha256'] !== $document['blob_sha256'] ) {
				$document['access']['status'] = 'source_changed';
				continue;
			}
			$file = DocumentFiles::locate( $now['url'] );
			if ( null === $file ) {
				continue;
			}
			$document['access'] = array(
				'status'                    => 'available',
				'url'                       => add_query_arg(
					array(
						DocumentAccess::QUERY_VAR         => $file['relative'],
						DocumentAccess::VERSION_QUERY_VAR => $document['blob_sha256'],
					),
					site_url( '/index.php' )
				),
				'current_document_revision' => $now['document_revision'],
			);
		}
		unset( $document );
		return $recorded;
	}
}

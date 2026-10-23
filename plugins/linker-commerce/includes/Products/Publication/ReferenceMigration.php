<?php
/**
 * Adopt the verified reference input into Woo once, without maintaining a copy.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\SelectionFacts;
use WC_Product_Attribute;
use WC_Product_Simple;

/** Migration reruns never overwrite Woo edits, publish a draft, or rebind bytes. */
final class ReferenceMigration {
	/** Generated provenance, not a second manually maintained reference source. */
	public const MIGRATION_META_KEY = '_linker_engineering_migration';

	/**
	 * Preview or apply the single existing reference migration.
	 *
	 * @param array<string,mixed> $input One-time shipped source object.
	 * @param bool                $dry_run Read-only preview.
	 * @return array{action:string,product_id:int,engineering_id:string,figures:int,documents:int}
	 * @throws \RuntimeException When the input or native environment is incomplete.
	 */
	public static function run( array $input, bool $dry_run = true ): array {
		$entries = $input['overlay'] ?? null;
		if ( ! is_array( $entries ) || 1 !== count( $entries ) ) {
			throw new \RuntimeException( 'Expected the single verified reference input.' );
		}
		$entry = reset( $entries );
		if ( ! is_array( $entry ) || 'pv_module' !== ( $entry['kind'] ?? null ) || ! is_string( $entry['id'] ?? null ) || '' === $entry['id'] || ! is_array( $entry['figures'] ?? null ) || ! is_array( $entry['documents'] ?? null ) || ! is_string( $entry['brand'] ?? null ) || ! is_string( $entry['model'] ?? null ) ) {
			throw new \RuntimeException( 'Reference identity, figures and documents are required.' );
		}
		$existing = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ),
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
				'meta_key'                    => EngineeringReference::ID_META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Explicit, bounded migration identity lookup.
				'meta_value'                  => $entry['id'], // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- No runtime catalogue query.
			)
		);
		$existing = array_values( array_unique( array_map( static fn ( int|string $id ): int => \Linker\Commerce\Products\Publication::canonical_id( (int) $id ), $existing ) ) );
		if ( count( $existing ) > 1 ) {
			throw new \RuntimeException( 'Multiple Woo records carry this engineering identity; no record was changed.' );
		}
		$result = array(
			'action'         => $dry_run ? 'would_create' : 'created',
			'product_id'     => 0,
			'engineering_id' => $entry['id'],
			'figures'        => count( $entry['figures'] ),
			'documents'      => count( $entry['documents'] ),
		);
		if ( array() !== $existing ) {
			$id = (int) reset( $existing );
			if ( ! EngineeringReference::is_reference( $id ) ) {
				throw new \RuntimeException( 'The engineering identity belongs to a non-reference product; no record was changed.' );
			}
			$result['action']     = 'unchanged';
			$result['product_id'] = $id;
			return $result;
		}
		$documents = self::documents( $entry['documents'] );
		foreach ( array( 'pa_brand', 'pa_model' ) as $taxonomy ) {
			if ( ! taxonomy_exists( $taxonomy ) ) {
				throw new \RuntimeException( 'Native Woo brand/model attributes must exist before migration.' );
			}
		}
		if ( $dry_run ) {
			return $result;
		}
		$product = new WC_Product_Simple();
		$product->set_name( $entry['brand'] . ' ' . $entry['model'] );
		$product->set_status( 'draft' );
		EngineeringReference::configure( $product );
		$product->update_meta_data( EngineeringReference::ROLE_META_KEY, EngineeringReference::PV_MODULE );
		$product->update_meta_data( EngineeringReference::ID_META_KEY, $entry['id'] );
		$product->update_meta_data( self::MIGRATION_META_KEY, 'woo-reference-v1' );
		// Associations exist before figures are written, so the normal event binds
		// only the current explicitly associated bytes on this first adoption.
		$product->update_meta_data( EngineeringData::DOCUMENTS_META_KEY, $documents );
		$product->update_meta_data( '_linker_documents_managed', '1' );
		$id                   = $product->save();
		$result['product_id'] = $id;
		try {
			$attributes = array();
			foreach ( array( 'brand', 'model' ) as $name ) {
				$taxonomy = 'pa_' . $name;
				$terms    = wp_set_object_terms( $id, $entry[ $name ], $taxonomy );
				if ( is_wp_error( $terms ) ) {
					throw new \RuntimeException( 'Cannot assign the native reference attributes.' );
				}
				// The assignment returns term_taxonomy_ids; Woo attribute options
				// resolve integer values as term_ids. Read the actual assigned terms.
				$term_ids = wp_get_object_terms( $id, $taxonomy, array( 'fields' => 'ids' ) );
				if ( is_wp_error( $term_ids ) || array() === $term_ids ) {
					throw new \RuntimeException( 'Cannot read the assigned native reference attribute terms.' );
				}
				$attribute = new WC_Product_Attribute();
				$attribute->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
				$attribute->set_name( $taxonomy );
				$attribute->set_options( array_map( 'intval', $term_ids ) );
				$attribute->set_visible( true );
				$attributes[] = $attribute;
			}
			$product->set_attributes( $attributes );
			$product->save();
			// Woo assigns the default category to an empty list during create;
			// remove that native default too. References have no product category.
			wp_delete_object_term_relationships( $id, 'product_cat' );
			update_post_meta( $id, SelectionFacts::FIGURES_META_KEY, $entry['figures'] );
			EvidenceBindings::capture( $id, true );
			if ( function_exists( 'pll_set_post_language' ) ) {
				pll_set_post_language( $id, 'en' );
			}
			$product->set_status( 'publish' );
			$product->save();
			wp_delete_object_term_relationships( $id, 'product_cat' );
			( new PreparationJobs() )->changed();
		} catch ( \Throwable $error ) {
			$product->set_status( 'draft' );
			$product->save();
			// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI diagnostic, never rendered HTML; retain the original exception.
			throw new \RuntimeException( 'Reference adoption stopped; the retained Woo record is draft: ' . $id, 0, $error );
		}
		return $result;
	}

	/**
	 * Reverse this migration's public effect without deleting source data/files.
	 *
	 * @param int  $id Created Woo identity from the migration result.
	 * @param bool $dry_run Preview only.
	 * @return array{action:string,product_id:int}
	 * @throws \RuntimeException When the record was not created by this migration.
	 */
	public static function withdraw( int $id, bool $dry_run = true ): array {
		$product = wc_get_product( $id );
		if ( ! $product instanceof \WC_Product || ! EngineeringReference::is_reference( $id ) || 'woo-reference-v1' !== get_post_meta( $id, self::MIGRATION_META_KEY, true ) ) {
			throw new \RuntimeException( 'Only the reference created by this migration can be withdrawn here.' );
		}
		if ( ! $dry_run ) {
			$product->set_status( 'draft' );
			$product->save();
		}
		return array(
			'action'     => $dry_run ? 'would_withdraw' : 'withdrawn',
			'product_id' => $id,
		);
	}

	/**
	 * Resolve the retained PDFs before creating any record. Never download or grant
	 * permission to a private attachment as part of importing its metadata.
	 *
	 * @param array<int|string,mixed> $rows One-time document rows.
	 * @return list<array<string,mixed>>
	 * @throws \RuntimeException When an original is absent or actively withdrawn.
	 */
	private static function documents( array $rows ): array {
		$documents = array();
		foreach ( $rows as $row ) {
			$file = is_array( $row ) && is_string( $row['url'] ?? null ) ? DocumentFiles::resolve( $row['url'] ) : null;
			if ( null === $file ) {
				throw new \RuntimeException( 'Every original reference PDF must already be present in this site uploads directory.' );
			}
			$attachment = attachment_url_to_postid( $file['url'] );
			if ( $attachment > 0 && ( '0' === get_post_meta( $attachment, '_linker_document_public', true ) || ! in_array( get_post_status( $attachment ), array( 'inherit', 'publish' ), true ) ) ) {
				throw new \RuntimeException( 'A reference PDF is explicitly withdrawn; migration does not restore it.' );
			}
			$row['url']  = $file['url'];
			$documents[] = $row;
		}
		if ( array() === $documents ) {
			throw new \RuntimeException( 'Reference documents are required.' );
		}
		return $documents;
	}
}

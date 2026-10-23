<?php
/**
 * Native WordPress/Woo events and technical-document controls.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/** All native writers converge here; current permission does not wait for hooks. */
final class Module {
	/** Register native mutation, file and media-library hooks. */
	public function register(): void {
		( new Visibility() )->register();
		$jobs   = new PreparationJobs();
		$access = new DocumentAccess();
		add_action( 'rest_api_init', array( new Controller(), 'register_routes' ) );
		add_action( 'linker_publication_reconcile', array( $jobs, 'reconcile' ) );
		foreach ( array( 'save_post_product', 'transition_post_status', 'deleted_post', 'set_object_terms', 'added_post_meta', 'updated_post_meta', 'deleted_post_meta', 'add_attachment', 'edit_attachment', 'delete_attachment', 'pll_save_post', 'edited_term', 'created_term', 'delete_term', 'woocommerce_update_product', 'wp_update_attachment_metadata' ) as $hook ) {
			add_action( $hook, array( $jobs, 'changed' ) );
		}
		foreach ( array( 'added_post_meta', 'updated_post_meta', 'deleted_post_meta' ) as $hook ) {
			add_action( $hook, array( $this, 'managed_documents' ), 10, 3 );
		}
		add_action( 'template_redirect', array( $access, 'serve' ), 0 );
		add_filter( 'mod_rewrite_rules', array( $access, 'rewrite_rules' ) );
		add_filter( 'attachment_fields_to_edit', array( $this, 'attachment_fields' ), 10, 2 );
		add_filter( 'attachment_fields_to_save', array( $this, 'save_attachment' ), 10, 2 );
	}

	/**
	 * Once normal writers maintain the document list, old presentation data cannot restore removed rows.
	 *
	 * @param int|array<int> $meta_id Changed metadata identity.
	 * @param int            $id Post ID.
	 * @param string         $key Changed metadata key.
	 */
	public function managed_documents( int|array $meta_id, int $id, string $key ): void {
		if ( \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY === $key && 'product' === get_post_type( $id ) ) {
			EvidenceBindings::capture( $id );
		}
		if ( \Linker\Commerce\Products\Faqs::META_KEY === $key && 'product' === get_post_type( $id ) ) {
			EvidenceBindings::capture_faqs( $id );
		}
		if ( \Linker\Commerce\Products\EngineeringData::DOCUMENTS_META_KEY === $key && 'product' === get_post_type( $id ) ) {
			update_post_meta( $id, '_linker_documents_managed', '1' );
		}
	}

	/**
	 * Extend the existing Woo/media maintenance entry.
	 *
	 * @param array<string,mixed> $fields Media fields.
	 * @param \WP_Post            $post Attachment.
	 * @return array<string,mixed>
	 */
	public function attachment_fields( array $fields, \WP_Post $post ): array {
		if ( 'application/pdf' === $post->post_mime_type ) {
			$fields['linker_document_public'] = array(
				'label' => __( 'Public technical document', 'linker-commerce' ),
				'input' => 'html',
				'html'  => '<input type="hidden" name="attachments[' . $post->ID . '][linker_document_public]" value="0"><input type="checkbox" name="attachments[' . $post->ID . '][linker_document_public]" value="1" ' . checked( '0' !== (string) get_post_meta( $post->ID, '_linker_document_public', true ), true, false ) . '>',
				'helps' => __( 'Requires an associated published product. Clear to withdraw this document from every product.', 'linker-commerce' ),
			);
		}
		return $fields;
	}

	/**
	 * Persist explicit document withdrawal with normal WordPress metadata.
	 *
	 * @param array<string,mixed> $post Media post fields.
	 * @param array<string,mixed> $attachment Submitted media fields.
	 * @return array<string,mixed>
	 */
	public function save_attachment( array $post, array $attachment ): array {
		if ( isset( $attachment['linker_document_public'] ) && current_user_can( 'edit_post', (int) $post['ID'] ) ) {
			update_post_meta( (int) $post['ID'], '_linker_document_public', '1' === $attachment['linker_document_public'] ? '1' : '0' );
		}
		return $post;
	}
}

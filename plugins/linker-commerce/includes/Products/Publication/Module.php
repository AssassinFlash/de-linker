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
		( new \Linker\Commerce\Products\EngineeringReference() )->register();
		( new CompatibilityEditor() )->register();
		$jobs   = new PreparationJobs();
		$access = new DocumentAccess();
		add_action( 'rest_api_init', array( new Controller(), 'register_routes' ) );
		add_action( 'linker_publication_reconcile', array( $jobs, 'reconcile' ) );
		foreach ( array( 'save_post_product', 'set_object_terms', 'deleted_term_relationships', 'add_attachment', 'edit_attachment', 'delete_attachment', 'pll_save_post', 'woocommerce_update_product' ) as $hook ) {
			add_action( $hook, array( $this, 'source_changed' ) );
		}
		add_action( 'woocommerce_after_product_object_save', array( $this, 'product_saved' ) );
		add_action( 'transition_post_status', array( $this, 'status_changed' ), 10, 3 );
		add_action( 'deleted_post', array( $this, 'source_deleted' ), 10, 2 );
		foreach ( array( 'edited_term', 'created_term', 'delete_term' ) as $hook ) {
			add_action( $hook, array( $this, 'term_changed' ), 10, 3 );
		}
		foreach ( array( 'added_post_meta', 'updated_post_meta', 'deleted_post_meta' ) as $hook ) {
			add_action( $hook, array( $this, 'metadata_changed' ), 10, 3 );
			add_action( $hook, array( $this, 'managed_documents' ), 10, 3 );
		}
		add_action( 'template_redirect', array( $access, 'serve' ), 0 );
		add_filter( 'mod_rewrite_rules', array( $access, 'rewrite_rules' ) );
		add_filter( 'attachment_fields_to_edit', array( $this, 'attachment_fields' ), 10, 2 );
		add_filter( 'attachment_fields_to_save', array( $this, 'save_attachment' ), 10, 2 );
	}

	/**
	 * Product and technical-PDF events have their source ID as the first argument.
	 *
	 * @param int $id Native post identity.
	 */
	public function source_changed( int $id ): void {
		$post = get_post( $id );
		if ( $post instanceof \WP_Post && self::is_source( $post ) ) {
			( new PreparationJobs() )->changed();
		}
	}

	/**
	 * The editor, Woo REST and CRUD reach this after object metadata is persisted.
	 * Earlier WordPress status/save events only queue; they may still see old fields.
	 *
	 * @param \WC_Product $product Fully saved Woo object.
	 */
	public function product_saved( \WC_Product $product ): void {
		EvidenceBindings::capture_missing( $product->get_id() );
		$this->source_changed( $product->get_id() );
	}

	/**
	 * Metadata actions identify their owning post in the second argument.
	 * Attachment metadata is observed after persistence, never by replacing its filter value.
	 *
	 * @param int|array<int> $meta_id Native metadata identity or deleted identities.
	 * @param int            $id Owning post.
	 * @param string         $key Changed metadata key.
	 */
	public function metadata_changed( int|array $meta_id, int $id, string $key ): void {
		unset( $meta_id );
		$post = get_post( $id );
		if ( ! $post instanceof \WP_Post || ! self::is_source( $post ) ) {
			return;
		}
		if ( 'product' === $post->post_type || in_array( $key, array( '_wp_attached_file', '_wp_attachment_metadata', '_linker_document_public' ), true ) ) {
			( new PreparationJobs() )->changed();
		}
	}

	/**
	 * Native status transitions pass the post third, rather than a post ID first.
	 *
	 * @param string   $new_status New post status.
	 * @param string   $old_status Previous post status.
	 * @param \WP_Post $post Changed source.
	 */
	public function status_changed( string $new_status, string $old_status, \WP_Post $post ): void {
		unset( $new_status, $old_status );
		if ( self::is_source( $post ) ) {
			( new PreparationJobs() )->changed();
		}
	}

	/**
	 * After deletion, the supplied snapshot is authoritative for the source type.
	 *
	 * @param int      $id Deleted identity.
	 * @param \WP_Post $post Native snapshot of the deleted source.
	 */
	public function source_deleted( int $id, \WP_Post $post ): void {
		unset( $id );
		if ( self::is_source( $post ) ) {
			( new PreparationJobs() )->changed();
		}
	}

	/**
	 * Woo product taxonomies and attributes can change the current product facts.
	 *
	 * @param int    $id Native term ID.
	 * @param int    $taxonomy_id Native term-taxonomy ID.
	 * @param string $taxonomy Native taxonomy name.
	 */
	public function term_changed( int $id, int $taxonomy_id, string $taxonomy ): void {
		unset( $id, $taxonomy_id );
		if ( str_starts_with( $taxonomy, 'pa_' ) || str_starts_with( $taxonomy, 'product_' ) ) {
			( new PreparationJobs() )->changed();
		}
	}

	/**
	 * Queued mail, inquiries, conversation history and ordinary posts are not product sources.
	 *
	 * @param \WP_Post $post Current post or native deletion snapshot.
	 */
	private static function is_source( \WP_Post $post ): bool {
		return 'product' === $post->post_type || ( 'attachment' === $post->post_type && 'application/pdf' === $post->post_mime_type );
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
			update_post_meta( \Linker\Commerce\Products\Publication::canonical_id( $id ), '_linker_faqs_managed', '1' );
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

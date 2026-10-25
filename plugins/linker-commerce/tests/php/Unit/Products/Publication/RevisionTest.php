<?php
/**
 * Publication revisions distinguish product evidence from translation job state.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Retry bookkeeping cannot revoke unchanged product/document dependencies.
 *
 * @covers \Linker\Commerce\Products\Publication
 */
final class RevisionTest extends TestCase {

	use CurrentFaqProduct;

	/** One currently published product with a real hosted document. */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product( 12, array() );
	}

	/** Remove only this unit fixture's generated file. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** The observed retry error-to-queued change preserves current dependencies. */
	public function test_translation_retry_note_does_not_change_current_dependencies(): void {
		$this->current_faq_meta['_linker_i18n_status'] = array( 'pending' );
		$this->current_faq_meta['_linker_i18n_note']   = array( 'DeepSeek unreachable' );
		$before                                        = Publication::manifest();
		$this->current_faq_meta['_linker_i18n_note']   = array( 'queued' );
		$stored                                        = $this->current_faq_meta;
		$after = Publication::manifest();

		$this->assertSame( $before['source_revision'], $after['source_revision'] );
		$this->assertSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertSame( $before['documents'], $after['documents'] );
		$this->assertTrue( $this->initial_dependencies_are_valid( $before ) );
		$this->assertSame( $stored, $this->current_faq_meta );
	}

	/** Added, removed and changed translation state remains observable bookkeeping. */
	public function test_translation_state_lifecycle_preserves_source_and_stored_metadata(): void {
		$before = Publication::manifest();
		foreach ( array( 'pending', 'synced', 'failed', 'structure_mismatch' ) as $status ) {
			$this->current_faq_meta['_linker_i18n_status'] = array( $status );
			$this->current_faq_meta['_linker_i18n_note']   = array( 'Current translation diagnostic.' );
			$stored                                        = $this->current_faq_meta;
			$after = Publication::manifest();
			$this->assertSame( $before['source_revision'], $after['source_revision'], $status );
			$this->assertSame( $stored, $this->current_faq_meta );
		}
		unset( $this->current_faq_meta['_linker_i18n_note'] );
		$this->assertSame( $before['source_revision'], Publication::manifest()['source_revision'] );
		unset( $this->current_faq_meta['_linker_i18n_status'] );
		$this->assertSame( $before['source_revision'], Publication::manifest()['source_revision'] );
		$this->assertTrue( $this->initial_dependencies_are_valid( $before ) );
	}

	/** A real Woo product-content edit still invalidates the earlier dependency. */
	public function test_product_content_changes_source_and_product_revision(): void {
		$before = Publication::manifest();
		WP_Mock::userFunction( 'get_post' )->with( 12 )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'           => 12,
					'post_title'   => 'Prepared FAQ fixture',
					'post_content' => 'Updated product installation information.',
					'post_excerpt' => '',
					'post_name'    => 'prepared-faq',
				)
			)
		);
		$after = Publication::manifest();
		$this->assertNotSame( $before['source_revision'], $after['source_revision'] );
		$this->assertNotSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertSame( $before['documents'], $after['documents'] );
		$this->assertFalse( $this->initial_dependencies_are_valid( $before ) );
	}

	/** Same-URL replacement still revokes old document and product revisions. */
	public function test_document_bytes_change_source_and_revoke_previous_dependencies(): void {
		$before = Publication::manifest();
		file_put_contents( $this->publication_uploads . '/2026/manual.pdf', "%PDF-1.4\nCurrent replacement evidence.\n%%EOF" );
		$after = Publication::manifest();
		$this->assertSame( $before['documents'][0]['document_id'], $after['documents'][0]['document_id'] );
		$this->assertNotSame( $before['documents'][0]['document_revision'], $after['documents'][0]['document_revision'] );
		$this->assertNotSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertNotSame( $before['source_revision'], $after['source_revision'] );
		$this->assertFalse( $this->initial_dependencies_are_valid( $before ) );
	}

	/** Removing the Woo association still removes current document permission. */
	public function test_document_relation_removal_changes_source_and_revokes_dependencies(): void {
		$before = Publication::manifest();
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array();
		$after = Publication::manifest();
		$this->assertSame( array(), $after['documents'] );
		$this->assertNotSame( $before['source_revision'], $after['source_revision'] );
		$this->assertNotSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertFalse( $this->initial_dependencies_are_valid( $before ) );
	}

	/**
	 * Exercise the public dependency contract against the fixture's next read.
	 *
	 * @param array<string,mixed> $manifest Earlier actual publication read.
	 */
	private function initial_dependencies_are_valid( array $manifest ): bool {
		$result = Publication::validate(
			array(
				'products'  => array(
					array(
						'product_id'       => 12,
						'product_revision' => $manifest['products'][0]['product_revision'],
					),
				),
				'documents' => array(
					array(
						'document_id'       => $manifest['documents'][0]['document_id'],
						'document_revision' => $manifest['documents'][0]['document_revision'],
						'product_id'        => 12,
					),
				),
			)
		);
		return $result['valid'];
	}
}

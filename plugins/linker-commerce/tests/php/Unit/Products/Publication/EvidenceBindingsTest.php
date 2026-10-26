<?php
/**
 * Cited FAQ identity and evidence changes, backed by actual replacement bytes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\Publication\Module;
use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;

/**
 * Preparation and row movement cannot change a recorded answer's source bytes.
 *
 * @covers \Linker\Commerce\Products\Publication\EvidenceBindings
 * @covers \Linker\Commerce\Products\Publication::faqs_for
 */
final class EvidenceBindingsTest extends TestCase {
	use CurrentFaqProduct;

	/** Two deliberately bound current source answers. */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product(
			12,
			array(
				array(
					'question' => 'Alpha?',
					'answer'   => 'Recorded alpha.',
					'citation' => array(
						'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
						'page' => 7,
					),
				),
				array(
					'question' => 'Beta?',
					'answer'   => 'Recorded beta.',
					'citation' => array(
						'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
						'page' => 19,
					),
				),
			)
		);
	}

	/** Remove only this unit's generated files. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Replacement bytes remove the answer and page together, preserving editor data. */
	public function test_replacement_removes_current_answers_without_deleting_them(): void {
		$this->assertCount( 2, Publication::faqs_for( 12 ) );
		$this->assertCount( 2, Publication::faqs_for( 12, Publication::library_read() ) );
		$this->replace_pdf();
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
		$this->assertSame( array(), Publication::faqs_for( 12, Publication::library_read() ) );
		$this->assertCount( 2, Faqs::of( 12 ) );
	}

	/** Library metadata never supplies uninspected bytes to a cited answer. */
	public function test_library_lists_uncited_metadata_but_checks_cited_alias_bytes(): void {
		$base = 'https://de-linker.com/wp-content/uploads/2026/';
		$this->assertTrue( copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/alias.pdf' ) );
		$this->assertTrue( copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/brochure.pdf' ) );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array(
			array(
				'url'     => $base . 'manual.pdf',
				'aliases' => array( $base . 'alias.pdf' ),
			),
			array( 'url' => $base . 'brochure.pdf' ),
		);
		foreach ( $this->current_faq_meta[ Faqs::META_KEY ] as &$entry ) {
			$entry['citation']['url'] = $base . 'alias.pdf';
		}
		unset( $entry );
		EvidenceBindings::capture_faqs( 12 );
		$full    = Publication::manifest();
		$library = Publication::library_read();
		$this->assertSame( array( 'products', 'documents' ), array_keys( $library ) );
		$this->assertCount( 2, $library['documents'] );
		$this->assertSame( Publication::faqs_for( 12, $full ), Publication::faqs_for( 12, $library ) );
		$this->assertCount( 2, Publication::faqs_for( 12, $library ) );
		foreach ( $library['documents'] as $document ) {
			$this->assertArrayNotHasKey( 'document_revision', $document );
			if ( $base . 'brochure.pdf' === $document['url'] ) {
				$this->assertNull( $document['blob_sha256'] );
			} else {
				$this->assertSame( hash_file( 'sha256', $this->publication_uploads . '/2026/manual.pdf' ), $document['blob_sha256'] );
			}
		}
		file_put_contents( $this->publication_uploads . '/2026/alias.pdf', "%PDF-1.4\ndifferent alias bytes\n%%EOF" );
		$this->assertSame( array(), Publication::faqs_for( 12, Publication::library_read() ) );
		unlink( $this->publication_uploads . '/2026/brochure.pdf' );
		$this->assertCount( 1, Publication::library_read()['documents'] );
	}

	/** An unchanged answer cannot acquire fresh evidence because of a list operation. */
	public function test_adoption_equivalent_save_and_reordering_preserve_old_bindings(): void {
		$before = $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ];
		$this->replace_pdf();
		EvidenceBindings::capture_faqs( 12, true );
		( new Module() )->managed_documents( 1, 12, Faqs::META_KEY );
		$this->current_faq_meta[ Faqs::META_KEY ] = array_reverse( $this->current_faq_meta[ Faqs::META_KEY ] );
		( new Module() )->managed_documents( 1, 12, Faqs::META_KEY );
		$this->assertEqualsCanonicalizing( $before, $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
	}

	/** A real content correction binds only that changed answer to current bytes. */
	public function test_changed_answer_binds_only_its_current_source(): void {
		$this->replace_pdf();
		$this->current_faq_meta[ Faqs::META_KEY ][0]['answer']           = 'Current corrected alpha.';
		$this->current_faq_meta[ Faqs::META_KEY ][0]['citation']['page'] = 21;
		( new Module() )->managed_documents( 1, 12, Faqs::META_KEY );
		$current = Publication::faqs_for( 12 );
		$this->assertCount( 1, $current );
		$this->assertSame( 'Current corrected alpha.', $current[0]['answer'] );
		$this->assertSame( 21, $current[0]['citation']['page'] );
	}

	/** Published files alone grant no permission to an unbound answer. */
	public function test_unbound_answer_is_not_a_current_answer(): void {
		unset( $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
	}

	/** Same URL, different real PDF bytes. */
	private function replace_pdf(): void {
		$file = DocumentFiles::resolve( 'https://de-linker.com/wp-content/uploads/2026/manual.pdf' );
		$this->assertNotNull( $file );
		file_put_contents( $file['path'], "%PDF-1.4\nnew document bytes\n%%EOF" );
	}
}

<?php
/**
 * A binding whose cited bytes did not change is renewed, not re-adopted.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use Linker\Commerce\Tests\TestCase;

/**
 * `bind-figures` preserves recorded bindings, so an entry whose own text moved
 * while its document and bytes stayed keeps a stale revision and leaves the
 * feed. The repair renews exactly that and never adopts a replaced file.
 *
 * @covers \Linker\Commerce\Products\Publication\EvidenceBindings::repair_unchanged
 */
final class RepairBindingsTest extends TestCase {

	use CurrentFaqProduct;

	/**
	 * The product's only figure, citing the hosted manual.
	 *
	 * @var array<string,mixed>
	 */
	private array $figure = array(
		'value'    => '10',
		'unit'     => 'kW',
		'citation' => array(
			'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
			'page' => 1,
		),
	);

	/** A published product with one bound, current figure. */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product( 12, array() );
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ] = array(
			'rated_ac_power_kw' => $this->figure,
		);
		EvidenceBindings::capture( 12, true );
	}

	/** Remove only this unit's generated files. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** The bound entry is current before anything is changed. */
	public function test_the_fixture_binds_and_projects_the_figure(): void {
		$this->assertArrayHasKey( 'rated_ac_power_kw', Publication::figures_for( 12 ) );
		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
	}

	/** A citation rewritten to name the same file renews once the file is rechecked. */
	public function test_an_entry_whose_citation_changed_to_the_same_file_is_renewed(): void {
		$before = get_post_meta( 12, EvidenceBindings::META_KEY, true );
		// The real drift: a citation stored as a document label instead of its URL.
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ] = array(
			'rated_ac_power_kw' => array(
				'value'    => '10',
				'unit'     => 'kW',
				'citation' => array(
					'doc'  => 'manual.pdf',
					'page' => 1,
				),
			),
		);
		$this->assertSame( array(), Publication::figures_for( 12 ) );

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12 ) );

		$after = get_post_meta( 12, EvidenceBindings::META_KEY, true );
		$this->assertSame( $before['rated_ac_power_kw']['document_id'], $after['rated_ac_power_kw']['document_id'] );
		$this->assertSame( $before['rated_ac_power_kw']['blob_sha256'], $after['rated_ac_power_kw']['blob_sha256'] );
		$this->assertNotSame( $before['rated_ac_power_kw']['figure_revision'], $after['rated_ac_power_kw']['figure_revision'] );
		$this->assertArrayHasKey( 'rated_ac_power_kw', Publication::figures_for( 12 ) );
	}

	/** A dry run reports the same count and leaves the stored binding untouched. */
	public function test_a_dry_run_counts_without_writing(): void {
		$before = get_post_meta( 12, EvidenceBindings::META_KEY, true );
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ]['rated_ac_power_kw']['value_de'] = '10';

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12, true ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::META_KEY, true ) );

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertArrayHasKey( 'rated_ac_power_kw', Publication::figures_for( 12 ) );
	}

	/** Replaced bytes are new evidence: the repair reports nothing and keeps the old binding. */
	public function test_replaced_bytes_are_never_adopted(): void {
		$before = get_post_meta( 12, EvidenceBindings::META_KEY, true );
		$file   = DocumentFiles::resolve( $this->figure['citation']['url'] );
		$this->assertNotNull( $file );
		file_put_contents( $file['path'], "%PDF-1.4\nreplacement bytes\n%%EOF" );
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ]['rated_ac_power_kw']['value_de']         = '10';
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ]['rated_ac_power_kw']['citation']['page'] = 2;

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::META_KEY, true ) );
		$this->assertSame( array(), Publication::figures_for( 12 ) );
	}

	/** An entry citing a document this product does not publish cannot be renewed. */
	public function test_an_unknown_citation_is_left_unbound(): void {
		$before = get_post_meta( 12, EvidenceBindings::META_KEY, true );
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ]['rated_ac_power_kw']['citation']['url'] = 'https://de-linker.com/wp-content/uploads/2026/other.pdf';

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::META_KEY, true ) );
	}

	/** A product without recorded bindings has nothing to renew. */
	public function test_no_binding_means_no_repair(): void {
		$this->current_faq_meta[ EvidenceBindings::META_KEY ] = array();
		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( array(), $this->current_faq_meta[ EvidenceBindings::META_KEY ] );
	}

	/** An FAQ whose text changed while its cited PDF stayed the same is renewed. */
	public function test_an_faq_whose_text_changed_against_unchanged_pdf_is_renewed(): void {
		$this->bind_sample_faqs();
		$before = get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true );
		$this->assertCount( 1, Publication::faqs_for( 12 ) );

		$this->current_faq_meta[ Faqs::META_KEY ][0]['answer_de'] = 'Korrigierte deutsche Antwort.';
		$this->assertSame( array(), Publication::faqs_for( 12 ) );

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12 ) );

		$after   = get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true );
		$old_key = array_key_first( $before );
		$new_key = Publication::figure_revision( Faqs::of( 12 )[0] );
		$this->assertNotNull( $old_key );
		$this->assertNotSame( $old_key, $new_key );
		$this->assertArrayNotHasKey( $old_key, $after );
		$this->assertArrayHasKey( $new_key, $after );
		$this->assertSame( $before[ $old_key ]['document_id'], $after[ $new_key ]['document_id'] );
		$this->assertSame( $before[ $old_key ]['blob_sha256'], $after[ $new_key ]['blob_sha256'] );
		$this->assertSame( $new_key, $after[ $new_key ]['figure_revision'] );
		$this->assertCount( 1, Publication::faqs_for( 12 ) );
		$this->assertSame( 'Korrigierte deutsche Antwort.', Publication::faqs_for( 12 )[0]['answer_de'] );
	}

	/** A dry run counts renewable FAQ bindings without writing meta. */
	public function test_faq_dry_run_counts_without_writing(): void {
		$this->bind_sample_faqs();
		$before = get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true );

		$this->current_faq_meta[ Faqs::META_KEY ][0]['answer_de'] = 'Geänderte Antwort.';

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12, true ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true ) );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );

		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertCount( 1, Publication::faqs_for( 12 ) );
	}

	/** An FAQ whose PDF bytes were replaced is never renewed onto the new file. */
	public function test_faq_with_replaced_bytes_is_never_adopted(): void {
		$this->bind_sample_faqs();
		$before = get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true );
		$file   = DocumentFiles::resolve( 'https://de-linker.com/wp-content/uploads/2026/manual.pdf' );
		$this->assertNotNull( $file );
		file_put_contents( $file['path'], "%PDF-1.4\nreplacement bytes\n%%EOF" );
		$this->current_faq_meta[ Faqs::META_KEY ][0]['answer_de'] = 'Korrigierte Antwort.';

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true ) );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
	}

	/** An FAQ citing another document (even with identical bytes) or an unknown URL is never renewed. */
	public function test_faq_with_mismatched_document_id_is_never_renewed(): void {
		$this->bind_sample_faqs();
		$before = get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true );
		$other  = 'https://de-linker.com/wp-content/uploads/2026/other.pdf';
		$this->assertTrue( copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/other.pdf' ) );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ][] = array(
			'url'  => $other,
			'type' => 'datasheet',
		);

		$this->current_faq_meta[ Faqs::META_KEY ][0]['citation']['url'] = $other;

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true ) );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );

		$this->current_faq_meta[ Faqs::META_KEY ][0]['citation']['url'] = 'https://de-linker.com/wp-content/uploads/2026/missing.pdf';
		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( $before, get_post_meta( 12, EvidenceBindings::FAQ_META_KEY, true ) );
	}

	/** A newly added FAQ cannot borrow an already-used or already-consumed binding. */
	public function test_new_unbound_faq_does_not_borrow_existing_binding(): void {
		$this->bind_sample_faqs();
		$this->current_faq_meta[ Faqs::META_KEY ][] = array(
			'question'    => 'Second question?',
			'answer'      => 'Second answer.',
			'question_de' => 'Zweite Frage?',
			'answer_de'   => 'Zweite Antwort.',
			'citation'    => array(
				'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
				'page' => 2,
			),
		);

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertCount( 1, Publication::faqs_for( 12 ) );

		$this->current_faq_meta[ Faqs::META_KEY ][0]['answer_de'] = 'Korrigierte erste Antwort.';
		$this->assertSame( 1, EvidenceBindings::repair_unchanged( 12 ) );
		$faqs = Publication::faqs_for( 12 );
		$this->assertCount( 1, $faqs );
		$this->assertSame( 'Korrigierte erste Antwort.', $faqs[0]['answer_de'] );
	}

	/** An FAQ product without recorded FAQ bindings has nothing to renew. */
	public function test_no_faq_binding_means_no_repair(): void {
		$this->current_faq_meta[ Faqs::META_KEY ]                 = array(
			array(
				'question'    => 'Question?',
				'answer'      => 'Answer.',
				'question_de' => 'Frage?',
				'answer_de'   => 'Antwort.',
				'citation'    => array(
					'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
					'page' => 1,
				),
			),
		);
		$this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] = array();

		$this->assertSame( 0, EvidenceBindings::repair_unchanged( 12 ) );
		$this->assertSame( array(), $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
	}

	/** Bind one FAQ citing the fixture manual, independent of figure bindings. */
	private function bind_sample_faqs(): void {
		$this->current_faq_meta[ Faqs::META_KEY ] = array(
			array(
				'question'    => 'Does it work?',
				'answer'      => 'Yes, with a meter.',
				'question_de' => 'Funktioniert es?',
				'answer_de'   => 'Ja, mit einem Zähler.',
				'citation'    => array(
					'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
					'page' => 1,
				),
			),
		);
		EvidenceBindings::capture_faqs( 12, true );
	}
}

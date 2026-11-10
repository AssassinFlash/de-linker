<?php
/**
 * A binding whose cited bytes did not change is renewed, not re-adopted.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

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
}

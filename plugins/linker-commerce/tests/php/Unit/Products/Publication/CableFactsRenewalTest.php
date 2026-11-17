<?php
/**
 * Cable evidence follows unchanged hosted documents after a local URL rewrite.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\CableFacts;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use Linker\Commerce\Tests\TestCase;

/**
 * Unchanged originals retain their engineering meaning across host rewrites.
 *
 * @covers \Linker\Commerce\Products\Publication\CableFacts
 */
final class CableFactsRenewalTest extends TestCase {
	use CurrentFaqProduct;

	/** Release this test's hosted fixture. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Same bytes and owner permit renewal, including every condition-specific row. */
	public function test_unchanged_cable_sources_renew_without_changing_parameters(): void {
		$manifest = $this->fixture();
		$before   = $this->current_faq_meta[ CableFacts::META_KEY ];
		$this->assertNull( CableFacts::projection( 12, $manifest ) );
		$this->assertSame( 1, CableFacts::renew_unchanged( 12, $manifest, true ) );
		$this->assertSame( $before, $this->current_faq_meta[ CableFacts::META_KEY ] );
		$this->assertSame( 1, CableFacts::renew_unchanged( 12, $manifest ) );
		$this->assertNotNull( CableFacts::projection( 12, $manifest ) );
		$expected                                = $before;
		$revision                                = $manifest['documents'][0]['document_revision'];
		$expected['source']['document_revision'] = $revision;
		$expected['parameter_sets'][0]['source']['document_revision']            = $revision;
		$expected['reference_current_ratings'][0]['source']['document_revision'] = $revision;
		$this->assertSame( $expected, $this->current_faq_meta[ CableFacts::META_KEY ] );
		$this->assertSame( 0, CableFacts::renew_unchanged( 12, $manifest ) );
	}

	/** Replaced bytes or a removed product association must not acquire a new binding. */
	public function test_changed_or_unrelated_documents_remain_unbound(): void {
		$manifest                               = $this->fixture();
		$before                                 = $this->current_faq_meta[ CableFacts::META_KEY ];
		$changed                                = $manifest;
		$changed['documents'][0]['blob_sha256'] = str_repeat( 'f', 64 );
		$this->assertSame( 0, CableFacts::renew_unchanged( 12, $changed ) );
		$manifest['documents'][0]['product_ids'] = array( 99 );
		$this->assertSame( 0, CableFacts::renew_unchanged( 12, $manifest ) );
		$this->assertSame( $before, $this->current_faq_meta[ CableFacts::META_KEY ] );
	}

	/**
	 * A typed cable with one source, resistance condition and current rating.
	 *
	 * @return array<string,mixed> Current authority manifest.
	 */
	private function fixture(): array {
		$this->current_faq_product( 12, array() );
		$manifest = Publication::manifest();
		$document = $manifest['documents'][0];
		$source   = array(
			'document_id'       => $document['document_id'],
			'document_revision' => 'previous-host-revision',
			'blob_sha256'       => $document['blob_sha256'],
			'product_id'        => 12,
			'page'              => 1,
			'quote'             => 'Synthetic cable fixture, not a product specification.',
		);
		$this->current_faq_meta[ CableFacts::META_KEY ] = array(
			'schema_version'            => 1,
			'construction'              => 'single_conductor',
			'core_count'                => 1,
			'cross_section_mm2'         => 4,
			'conductor_material'        => 'copper',
			'insulation'                => 'fixture insulation',
			'source'                    => $source,
			'parameter_sets'            => array(
				array(
					'id'                    => 'dc-fixture',
					'current_kind'          => 'dc',
					'temperature_c'         => 20,
					'frequency_hz'          => null,
					'arrangement'           => null,
					'resistance_ohm_per_km' => 5,
					'reactance_ohm_per_km'  => null,
					'resistance_basis'      => 'maximum',
					'source'                => $source,
				),
			),
			'reference_current_ratings' => array(
				array(
					'id'                            => 'air-fixture',
					'laying'                        => 'single_in_air',
					'ambient_temperature_c'         => 60,
					'rated_conductor_temperature_c' => 120,
					'current_a'                     => 50,
					'source'                        => $source,
				),
			),
		);
		return $manifest;
	}
}

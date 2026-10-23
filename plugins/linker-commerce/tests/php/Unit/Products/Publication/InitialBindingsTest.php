<?php
/**
 * First Woo publication adopts only evidence fields that have never existed.
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
use Linker\Commerce\Products\Publication\Module;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Routine publishing initializes missing evidence without renewing old evidence.
 *
 * @covers \Linker\Commerce\Products\Publication\EvidenceBindings
 * @covers \Linker\Commerce\Products\Publication\Module::product_saved
 */
final class InitialBindingsTest extends TestCase {

	use CurrentFaqProduct;

	/**
	 * Persisted statuses, separate from prewarmed runtime copies.
	 *
	 * @var array<int,string>
	 */
	private array $source_statuses = array(
		12 => 'publish',
		13 => 'publish',
	);

	/**
	 * Native request-local copies.
	 *
	 * @var array<int,string>
	 */
	private array $runtime_statuses = array(
		12 => 'publish',
		13 => 'publish',
	);

	/**
	 * Fresh authority boundaries.
	 *
	 * @var int
	 */
	private int $fresh_reads = 0;

	/** A canonical product with actual hosted bytes and two missing generated keys. */
	public function setUp(): void {
		parent::setUp();
		$url = 'https://de-linker.com/wp-content/uploads/2026/manual.pdf';
		$this->current_faq_product(
			12,
			array(
				array(
					'question' => 'Fixture?',
					'answer'   => 'Fixture answer.',
					'citation' => array(
						'url'  => $url,
						'page' => 1,
					),
				),
			)
		);
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ] = array(
			'rated_ac_power_kw' => array(
				'value'    => 10,
				'unit'     => 'kW',
				'citation' => array(
					'url'  => $url,
					'page' => 1,
				),
			),
		);
		unset( $this->current_faq_meta[ EvidenceBindings::META_KEY ], $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		WP_Mock::userFunction( 'has_filter' )->andReturnUsing( static fn ( string $hook ): bool => 'linker_commerce_facts_product_id' === $hook );
		$this->english_products(
			array(
				12 => 12,
				13 => 12,
			)
		);
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( fn ( int $id ): string => $this->runtime_statuses[ $id ] );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			function (): bool {
				++$this->fresh_reads;
				$this->runtime_statuses = $this->source_statuses;
				return true;
			}
		);
		WP_Mock::userFunction( 'metadata_exists' )->andReturnUsing(
			function ( string $type, int $id, string $key ): bool {
				$this->assertSame( 'post', $type );
				$this->assertSame( 12, $id, 'Bindings belong to the canonical source, not its locale mirror.' );
				$this->assertGreaterThan( 0, $this->fresh_reads, 'Publication must refresh before inspecting binding metadata.' );
				return array_key_exists( $key, $this->current_faq_meta );
			}
		);
	}

	/** Remove only this unit's generated files. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** A normal final Woo save captures unchanged source fields before its final queue signal. */
	public function test_final_woo_save_initializes_canonical_evidence_then_queues_preparation(): void {
		$raw    = $this->source_fields();
		$file   = DocumentFiles::resolve( $raw['documents'][0]['url'] );
		$queued = false;
		WP_Mock::userFunction( 'get_post' )->with( 13 )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'        => 13,
					'post_type' => 'product',
				)
			)
		);
		WP_Mock::userFunction( 'update_option' )->with( 'linker_publication_pending', true, false )->andReturnUsing(
			function () use ( &$queued ): bool {
				$this->assertNotEmpty( $this->current_faq_meta[ EvidenceBindings::META_KEY ] );
				$this->assertNotEmpty( $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
				$queued = true;
				return true;
			}
		);
		WP_Mock::userFunction( 'as_has_scheduled_action' )->andReturn( false );
		WP_Mock::userFunction( 'as_enqueue_async_action' )->with( 'linker_publication_reconcile', array(), 'linker-publication', true )->once()->andReturn( 1 );
		$product = \Mockery::mock( \WC_Product::class );
		$product->shouldReceive( 'get_id' )->andReturn( 13 );
		( new Module() )->product_saved( $product );
		$this->assertTrue( $queued );
		$this->assertSame( 1, $this->fresh_reads );
		$this->assertSame( $raw, $this->source_fields() );
		$this->assertSame( $file, DocumentFiles::resolve( $raw['documents'][0]['url'] ) );
		$this->assertCount( 1, Publication::figures_for( 12 ) );
		$this->assertCount( 1, Publication::faqs_for( 13 ) );
	}

	/** Existing empty or malformed metadata is initialized history, never permission to re-adopt. */
	public function test_existing_empty_binding_keys_are_never_auto_initialized(): void {
		WP_Mock::userFunction( 'wp_upload_dir' )->never();
		foreach ( array( array(), '', null ) as $empty ) {
			$this->current_faq_meta[ EvidenceBindings::META_KEY ]     = $empty;
			$this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] = $empty;
			EvidenceBindings::capture_missing( 12 );
			$this->assertSame( $empty, $this->current_faq_meta[ EvidenceBindings::META_KEY ] );
			$this->assertSame( $empty, $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		}
	}

	/** A missing FAQ key cannot cause the existing figure binding to be rewritten. */
	public function test_each_key_initializes_independently_and_preserves_stale_bindings(): void {
		EvidenceBindings::capture_missing( 12 );
		$figures = $this->current_faq_meta[ EvidenceBindings::META_KEY ];
		$faqs    = $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ];
		$file    = DocumentFiles::resolve( $this->source_fields()['documents'][0]['url'] );
		$this->assertNotNull( $file );
		file_put_contents( $file['path'], "%PDF-1.4\nreplacement bytes\n%%EOF" );
		EvidenceBindings::capture_missing( 12 );
		$this->assertSame( $figures, $this->current_faq_meta[ EvidenceBindings::META_KEY ] );
		$this->assertSame( $faqs, $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		$this->assertSame( array(), Publication::figures_for( 12 ) );
		$this->assertSame( array(), Publication::faqs_for( 12 ) );
		unset( $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
		EvidenceBindings::capture_missing( 13 );
		$this->assertSame( $figures, $this->current_faq_meta[ EvidenceBindings::META_KEY ] );
		$this->assertNotSame( $faqs, $this->current_faq_meta[ EvidenceBindings::FAQ_META_KEY ] );
	}

	/** Fresh source and locale permission both precede initialization, even with warm published copies. */
	public function test_draft_canonical_or_locale_prevents_initialization(): void {
		foreach ( array( 12, 13 ) as $draft ) {
			$this->runtime_statuses          = array(
				12 => 'publish',
				13 => 'publish',
			);
			$this->source_statuses           = array(
				12 => 'publish',
				13 => 'publish',
			);
			$this->source_statuses[ $draft ] = 'draft';
			EvidenceBindings::capture_missing( 13 );
			$this->assertArrayNotHasKey( EvidenceBindings::META_KEY, $this->current_faq_meta );
			$this->assertArrayNotHasKey( EvidenceBindings::FAQ_META_KEY, $this->current_faq_meta );
		}
		$this->assertSame( 2, $this->fresh_reads );
	}

	/** Plain WordPress status writes queue changes but do not claim Woo's final-save boundary. */
	public function test_status_only_wordpress_write_queues_without_initializing_bindings(): void {
		$queued = false;
		WP_Mock::userFunction( 'update_option' )->with( 'linker_publication_pending', true, false )->andReturnUsing(
			static function () use ( &$queued ): bool {
				$queued = true;
				return true;
			}
		);
		WP_Mock::userFunction( 'as_has_scheduled_action' )->andReturn( true );
		$post = new \WP_Post(
			(object) array(
				'ID'        => 12,
				'post_type' => 'product',
			)
		);
		( new Module() )->status_changed( 'publish', 'draft', $post );
		$this->assertTrue( $queued );
		$this->assertSame( 0, $this->fresh_reads );
		$this->assertArrayNotHasKey( EvidenceBindings::META_KEY, $this->current_faq_meta );
		$this->assertArrayNotHasKey( EvidenceBindings::FAQ_META_KEY, $this->current_faq_meta );
	}

	/**
	 * Raw editorial values are distinct from their generated binding metadata.
	 *
	 * @return array{figures:mixed,faqs:mixed,documents:mixed}
	 */
	private function source_fields(): array {
		return array(
			'figures'   => $this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ],
			'faqs'      => $this->current_faq_meta[ Faqs::META_KEY ],
			'documents' => $this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ],
		);
	}
}

<?php
/**
 * Publication revisions distinguish product evidence from translation job state.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringFeed;
use Linker\Commerce\Products\EngineeringFeedController;
use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\Publication\CompatibilityClaims;
use Linker\Commerce\Products\Publication\CompatibilityMigration;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\EvidenceBindings;
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

	/** Reviewed wording never changes evidence identities. */
	public function test_reviewed_document_titles_are_current_display_metadata(): void {
		$english = 'GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)';
		$german  = 'GoodWe Garantie für EV-Ladestationen (Europa, Rev. 1.2, englisches Original)';
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ][0]['title'] = $english;
		$titles = array();
		WP_Mock::userFunction( 'get_option' )->with( Materials::DE_DOCUMENT_TITLES, array() )->andReturnUsing(
			static function () use ( &$titles ): array {
				return $titles;
			}
		);
		$before = Publication::manifest();
		$titles = array( $english => $german );
		$after  = Publication::manifest();
		$this->assertSame( '', $before['documents'][0]['title_de'] );
		$this->assertSame( $english, $after['documents'][0]['title'] );
		$this->assertSame( $german, $after['documents'][0]['title_de'] );
		$this->assertSame( $before['source_revision'], $after['source_revision'] );
		$this->assertSame( $before['documents'][0]['document_revision'], $after['documents'][0]['document_revision'] );
		$this->assertSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$titles = array( strtolower( $english ) => $german );
		$this->assertSame( '', Publication::manifest()['documents'][0]['title_de'] );
	}

	/** Reuse this fresh assembly's terms, keeping miss/error and revision semantics. */
	public function test_primed_terms_preserve_manifest_without_repeating_object_queries(): void {
		$names   = array(
			'pa_model'    => array( 'Z model', 'A model' ),
			'pa_brand'    => array(),
			'product_cat' => new \WP_Error( 'invalid_taxonomy', 'Fixture unavailable taxonomy.' ),
		);
		$queries = 0;
		WP_Mock::userFunction( 'get_object_taxonomies' )->andReturn( array_keys( $names ) );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->times( 3 )->andReturn( true );
		WP_Mock::userFunction( '_prime_post_caches' )->with( array( 12 ), true, true )->times( 3 );
		WP_Mock::userFunction( 'get_object_term_cache' )->with( 12, 'pa_model' )->andReturn(
			false,
			array( (object) array( 'name' => 'Z model' ), (object) array( 'name' => 'A model' ) ),
			array( (object) array( 'name' => 'Changed current model' ) )
		);
		WP_Mock::userFunction( 'get_object_term_cache' )->with( 12, 'pa_brand' )->andReturn( false, array(), array() );
		WP_Mock::userFunction( 'get_object_term_cache' )->with( 12, 'product_cat' )->andReturn( false, $names['product_cat'], $names['product_cat'] );
		foreach ( array_keys( $names ) as $taxonomy ) {
			WP_Mock::userFunction( 'wp_get_object_terms' )->with( 12, $taxonomy, array( 'fields' => 'names' ) )->andReturnUsing(
				static function () use ( &$names, &$queries, $taxonomy ): mixed {
					++$queries;
					return $names[ $taxonomy ];
				}
			);
		}
		$fallback = Publication::manifest();
		$this->assertSame( 3, $queries );
		$queries = 0;
		$reused  = Publication::manifest();
		$this->assertSame( 0, $queries );
		$this->assertSame( $fallback, $reused );
		$this->assertSame( 'A model, Z model', $reused['products'][0]['model'] );
		$changed = Publication::manifest();
		$this->assertSame( 0, $queries );
		$this->assertNotSame( $reused['source_revision'], $changed['source_revision'] );
		$this->assertNotSame( $reused['products'][0]['product_revision'], $changed['products'][0]['product_revision'] );
		$this->assertSame( $reused['documents'], $changed['documents'] );
	}

	/** Only actual declarations enter product identity; recovery/empty fields do not. */
	public function test_compatibility_claim_lifecycle_preserves_uninvolved_identity(): void {
		$before = Publication::manifest();
		$this->current_faq_meta[ CompatibilityClaims::META_KEY ] = '';
		$this->assertSame( $before['products'][0]['product_revision'], Publication::manifest()['products'][0]['product_revision'] );
		$this->current_faq_meta[ CompatibilityMigration::META_KEY ] = array(
			'schema_version' => 1,
			'before'         => '',
		);
		$this->current_faq_meta[ CompatibilityClaims::META_KEY ]    = array(
			'schema_version' => 1,
			'pairs'          => array(),
			'requirements'   => array(),
		);
		$this->assertSame( $before['products'][0]['product_revision'], Publication::manifest()['products'][0]['product_revision'] );
		$this->current_faq_meta[ CompatibilityClaims::META_KEY ]['pairs'][] = array(
			'id'         => 'pending-maintenance',
			'unresolved' => array( 'Evidence still required.' ),
		);
		$declared = Publication::manifest();
		$this->assertNotSame( $before['products'][0]['product_revision'], $declared['products'][0]['product_revision'] );
		$this->current_faq_meta[ CompatibilityClaims::META_KEY ]['pairs'] = array();
		$cleared = Publication::manifest();
		$this->assertNotSame( $declared['products'][0]['product_revision'], $cleared['products'][0]['product_revision'] );
		$this->assertSame( $before['products'][0]['product_revision'], $cleared['products'][0]['product_revision'] );
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
		$stale = DocumentFiles::resolve( 'https://de-linker.com/wp-content/uploads/2026/manual.pdf' );
		$this->assertNotNull( $stale );
		$before = Publication::manifest();
		file_put_contents( $this->publication_uploads . '/2026/manual.pdf', "%PDF-1.4\nCurrent replacement evidence.\n%%EOF" );
		$after = Publication::manifest();
		$this->assertSame( $before['documents'][0]['document_id'], $after['documents'][0]['document_id'] );
		$this->assertNotSame( $before['documents'][0]['document_revision'], $after['documents'][0]['document_revision'] );
		$this->assertNotSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertNotSame( $before['source_revision'], $after['source_revision'] );
		$this->assertFalse( $this->initial_dependencies_are_valid( $before ) );
		$this->assertSame( 410, ( new DocumentAccess() )->response( $stale, 'HEAD' )['status'] );
	}

	/** Removing the Woo association still removes current document permission. */
	public function test_document_relation_removal_changes_source_and_revokes_dependencies(): void {
		$file = DocumentFiles::resolve( 'https://de-linker.com/wp-content/uploads/2026/manual.pdf' );
		$this->assertNotNull( $file );
		$before = Publication::manifest();
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array();
		$after = Publication::manifest();
		$this->assertSame( array(), $after['documents'] );
		$this->assertNotSame( $before['source_revision'], $after['source_revision'] );
		$this->assertNotSame( $before['products'][0]['product_revision'], $after['products'][0]['product_revision'] );
		$this->assertFalse( $this->initial_dependencies_are_valid( $before ) );
		$this->assertSame( 410, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'] );
	}

	/** An old manifest cannot reinstate a withdrawn item or its removed association. */
	public function test_stale_manifest_does_not_override_current_item_and_product_permission(): void {
		$this->current_faq_meta[ SelectionFacts::FIGURES_META_KEY ] = array(
			'rated_ac_power_kw' => array(
				'value'    => 10,
				'unit'     => 'kW',
				'citation' => array(
					'url'  => 'https://de-linker.com/wp-content/uploads/2026/manual.pdf',
					'page' => 1,
				),
			),
		);
		EvidenceBindings::capture( 12, true );
		$stale = Publication::manifest();
		$this->assertCount( 1, Publication::figures_for( 12, $stale ) );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array();
		WP_Mock::userFunction( 'wc_get_product' )->with( 12 )->andReturn( null );
		WP_Mock::userFunction( 'get_the_terms' )->andReturn( array() );
		$item = EngineeringFeed::item( 12, $stale );
		$this->assertNotNull( $item );
		$this->assertSame( array(), $item['documents'] );
		$this->assertSame( array(), (array) $item['figures'] );
		$this->assertSame( 'unknown', $item['ac_power_kw'] );
		WP_Mock::userFunction( 'get_post_status' )->with( 12 )->andReturn( 'draft' );
		$this->assertSame( array(), Publication::figures_for( 12, $stale ) );
		$this->assertFalse( Publication::is_published( 12 ) );
		$this->assertNull( EngineeringFeed::item( 12, $stale ) );
	}

	/**
	 * A product withdrawal or removed Woo association while building the feed
	 * must reject the whole response; a retry reads the new authority.
	 *
	 * @dataProvider engineering_withdrawals
	 * @param string $withdrawal Source change to apply after the first read.
	 */
	public function test_feed_rejects_an_inflight_withdrawal_and_retry_reads_current_source( string $withdrawal ): void {
		$source_status  = 'publish';
		$runtime_status = 'publish';
		$changed        = false;
		WP_Mock::userFunction( 'get_post_status' )->with( 12 )->andReturnUsing(
			static function () use ( &$runtime_status ): string {
				return $runtime_status;
			}
		);
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			static function () use ( &$runtime_status, &$source_status ): bool {
				$runtime_status = $source_status;
				return true;
			}
		);
		WP_Mock::userFunction( 'update_postmeta_cache' )->andReturnUsing(
			function () use ( $withdrawal, &$changed, &$source_status ): array {
				if ( ! $changed ) {
						$changed = true;
					if ( 'product' === $withdrawal ) {
						$source_status = 'draft';
					} else {
						$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array();
					}
				}
				return array();
			}
		);
		WP_Mock::userFunction( 'update_object_term_cache' )->andReturn( array() );
		WP_Mock::userFunction( 'wc_get_product' )->with( 12 )->andReturn( null );
		WP_Mock::userFunction( 'get_the_terms' )->andReturn( array() );
		$request = \Mockery::mock( \WP_REST_Request::class );
		$request->shouldReceive( 'get_param' )->with( 'since' )->andReturn( null );
		$controller = new EngineeringFeedController();
		$error      = $controller->get_items( $request );
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 503, $error->get_error_data()['status'] );
		$retry = $controller->get_items( $request );
		$this->assertNotInstanceOf( \WP_Error::class, $retry );
		$retry = (array) $retry;
		if ( 'product' === $withdrawal ) {
			$this->assertSame( array(), $retry['products'] );
		} else {
			$this->assertSame( array(), $retry['products'][0]['documents'] );
		}
	}

	/**
	 * The two source changes exercised by the feed release check.
	 *
	 * @return array<string,array{string}>
	 */
	public static function engineering_withdrawals(): array {
		return array(
			'product'     => array( 'product' ),
			'association' => array( 'association' ),
		);
	}

	/** The internal projection capability cannot be reused after its read closes. */
	public function test_engineering_figure_reader_expires_after_projection(): void {
		$reader = null;
		Publication::engineering_read(
			static function ( array $manifest, callable $figures ) use ( &$reader ): void {
				$reader = $figures;
			}
		);
		$this->assertIsCallable( $reader );
		$this->expectException( \RuntimeException::class );
		$reader( 12 );
	}

	/** Shared URLs are checked once per assembly, including denied aliases, then read afresh. */
	public function test_shared_attachment_permission_is_fresh_for_each_manifest(): void {
		$url   = 'https://de-linker.com/wp-content/uploads/2026/manual.pdf';
		$alias = 'https://de-linker.com/wp-content/uploads/2026/alias.pdf';
		$this->assertTrue( copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/alias.pdf' ) );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] = array(
			array(
				'url'     => $url,
				'aliases' => array( $alias ),
				'type'    => 'manual',
			),
			array(
				'url'  => $alias,
				'type' => 'manual',
			),
		);
		WP_Mock::userFunction( 'get_posts' )->andReturn( array( 12, 13 ) );
		WP_Mock::userFunction( 'get_post_type' )->with( 13 )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->with( 13 )->andReturn( 'publish' );
		WP_Mock::userFunction( 'get_post' )->with( 13 )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'         => 13,
					'post_title' => 'Second shared-document product',
				)
			)
		);
		$states               = array(
			301 => '1',
			302 => '0',
		);
		$lookups              = array();
		$documents_by_product = array( 13 => $this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ] );
		WP_Mock::userFunction( 'attachment_url_to_postid' )->andReturnUsing(
			static function ( string $document_url ) use ( $url, $alias, &$lookups ): int {
				$lookups[ $document_url ] = ( $lookups[ $document_url ] ?? 0 ) + 1;
				return match ( $document_url ) {
					$url => 301,
					$alias => 302,
					default => 0,
				};
			}
		);
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			function ( int $id, string $key = '' ) use ( &$states, &$documents_by_product ): mixed {
				if ( isset( $states[ $id ] ) ) {
					return '_linker_document_public' === $key ? $states[ $id ] : '';
				}
				$meta = $this->current_faq_meta;
				if ( isset( $documents_by_product[ $id ] ) ) {
					$meta[ EngineeringData::DOCUMENTS_META_KEY ] = $documents_by_product[ $id ];
				}
				return '' === $key ? $meta : ( $meta[ $key ] ?? '' );
			}
		);

		$before = Publication::manifest();
		$this->assertCount( 1, $before['documents'] );
		$this->assertSame( array( 12, 13 ), $before['documents'][0]['product_ids'] );
		$this->assertSame( array( $url ), $before['documents'][0]['aliases'] );
		$this->assertSame(
			array(
				$url   => 1,
				$alias => 1,
			),
			$lookups
		);

		$states[301] = '0';
		$lookups     = array();
		$withdrawn   = Publication::manifest();
		$this->assertSame( array(), $withdrawn['documents'] );
		$this->assertSame(
			array(
				$url   => 1,
				$alias => 1,
			),
			$lookups
		);

		$this->assertSame( array(), Publication::library_read()['documents'] );
		$this->assertSame( array(), Publication::product_library_read( 12 )['documents'] );
		$states   = array(
			301 => '1',
			302 => '1',
		);
		$lookups  = array();
		$restored = Publication::manifest();
		$this->assertCount( 2, $restored['documents'] );
		$this->assertSame(
			array(
				$url   => 1,
				$alias => 1,
			),
			$lookups
		);
		$this->assertNotSame( $before['source_revision'], $restored['source_revision'] );

		$states[302] = '0';
		$lookups     = array();
		$file        = DocumentFiles::resolve( $url );
		$this->assertNotNull( $file );
		$this->assertSame( 200, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'] );
		$this->assertSame( array( $url => 1 ), $lookups, 'A download must not check an unrelated alias.' );

		$lookups = array();
		$file    = DocumentFiles::resolve( $alias );
		$this->assertNotNull( $file );
		$this->assertSame( 410, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'] );
		$this->assertSame(
			array(
				$url   => 1,
				$alias => 1,
			),
			$lookups
		);

		$states[301] = '0';
		$lookups     = array();
		$file        = DocumentFiles::resolve( $url );
		$this->assertNotNull( $file );
		$this->assertSame( 410, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'] );
		$this->assertSame( array( $url => 1 ), $lookups );

		$late = 'https://de-linker.com/wp-content/uploads/2026/later-alias.pdf';
		$this->assertTrue( copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/later-alias.pdf' ) );
		$states[301]              = '1';
		$documents_by_product[13] = array(
			array(
				'url'     => $url,
				'aliases' => array( $late ),
			),
		);
		$file                     = DocumentFiles::resolve( $late );
		$this->assertNotNull( $file );
		$this->assertSame( 410, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'], 'A later shared row cannot add aliases to the first published document record.' );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ][0]['aliases'][] = $late;
		$this->assertSame( 200, ( new DocumentAccess() )->response( $file, 'HEAD' )['status'] );
	}

	/** A product keeps earlier shared metadata and aliases without inspecting unrelated files. */
	public function test_product_read_preserves_shared_rows_without_unrelated_file_checks(): void {
		$url       = 'https://de-linker.com/wp-content/uploads/2026/manual.pdf';
		$alias     = 'https://de-linker.com/wp-content/uploads/2026/alias.pdf';
		$unrelated = 'https://de-linker.com/wp-content/uploads/2026/unrelated.pdf';
		copy( $this->publication_uploads . '/2026/manual.pdf', $this->publication_uploads . '/2026/alias.pdf' );
		file_put_contents( $this->publication_uploads . '/2026/unrelated.pdf', "%PDF-1.4\nOther product evidence.\n%%EOF" );
		$rows                                     = array(
			11 => array(
				array(
					'url'     => $url,
					'title'   => 'Earlier shared title',
					'aliases' => array( $alias ),
				),
			),
			12 => array(
				array(
					'url'     => $url,
					'title'   => 'Later product title',
					'aliases' => array( $alias ),
				),
			),
			14 => array(
				array(
					'url'   => $unrelated,
					'title' => 'Unrelated document',
				),
			),
		);
		$this->current_faq_meta[ Faqs::META_KEY ] = array(
			array(
				'question' => 'Shared source?',
				'answer'   => 'Current shared evidence.',
				'citation' => array(
					'url'  => $alias,
					'page' => 1,
				),
			),
		);
		$read_order                               = array();
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			static function () use ( &$read_order ): bool {
				$read_order[] = 'refresh';
				return true;
			}
		);
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			static function () use ( &$read_order ): array {
				$read_order[] = 'candidates';
				return array( 11, 12, 14 );
			}
		);
		WP_Mock::userFunction( '_prime_post_caches' )->with( array( 11, 12, 14 ), true, true )->andReturnUsing(
			static function () use ( &$read_order ): void {
				$read_order[] = 'prime';
			}
		);
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' );
		WP_Mock::userFunction( 'get_post' )->andReturnUsing(
			static fn ( int $id ): \WP_Post => new \WP_Post(
				(object) array(
					'ID'         => $id,
					'post_title' => 'Current product',
				)
			)
		);
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			function ( int $id, string $key = '' ) use ( $rows ): mixed {
				$meta                                        = $this->current_faq_meta;
				$meta[ EngineeringData::DOCUMENTS_META_KEY ] = $rows[ $id ];
				if ( 12 !== $id ) {
					$meta[ Faqs::META_KEY ] = array();
				}
				return '' === $key ? $meta : ( $meta[ $key ] ?? '' );
			}
		);
		EvidenceBindings::capture_faqs( 12, true );
		$all = Publication::library_read();
		$this->assertSame( array( 'refresh', 'candidates', 'prime' ), $read_order );
		$expected = array_values( array_filter( $all['documents'], static fn ( array $document ): bool => in_array( 12, $document['product_ids'], true ) ) );
		$answers  = Publication::faqs_for( 12, $all );
		$this->assertCount( 1, $answers );
		$lookups = array();
		WP_Mock::userFunction( 'attachment_url_to_postid' )->andReturnUsing(
			static function ( string $document_url ) use ( &$lookups ): int {
				$lookups[ $document_url ] = true;
				return 0;
			}
		);
		$read_order = array();
		$read       = Publication::product_library_read( 12 );
		$this->assertSame( array( 'refresh', 'candidates', 'prime' ), $read_order, 'Independent reads batch native data only after refreshing current permissions.' );
		$this->assertSame( $expected, $read['documents'] );
		$this->assertSame( 'Earlier shared title', $read['documents'][0]['title'] );
		$this->assertSame( $answers, Publication::faqs_for( 12 ) );
		$this->assertArrayNotHasKey( $unrelated, $lookups );

		// The inquiry line also needs uncited legacy aliases, without a full manifest.
		$this->current_faq_meta[ Faqs::META_KEY ]          = array();
		$this->current_faq_meta['_delinker_datasheet_url'] = $alias;
		WP_Mock::userFunction( 'is_wc_endpoint_url' )->andReturn( true );
		WP_Mock::passthruFunction( 'esc_url' );
		WP_Mock::passthruFunction( 'esc_html__' );
		$item = \Mockery::mock( \WC_Order_Item_Product::class );
		$item->allows( 'get_product_id' )->andReturn( 12 );
		$order   = \Mockery::mock( \WC_Order::class );
		$list    = new \Linker\Commerce\Account\InquiryList();
		$lookups = array();
		ob_start();
		$list->datasheet_link( 1, $item, $order );
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'href="' . $url . '"', $html );
		$this->assertArrayNotHasKey( $unrelated, $lookups, 'An inquiry line must not read other products\' files.' );
		file_put_contents( $this->publication_uploads . '/2026/alias.pdf', "%PDF-1.4\nChanged alias bytes.\n%%EOF" );
		ob_start();
		$list->datasheet_link( 1, $item, $order );
		$this->assertSame( '', ob_get_clean(), 'A changed legacy alias cannot authorize this datasheet.' );
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

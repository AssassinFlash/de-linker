<?php
/**
 * Existing unbound drafts publish through the final native Woo save boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\SelectionFacts;
use WC_Product_Simple;

/**
 * Only this fixture's tagged products, files and in-process actions are removed.
 *
 * @coversNothing
 */
final class PublicationInitialBindingsTest extends IntegrationTestCase {

	/** Preserve the existing preparation marker and unrelated scheduler actions. */
	protected function setUp(): void {
		parent::setUp();
		$this->assertSame( 'local', wp_get_environment_type(), 'Never run native publication fixtures outside a local instance.' );
		$pending = get_option( 'linker_publication_pending' );
		$actions = array();
		$record  = static function ( int $id ) use ( &$actions ): void {
			$action = \ActionScheduler::store()->fetch_action( $id );
			if ( 'linker_publication_reconcile' === $action->get_hook() && 'linker-publication' === $action->get_group() ) {
				$actions[] = $id;
			}
		};
		add_action( 'action_scheduler_stored_action', $record );
		add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
		$this->later(
			static function () use ( $pending, &$actions, $record ): void {
				remove_action( 'action_scheduler_stored_action', $record );
				remove_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
				foreach ( $actions as $id ) {
					\ActionScheduler::store()->delete_action( $id );
				}
				if ( false === $pending ) {
					delete_option( 'linker_publication_pending' );
				} else {
					update_option( 'linker_publication_pending', $pending, false );
				}
			}
		);
	}

	/** No edited fact, FAQ, document or PDF byte is needed for an old draft's first publication. */
	public function test_normal_woo_publish_initializes_missing_bindings_without_source_changes(): void {
		[ $product, $file ] = $this->unbound_draft();
		$id                 = $product->get_id();
		$before             = $this->source_snapshot( $id, $file );
		foreach ( $before['metadata'] as $key => $value ) {
			$this->assertFalse( update_post_meta( $id, $key, $value ), 'Native metadata equality deliberately emits no update event.' );
		}
		$this->assertFalse( metadata_exists( 'post', $id, EvidenceBindings::META_KEY ) );
		$this->assertFalse( metadata_exists( 'post', $id, EvidenceBindings::FAQ_META_KEY ) );
		$product->set_status( 'publish' );
		$product->save();
		$this->assert_initial_bindings_and_queue( $id );
		$this->assertSame( $before, $this->source_snapshot( $id, $file ), 'Raw source, fact fingerprint, PDF SHA and document identity did not change.' );
		$manifest = Publication::manifest();
		$this->assertCount( 1, Publication::figures_for( $id, $manifest ) );
		$this->assertCount( 1, Publication::faqs_for( $id, $manifest ) );
		$this->assertNotEmpty( get_post_meta( $id, EvidenceBindings::META_KEY, true ) );
		$this->assertNotEmpty( get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true ) );
	}

	/** Routine draft/publish cannot renew evidence whose original URL now has other bytes. */
	public function test_normal_republish_preserves_stale_bindings(): void {
		[ $product, $file ] = $this->unbound_draft();
		$product->set_status( 'publish' );
		$product->save();
		$id       = $product->get_id();
		$bindings = $this->bindings( $id );
		$this->assertNotEmpty( $bindings[0] );
		$this->assertNotEmpty( $bindings[1] );
		$before = $this->source_snapshot( $id, $file );
		$product->set_status( 'draft' );
		$product->save();
		file_put_contents( $file['path'], "%PDF-1.4\nReplacement initial-binding fixture\n%%EOF\n" );
		$product->set_status( 'publish' );
		$product->save();
		$after = $this->source_snapshot( $id, $file );
		$this->assertSame( $before['metadata'], $after['metadata'] );
		$this->assertSame( $before['figure_revision'], $after['figure_revision'] );
		$this->assertSame( $before['document_id'], $after['document_id'] );
		$this->assertNotSame( $before['blob_sha256'], $after['blob_sha256'] );
		$this->assertSame( $bindings, $this->bindings( $id ) );
		$manifest = Publication::manifest();
		$this->assertSame( array(), Publication::figures_for( $id, $manifest ) );
		$this->assertSame( array(), Publication::faqs_for( $id, $manifest ) );
	}

	/** Final relation removal, withdrawal and an existing empty binding all remain authoritative. */
	public function test_normal_republish_cannot_restore_removed_relations_or_empty_bindings(): void {
		[ $product, $file ] = $this->unbound_draft();
		$product->set_status( 'publish' );
		$product->save();
		$id       = $product->get_id();
		$bindings = $this->bindings( $id );
		$before   = $this->source_snapshot( $id, $file );
		$this->assertSame( 200, $this->download_status( $file['url'] ) );
		$product->set_status( 'draft' );
		$product->save();
		$this->assertSame( 410, $this->download_status( $file['url'] ) );
		update_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, array() );
		$product->set_status( 'publish' );
		$product->save();
		$this->assertSame( $bindings, $this->bindings( $id ) );
		$manifest = Publication::manifest();
		$this->assertSame( array(), Publication::figures_for( $id, $manifest ) );
		$this->assertSame( array(), Publication::faqs_for( $id, $manifest ) );
		$this->assertSame( 410, $this->download_status( $file['url'] ) );
		$after = $this->source_snapshot( $id, $file );
		$this->assertSame( $before['blob_sha256'], $after['blob_sha256'] );
		$this->assertSame( $before['figure_revision'], $after['figure_revision'] );
		$this->assertSame( $before['metadata'][ Faqs::META_KEY ], $after['metadata'][ Faqs::META_KEY ] );
		$this->assertFileExists( $file['path'] );
		update_post_meta( $id, EvidenceBindings::META_KEY, array() );
		update_post_meta( $id, EvidenceBindings::FAQ_META_KEY, array() );
		update_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, $before['metadata'][ EngineeringData::DOCUMENTS_META_KEY ] );
		$product->save();
		$this->assertSame( array( array(), array() ), $this->bindings( $id ), 'Restoring a document relation does not reset initialized empty evidence.' );
		$manifest = Publication::manifest();
		$this->assertSame( array(), Publication::figures_for( $id, $manifest ) );
		$this->assertSame( array(), Publication::faqs_for( $id, $manifest ) );
	}

	/**
	 * A pre-adoption draft with owned explicit sources, as skipped by published-only adoption.
	 *
	 * @return array{WC_Product_Simple,array{path:string,url:string}}
	 */
	private function unbound_draft(): array {
		$product = new WC_Product_Simple();
		$product->set_name( 'Initial binding fixture ' . self::tag() );
		$product->set_status( 'draft' );
		$product->save();
		$this->later(
			static function () use ( $product ): void {
				$product->delete( true );
			}
		);
		$id = $product->get_id();
		pll_set_post_language( $id, 'en' );
		$uploads   = wp_upload_dir();
		$relative  = 'publication-initial-bindings/' . self::tag();
		$directory = $uploads['basedir'] . '/' . $relative;
		$this->assertTrue( wp_mkdir_p( $directory ) );
		$file = array(
			'path' => $directory . '/manual.pdf',
			'url'  => $uploads['baseurl'] . '/' . $relative . '/manual.pdf',
		);
		$this->later(
			static function () use ( $file, $directory ): void {
				wp_delete_file( $file['path'] );
				rmdir( $directory );
			}
		);
		file_put_contents( $file['path'], "%PDF-1.4\nOriginal initial-binding fixture\n%%EOF\n" );
		update_post_meta(
			$id,
			EngineeringData::DOCUMENTS_META_KEY,
			array(
				array(
					'url'  => $file['url'],
					'type' => 'manual',
				),
			)
		);
		update_post_meta(
			$id,
			SelectionFacts::FIGURES_META_KEY,
			array(
				'rated_ac_power_kw' => array(
					'value'    => 10,
					'unit'     => 'kW',
					'citation' => array(
						'url'  => $file['url'],
						'page' => 1,
					),
				),
			)
		);
		update_post_meta(
			$id,
			Faqs::META_KEY,
			Faqs::encode(
				array(
					array(
						'question'    => 'Fixture question?',
						'answer'      => 'Fixture answer.',
						'question_de' => 'Fixture-Frage?',
						'answer_de'   => 'Fixture-Antwort.',
						'citation'    => array(
							'url'  => $file['url'],
							'page' => 1,
						),
					),
				)
			)
		);
		// Only these owned keys emulate an existing draft skipped by first adoption.
		delete_post_meta( $id, EvidenceBindings::META_KEY );
		delete_post_meta( $id, EvidenceBindings::FAQ_META_KEY );
		return array( $product, $file );
	}

	/**
	 * Source content and document identity stay separate from generated product/source revisions.
	 *
	 * @param int                           $id Fixture product.
	 * @param array{path:string,url:string} $file Owned source file.
	 * @return array{metadata:array<string,mixed>,figure_revision:string,document_id:string,blob_sha256:string|false}
	 */
	private function source_snapshot( int $id, array $file ): array {
		$metadata = array();
		foreach ( array( SelectionFacts::FIGURES_META_KEY, Faqs::META_KEY, EngineeringData::DOCUMENTS_META_KEY ) as $key ) {
			$metadata[ $key ] = get_post_meta( $id, $key, true );
		}
		return array(
			'metadata'        => $metadata,
			'figure_revision' => Publication::revision( $metadata[ SelectionFacts::FIGURES_META_KEY ]['rated_ac_power_kw'] ),
			'document_id'     => DocumentFiles::id( $file['url'] ),
			'blob_sha256'     => hash_file( 'sha256', $file['path'] ),
		);
	}

	/**
	 * Exact generated history, including intentionally empty fields.
	 *
	 * @param int $id Fixture product.
	 * @return array{mixed,mixed}
	 */
	private function bindings( int $id ): array {
		return array( get_post_meta( $id, EvidenceBindings::META_KEY, true ), get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true ) );
	}

	/**
	 * Read persisted state after the final Woo save has completed.
	 *
	 * @param int $id Fixture product.
	 */
	private function assert_initial_bindings_and_queue( int $id ): void {
		$this->assertTrue( metadata_exists( 'post', $id, EvidenceBindings::META_KEY ), 'Final Woo save initialized the missing figure bindings.' );
		$this->assertTrue( metadata_exists( 'post', $id, EvidenceBindings::FAQ_META_KEY ), 'Final Woo save initialized the missing FAQ bindings.' );
		$this->assertTrue( get_option( 'linker_publication_pending' ), 'Final Woo save leaves preparation pending.' );
		$this->assertNotFalse( as_has_scheduled_action( 'linker_publication_reconcile', array(), 'linker-publication' ), 'Preparation has durable native Action Scheduler work.' );
	}

	/**
	 * The actual native original-URL gate, without issuing network requests.
	 *
	 * @param string $url Owned hosted PDF URL.
	 */
	private function download_status( string $url ): int {
		return ( new DocumentAccess() )->response( DocumentFiles::resolve( $url ), 'HEAD' )['status'];
	}
}

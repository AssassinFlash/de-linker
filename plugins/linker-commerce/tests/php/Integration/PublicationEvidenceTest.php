<?php
/**
 * Explicit document maintenance and cited answers against real Woo and files.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\GetProduct;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\SelectionFacts;
use WC_Product_Simple;

/**
 * Withdrawal preserves source records while removing their current authority.
 *
 * @coversNothing
 */
final class PublicationEvidenceTest extends IntegrationTestCase {
	/**
	 * Stored legacy, figure and ACF values cannot undo a normal explicit list.
	 *
	 * @dataProvider last_relation_removals
	 * @param bool $delete_key Delete the key instead of maintaining an empty list.
	 */
	public function test_normal_list_supersedes_old_associations_and_final_removal( bool $delete_key ): void {
		$product    = $this->published_product();
		$id         = $product->get_id();
		$files      = $this->files( array( 'current', 'figure', 'legacy', 'acf' ) );
		$attachment = wp_insert_attachment(
			array(
				'post_title'     => 'Evidence fixture attachment',
				'post_mime_type' => 'application/pdf',
				'post_status'    => 'inherit',
			),
			$files['acf']['path']
		);
		$this->assertGreaterThan( 0, $attachment );
		update_attached_file( $attachment, $files['acf']['path'] );
		$this->later(
			static function () use ( $attachment ): void {
				wp_delete_attachment( $attachment, true );
			}
		);
		$figure = array(
			'rated_ac_power_kw' => array(
				'value'    => 7,
				'unit'     => 'kW',
				'citation' => array(
					'url'  => $files['figure']['url'],
					'page' => 1,
				),
			),
		);
		update_post_meta( $id, '_delinker_datasheet_url', $files['legacy']['url'] );
		update_post_meta(
			$id,
			'_tv_legacy_acf_json',
			array(
				'downloads' => array(
					array(
						'download_file'  => $attachment,
						'download_title' => 'Old explicit ACF source',
					),
				),
			)
		);
		update_post_meta( $id, SelectionFacts::FIGURES_META_KEY, $figure );
		$this->assertCount( 3, Publication::document_rows( $id ) );
		update_post_meta(
			$id,
			EngineeringData::DOCUMENTS_META_KEY,
			array(
				array(
					'url'  => $files['current']['url'],
					'type' => 'manual',
				),
			)
		);
		$this->assertSame( '1', get_post_meta( $id, '_linker_documents_managed', true ) );
		$this->assertSame( array( $files['current']['url'] ), array_column( Publication::document_rows( $id ), 'url' ) );
		$this->assertSame( 200, $this->download_status( $files['current']['url'] ) );
		foreach ( array( 'figure', 'legacy', 'acf' ) as $name ) {
			$this->assertSame( 410, $this->download_status( $files[ $name ]['url'] ), $name );
		}
		if ( $delete_key ) {
			delete_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY );
		} else {
			update_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, array() );
		}
		$this->assertSame( array(), Publication::document_rows( $id ) );
		foreach ( $files as $file ) {
			$this->assertFileExists( $file['path'] );
			$this->assertSame( 410, $this->download_status( $file['url'] ) );
		}
		$this->assertSame( $figure, get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true ) );
		$this->assertSame( $files['legacy']['url'], get_post_meta( $id, '_delinker_datasheet_url', true ) );
		$this->assertSame( 'publish', get_post_status( $id ) );
		$response = wp_remote_head(
			$files['current']['url'],
			array(
				'timeout'     => 10,
				'redirection' => 0,
			)
		);
		$this->assertIsArray( $response );
		$this->assertSame( 410, wp_remote_retrieve_response_code( $response ), 'The original public URL also refuses the final removed relation.' );
	}

	/**
	 * Native empty-list and deleted-key writes preserve the withdrawal decision.
	 *
	 * @return array<string,array{bool}>
	 */
	public static function last_relation_removals(): array {
		return array(
			'explicit empty list' => array( false ),
			'deleted last key'    => array( true ),
		);
	}

	/** Old text/page references cannot adopt replacement bytes through a routine save. */
	public function test_same_url_replacement_requires_a_changed_faq_to_bind_current_bytes(): void {
		$product = $this->published_product();
		$id      = $product->get_id();
		$file    = $this->files( array( 'manual' ) )['manual'];
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
		$faqs = $this->answers( $file['url'] );
		update_post_meta( $id, Faqs::META_KEY, Faqs::encode( $faqs ) );
		update_post_meta(
			$id,
			'_linker_faq',
			array(
				array(
					'question'    => 'Old unbound question?',
					'answer'      => 'Unbound old answer',
					'question_de' => 'Alte Frage ohne Beleg?',
					'answer_de'   => 'Alte Antwort ohne Beleg',
				),
			)
		);
		$this->assertSame( '1', get_post_meta( $id, '_linker_faqs_managed', true ) );
		$this->assertCount( 2, Publication::faqs_for( $id ) );
		$this->assertSame( 'Old alpha answer', $this->ability_answers( $id, 'en' )[0]['answer'] );
		$this->assertSame( 'Alte Alpha-Antwort', $this->ability_answers( $id, 'de' )[0]['answer'] );
		$this->assertCount( 2, $this->library_answers( $product, 'en' ) );
		$this->assertStringContainsString( '#page=7', $this->library_answers( $product, 'en' )[0]['source_url'] );
		$this->product_context( $product );
		$this->assertTrue( linker_commerce_pdp_has_faqs() );
		$this->assertStringContainsString( 'Old alpha answer', ( new Shortcodes() )->faqs() );
		$original = get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true );
		file_put_contents( $file['path'], "%PDF-1.4\nReplacement evidence fixture\n%%EOF\n" );
		$this->assertCount( 2, Faqs::of( $id ), 'Stored source answers remain available to their editor.' );
		$this->assertSame( array(), Publication::faqs_for( $id ) );
		$this->assertSame( array(), $this->ability_answers( $id, 'en' ) );
		$this->assertSame( array(), $this->ability_answers( $id, 'de' ) );
		$this->assertSame( array(), $this->library_answers( $product, 'en' ) );
		$this->assertSame( array(), $this->library_answers( $product, 'de' ) );
		$this->assertSame( '', ( new Shortcodes() )->faqs() );
		$this->assertFalse( linker_commerce_pdp_has_faqs() );
		EvidenceBindings::capture_faqs( $id, true );
		update_post_meta( $id, Faqs::META_KEY, $faqs );
		$reordered = array_reverse( $faqs );
		update_post_meta( $id, Faqs::META_KEY, $reordered );
		$this->assertEqualsCanonicalizing( $original, get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true ) );
		$this->assertSame( array(), Publication::faqs_for( $id ), 'Adoption rerun, equivalent-content save and row reordering cannot renew stale evidence.' );
		$reordered[0]['answer']           = 'Current beta answer verified against replacement bytes.';
		$reordered[0]['answer_de']        = 'Aktuelle Beta-Antwort aus den neuen Unterlagen.';
		$reordered[0]['citation']['page'] = 21;
		update_post_meta( $id, Faqs::META_KEY, $reordered );
		$current = Publication::faqs_for( $id );
		$this->assertCount( 1, $current );
		$this->assertSame( 21, $current[0]['citation']['page'] );
		$this->assertSame( 'Current beta answer verified against replacement bytes.', $current[0]['answer'] );
		$this->assertStringContainsString( '#page=21', $this->library_answers( $product, 'en' )[0]['source_url'] );
		$this->assertStringContainsString( 'Aktuelle Beta-Antwort', $this->library_answers( $product, 'de' )[0]['answer'] );
		$this->assertTrue( linker_commerce_pdp_has_faqs() );
		$this->assertStringNotContainsString( 'Old alpha answer', ( new Shortcodes() )->faqs() );
		$this->assertFileExists( $file['path'] );
		update_post_meta(
			$id,
			'_tv_legacy_acf_json',
			array(
				'faqs' => array(
					array(
						'faq_question' => 'Old ACF question?',
						'faq_answer'   => 'Old ACF answer',
					),
				),
			)
		);
		delete_post_meta( $id, Faqs::META_KEY );
		$this->assertSame( '1', get_post_meta( $id, '_linker_faqs_managed', true ) );
		$this->assertSame( array(), $this->library_answers( $product, 'en' ), 'Deleting the final maintained FAQ cannot restore an old ACF answer.' );
		$this->assertSame( array(), $this->ability_answers( $id, 'en' ), 'The singular old field cannot restore a withdrawn answer.' );
		$this->assertNotEmpty( get_post_meta( $id, '_linker_faq', true ), 'The old editorial record was preserved.' );
	}

	/** Equal document bytes do not grant a FAQ another URL's association. */
	public function test_equal_sha_unassociated_faq_source_is_not_public(): void {
		$product = $this->published_product();
		$id      = $product->get_id();
		$files   = $this->files( array( 'allowed', 'unassociated' ) );
		update_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, array( array( 'url' => $files['allowed']['url'] ) ) );
		$legacy = array(
			'faqs' => array(
				array(
					'faq_question' => 'Unbound old question?',
					'faq_answer'   => 'Unbound old answer',
				),
			),
		);
		update_post_meta( $id, '_tv_legacy_acf_json', $legacy );
		$this->assertSame( array(), $this->library_answers( $product, 'en' ), 'Even a never-maintained FAQ list cannot authorize an uncited old answer.' );
		$this->assertSame( $legacy, get_post_meta( $id, '_tv_legacy_acf_json', true ) );
		update_post_meta( $id, Faqs::META_KEY, $this->answers( $files['unassociated']['url'] ) );
		$this->assertSame( array(), Publication::faqs_for( $id ) );
		$this->assertSame( 410, $this->download_status( $files['unassociated']['url'] ) );
		$this->assertSame( 200, $this->download_status( $files['allowed']['url'] ) );
	}

	/** A product owned by this fixture, explicitly in the source language. */
	private function published_product(): WC_Product_Simple {
		$product = $this->product( '100' );
		pll_set_post_language( $product->get_id(), 'en' );
		return $product;
	}

	/**
	 * Unique hosted PDF files; no existing source path is edited.
	 *
	 * @param string[] $names Generated filenames.
	 * @phpstan-param list<string> $names
	 * @return array<string,array{path:string,url:string}>
	 */
	private function files( array $names ): array {
		$uploads   = wp_upload_dir();
		$relative  = 'publication-evidence-tests/' . self::tag();
		$directory = $uploads['basedir'] . '/' . $relative;
		$this->assertTrue( wp_mkdir_p( $directory ) );
		$files = array();
		foreach ( $names as $name ) {
			$path = $directory . '/' . $name . '.pdf';
			file_put_contents( $path, "%PDF-1.4\nOriginal evidence fixture\n%%EOF\n" );
			$files[ $name ] = array(
				'path' => $path,
				'url'  => $uploads['baseurl'] . '/' . $relative . '/' . $name . '.pdf',
			);
		}
		$this->later(
			static function () use ( $files, $directory ): void {
				foreach ( $files as $file ) {
					wp_delete_file( $file['path'] ); }
				rmdir( $directory );
			}
		);
		return $files;
	}

	/**
	 * Current permission of the exact original hosted URL.
	 *
	 * @param string $url Original source.
	 */
	private function download_status( string $url ): int {
		return ( new DocumentAccess() )->response( DocumentFiles::resolve( $url ), 'HEAD' )['status'];
	}

	/**
	 * Two distinct answers with their historical page numbers.
	 *
	 * @param string $url Explicit Woo source.
	 * @return list<array{question:string,answer:string,question_de:string,answer_de:string,citation:array{url:string,page:int,title:string}}>
	 */
	private function answers( string $url ): array {
		return array(
			array(
				'question'    => 'Fixture alpha question?',
				'answer'      => 'Old alpha answer',
				'question_de' => 'Alpha-Frage der Testdaten?',
				'answer_de'   => 'Alte Alpha-Antwort',
				'citation'    => array(
					'url'   => $url,
					'page'  => 7,
					'title' => 'Fixture manual',
				),
			),
			array(
				'question'    => 'Fixture beta question?',
				'answer'      => 'Old beta answer',
				'question_de' => 'Beta-Frage der Testdaten?',
				'answer_de'   => 'Alte Beta-Antwort',
				'citation'    => array(
					'url'   => $url,
					'page'  => 19,
					'title' => 'Fixture manual',
				),
			),
		);
	}

	/**
	 * Only this synthetic product's actual library output.
	 *
	 * @param WC_Product_Simple $product Fixture product.
	 * @param 'en'|'de'         $lang Output language.
	 * @return list<array{question:string,answer:string,product:string,brand:string,url:string,source:string,source_url:string}>
	 */
	private function library_answers( WC_Product_Simple $product, string $lang ): array {
		return array_values( array_filter( ( new DocumentLibrary() )->answers( $lang ), static fn ( array $answer ): bool => $product->get_name() === $answer['product'] ) );
	}

	/**
	 * The same native metadata through Genie's current product ability.
	 *
	 * @param int       $id Fixture product.
	 * @param 'en'|'de' $lang Requested language.
	 * @return list<array{question:string,answer:string}>
	 */
	private function ability_answers( int $id, string $lang ): array {
		$result = ( new GetProduct() )->execute(
			array(
				'product_id' => $id,
				'lang'       => $lang,
			)
		);
		return $result['faq'];
	}

	/**
	 * Install the normal Woo product context and restore the caller's afterward.
	 *
	 * @param WC_Product_Simple $product Fixture product.
	 */
	private function product_context( WC_Product_Simple $product ): void {
		$present            = array_key_exists( 'product', $GLOBALS );
		$previous           = $GLOBALS['product'] ?? null;
		$GLOBALS['product'] = $product; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Native Woo rendering context, restored on exit.
		$this->later(
			static function () use ( $present, $previous ): void {
				if ( $present ) {
					$GLOBALS['product'] = $previous; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Restore the caller's native Woo rendering context.
				} else {
					unset( $GLOBALS['product'] ); }
			}
		);
	}
}

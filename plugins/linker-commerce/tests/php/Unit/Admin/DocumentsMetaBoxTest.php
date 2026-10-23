<?php
/**
 * Tests for the document meta box.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Admin;

use Linker\Commerce\Admin\DocumentsMetaBox;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for DocumentsMetaBox: the box lists the product's documents and the
 * save writes the list back — refusals keep the previous entry (ticket #68).
 *
 * @covers \Linker\Commerce\Admin\DocumentsMetaBox
 */
final class DocumentsMetaBoxTest extends TestCase {
	use \Linker\Commerce\Tests\Support\ManagedDocumentFixture;

	/** Provide the real managed PDFs the editor may associate. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'has_filter' )->andReturn( false )->byDefault();
		WP_Mock::userFunction( 'get_option' )->andReturn( array() )->byDefault();
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( array() )->byDefault();
		$this->managed_documents( array( '2026/10/manual.pdf', '2026/10/kept.pdf', '2026/10/gone.pdf', '2026/10/appended.pdf' ) );
	}

	/** Remove generated files after the editor case. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}



	/**
	 * The box registers on the product screen.
	 */
	public function test_registers_on_the_product_screen(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$box = new DocumentsMetaBox();
		WP_Mock::userFunction(
			'add_meta_box',
			array(
				'times' => 1,
				'args'  => array(
					'linker-commerce-documents',
					'Documents',
					\Mockery::type( 'closure' ),
					'product',
					'normal',
					'default',
				),
			)
		);
		$box->register();
		$this->assertConditionsMet();
	}

	/**
	 * The box lists one row per document plus spare rows, all posting into
	 * linker_documents[].
	 */
	public function test_renders_the_documents_and_spare_rows(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '' ) );
		WP_Mock::userFunction( 'selected', array( 'return' => static fn ( string $a, string $b ): string => $a === $b ? ' selected' : '' ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 6521, EngineeringData::DOCUMENTS_META_KEY, true ),
				'return' => array(
					array(
						'url'   => 'http://site/wp-content/uploads/2026/10/manual.pdf',
						'title' => 'GW5.1 Battery User Manual',
						'type'  => 'manual',
						'lang'  => 'de',
					),
				),
			)
		);

		ob_start();
		( new DocumentsMetaBox() )->render( 6521 );
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'linker_documents[0][url]', $html );
		$this->assertStringContainsString( 'GW5.1 Battery User Manual', $html );
		$this->assertStringContainsString( 'linker_documents[1][url]', $html, 'A spare row follows the stored one.' );
		$this->assertStringContainsString( 'selected', $html, 'The stored type and language stay selected.' );
		$this->assertConditionsMet();
	}

	/**
	 * The save writes the posted rows as the document list, in the shape the
	 * feed and the figures box read.
	 */
	public function test_save_writes_the_posted_rows(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $text ): string => trim( $text ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn ( string $url ): string => $url ) );
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ),
			)
		);
		WP_Mock::userFunction( 'home_url', array( 'return' => 'http://127.0.0.1:8927' ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times' => 1,
				'args'  => array(
					6521,
					EngineeringData::DOCUMENTS_META_KEY,
					array(
						array(
							'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/manual.pdf',
							'title' => 'User Manual',
							'type'  => 'manual',
							'lang'  => 'de',
						),
					),
				),
			)
		);

		$_POST = array(
			'linker_commerce_documents_nonce' => 'nonce',
			'linker_documents'                => array(
				0 => array(
					'title'  => 'User Manual',
					'url'    => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/manual.pdf',
					'type'   => 'manual',
					'lang'   => 'de',
					'remove' => '',
				),
				1 => array(
					'title' => '',
					'url'   => '',
					'type'  => '',
					'lang'  => '',
				),
				2 => array(
					'title' => 'A row without an address',
					'url'   => '',
					'type'  => 'manual',
					'lang'  => 'en',
				),
			),
		);
		( new DocumentsMetaBox() )->save( 6521 );
		$_POST = array();
		$this->assertConditionsMet();
	}

	/**
	 * A removed row and a row without an address are dropped; an address that
	 * is not ours keeps the previous entry at its index.
	 */
	public function test_save_drops_removed_rows_and_foreign_addresses(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $text ): string => trim( $text ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn ( string $url ): string => $url ) );
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ),
			)
		);
		WP_Mock::userFunction( 'home_url', array( 'return' => 'http://127.0.0.1:8927' ) );
		$previous = array(
			0 => array(
				'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/kept.pdf',
				'title' => 'Kept',
				'type'  => 'datasheet',
				'lang'  => 'en',
			),
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $previous ) );
		$kept = $previous;
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times' => 1,
				'args'  => array( 6521, EngineeringData::DOCUMENTS_META_KEY, $kept ),
			)
		);

		$_POST = array(
			'linker_commerce_documents_nonce' => 'nonce',
			'linker_documents'                => array(
				0 => array(
					'title' => 'Link to someone else',
					'url'   => 'https://vendor.example/manual.pdf',
					'type'  => 'manual',
					'lang'  => 'en',
				),
				1 => array(
					'title'  => 'Removed',
					'url'    => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/gone.pdf',
					'type'   => 'manual',
					'lang'   => 'en',
					'remove' => '1',
				),
				2 => array(
					'title' => 'A row without an address',
					'url'   => '',
					'type'  => 'manual',
					'lang'  => 'en',
				),
			),
		);
		( new DocumentsMetaBox() )->save( 6521 );
		$_POST = array();
		$this->assertConditionsMet();
	}

	/**
	 * A save without the box's nonce writes nothing.
	 */
	public function test_save_without_nonce_writes_nothing(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'update_post_meta', array( 'times' => 0 ) );

		$_POST = array( 'linker_documents' => array( 0 => array( 'url' => 'http://x/y.pdf' ) ) );
		( new DocumentsMetaBox() )->save( 6521 );
		$_POST = array();
		$this->assertConditionsMet();
	}

	/**
	 * Rows beyond the ones the box sent are kept: another writer appended them
	 * after this box was rendered, and the box did not see them. The save
	 * writes the sent row and the appended one, in that order.
	 */
	public function test_rows_beyond_the_ones_sent_are_kept(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $text ): string => trim( $text ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return' => static fn ( string $url ): string => $url ) );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ) ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'http://127.0.0.1:8927' ) );
		// The list as the save reads it: the box's row, then the row another
		// writer appended after the box was rendered.
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => array(
					array(
						'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/manual.pdf',
						'title' => 'User Manual',
						'type'  => 'manual',
						'lang'  => 'de',
					),
					array(
						'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/appended.pdf',
						'title' => 'Added by another writer',
						'type'  => 'document',
						'lang'  => 'en',
					),
				),
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times' => 1,
				'args'  => array(
					6521,
					EngineeringData::DOCUMENTS_META_KEY,
					array(
						array(
							'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/manual.pdf',
							'title' => 'User Manual',
							'type'  => 'manual',
							'lang'  => 'de',
						),
						array(
							'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/appended.pdf',
							'title' => 'Added by another writer',
							'type'  => 'document',
							'lang'  => 'en',
						),
					),
				),
			)
		);

		$_POST = array(
			'linker_commerce_documents_nonce' => 'nonce',
			'linker_documents'                => array(
				0 => array(
					'title' => 'User Manual',
					'url'   => 'http://127.0.0.1:8927/wp-content/uploads/2026/10/manual.pdf',
					'type'  => 'manual',
					'lang'  => 'de',
				),
			),
		);
		( new DocumentsMetaBox() )->save( 6521 );
		$_POST = array();
		$this->assertConditionsMet();
	}
}

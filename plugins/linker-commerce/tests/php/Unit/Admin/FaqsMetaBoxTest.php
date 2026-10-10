<?php
/**
 * Tests for the FAQ meta box.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Admin;

use Linker\Commerce\Admin\FaqsMetaBox;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for FaqsMetaBox: a question without a citation is refused and the
 * previous row stays; a cited question is written.
 *
 * @covers \Linker\Commerce\Admin\FaqsMetaBox
 */
final class FaqsMetaBoxTest extends TestCase {

	private const PRODUCT = 1959;

	private const STORED = array(
		array(
			'question'    => 'What does X stand for?',
			'answer'      => 'The battery option.',
			'question_de' => 'Wofür steht X?',
			'answer_de'   => 'Die Batterieoption.',
			'citation'    => array(
				'url'   => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
				'page'  => 2,
				'title' => 'CHS2 datasheet',
			),
		),
	);

	/**
	 * The escaping and sanitizing the box rides on; the nonce and permission
	 * checks pass.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::passthruFunction( 'esc_textarea' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'sanitize_textarea_field' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction(
			'wp_verify_nonce',
			array(
				'args'   => array( 'nonce', 'linker_commerce_faqs' ),
				'return' => 1,
			)
		);
		$_POST = array(
			'linker_commerce_faqs_nonce' => 'nonce',
		);
	}

	/**
	 * The request the box reads is per-test.
	 */
	public function tearDown(): void {
		$_POST = array();
		parent::tearDown();
	}

	/**
	 * A cited question is written with the German pair.
	 */
	public function test_a_cited_question_is_written(): void {
		$this->row(
			0,
			array(
				'question'    => 'What does X stand for?',
				'answer'      => 'The battery option on the nameplate.',
				'question_de' => 'Wofür steht X?',
				'answer_de'   => 'Die Batterieoption auf dem Typenschild.',
				'document'    => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
				'page'        => '2',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FaqsMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'The battery option on the nameplate.', $written['faqs'][0]['answer'] );
		$this->assertSame( 2, $written['faqs'][0]['citation']['page'] );
		$this->assertSame( 'CHS2 datasheet', $written['faqs'][0]['citation']['title'] );
	}

	/**
	 * A question without a citation keeps the previous row.
	 */
	public function test_a_question_without_the_citation_keeps_the_previous_row(): void {
		$this->row(
			0,
			array(
				'question' => 'What does X stand for?',
				'answer'   => 'Changed without a page.',
				'document' => '',
				'page'     => '',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FaqsMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'The battery option.', $written['faqs'][0]['answer'] );
		$this->assertSame( 2, $written['faqs'][0]['citation']['page'] );
	}

	/**
	 * An empty question is dropped.
	 */
	public function test_an_empty_question_is_dropped(): void {
		$this->row(
			0,
			array(
				'question' => '',
				'answer'   => 'Gone.',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
				'page'     => '2',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FaqsMetaBox() )->save( self::PRODUCT );

		$this->assertSame( array(), $written['faqs'] );
	}

	/**
	 * A wrong nonce writes nothing.
	 */
	public function test_a_missing_nonce_writes_nothing(): void {
		unset( $_POST['linker_commerce_faqs_nonce'] );
		$this->row(
			0,
			array(
				'question' => 'What does X stand for?',
				'answer'   => 'The battery option.',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
				'page'     => '2',
			)
		);
		WP_Mock::userFunction( 'current_user_can' )->never();
		WP_Mock::userFunction( 'update_post_meta' )->never();

		( new FaqsMetaBox() )->save( self::PRODUCT );

		$this->assertConditionsMet();
	}

	/**
	 * The box renders the stored question and the document dropdown.
	 */
	public function test_render_shows_the_stored_question_and_documents(): void {
		$this->mock_reads();
		WP_Mock::passthruFunction( 'wp_nonce_field' );
		WP_Mock::userFunction(
			'selected',
			array(
				'args'   => array( '*', '*', false ),
				'return' => ' selected',
			)
		);
		ob_start();
		( new FaqsMetaBox() )->render( self::PRODUCT );
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'name="linker_faqs[0][question]"', $html );
		$this->assertStringContainsString( 'What does X stand for?', $html );
		$this->assertStringContainsString( 'CHS2 datasheet', $html );
		$this->assertStringContainsString( 'name="linker_faqs[1][question]"', $html, 'spare empty rows so an editor can add an item' );
	}

	/**
	 * Puts one row into the request.
	 *
	 * @param int                   $index Row index.
	 * @param array<string, string> $row   Fields.
	 */
	private function row( int $index, array $row ): void {
		foreach ( array( 'question', 'answer', 'question_de', 'answer_de', 'document', 'page' ) as $field ) {
			$_POST[ "linker_faqs[{$index}][{$field}]" ] = $row[ $field ] ?? '';
		}
	}

	/**
	 * Mocks the reads: the permission, the revision checks, the stored list and
	 * the documents.
	 */
	private function mock_reads(): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'edit_post', self::PRODUCT ),
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'wp_is_post_revision',
			array(
				'args'   => array( self::PRODUCT ),
				'return' => false,
			)
		);
		WP_Mock::userFunction(
			'wp_is_post_autosave',
			array(
				'args'   => array( self::PRODUCT ),
				'return' => false,
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( self::PRODUCT, '_linker_faqs', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode( self::STORED ),
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( self::PRODUCT, '_linker_documents', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode(
					array(
						array(
							'url'   => 'https://de-linker.com/wp-content/uploads/2026/10/chs2.pdf',
							'title' => 'CHS2 datasheet',
							'type'  => 'datasheet',
							'lang'  => 'en',
						),
					)
				),
			)
		);
	}

	/**
	 * Mocks the write: captures what is saved.
	 *
	 * @param array<string, mixed> $written Receives the saved list.
	 */
	private function mock_write( array &$written ): void {
		$this->mock_reads();
		WP_Mock::passthruFunction( 'wp_slash' );
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => static fn( $data ): string => (string) json_encode( $data ),
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'args'   => array( self::PRODUCT, '_linker_faqs', '*' ),
				'return' => static function ( int $id, string $key, string $json ) use ( &$written ): bool {
					$written['faqs'] = json_decode( $json, true );

					return true;
				},
			)
		);
	}
}

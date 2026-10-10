<?php
/**
 * Tests for the figure-citation meta box.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Admin;

use Linker\Commerce\Admin\FiguresMetaBox;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for FiguresMetaBox: a changed value or unit without the citation
 * (document and page) is refused and keeps the previous entry; a citation
 * given for an unchanged or changed row is written.
 *
 * @covers \Linker\Commerce\Admin\FiguresMetaBox
 */
final class FiguresMetaBoxTest extends TestCase {

	private const PRODUCT = 4107;

	private const FIGURES = array(
		'mppt_voltage_range_v' => array(
			'value'    => '180~900',
			'unit'     => 'V',
			'citation' => array(
				'url'  => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page' => 2,
			),
		),
		'comms'                => array(
			'value' => 'Wi-Fi',
			'unit'  => '',
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
		WP_Mock::passthruFunction( 'esc_attr__' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction(
			'wp_verify_nonce',
			array(
				'args'   => array( 'nonce', 'linker_commerce_figures' ),
				'return' => 1,
			)
		);
		$_POST = array(
			'linker_commerce_figures_nonce' => 'nonce',
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
	 * A changed value with the document and the page is written, value_de
	 * stays.
	 */
	public function test_a_changed_value_with_the_citation_is_written(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'LAN',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page'     => '7',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$figures = $written['figures'];
		$this->assertSame( 'LAN', $figures['comms']['value'] );
		$this->assertSame(
			array(
				'url'  => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page' => 7,
			),
			$figures['comms']['citation']
		);
		$this->assertSame( '180~900', $figures['mppt_voltage_range_v']['value'], 'an untouched row keeps its entry' );
	}

	/**
	 * A changed value without the citation is refused: the entry keeps its
	 * previous value and gains nothing.
	 */
	public function test_a_changed_value_without_the_citation_is_refused(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'LAN',
				'document' => '',
				'page'     => '',
			)
		);
		$written = array();
		$this->mock_write( $written );
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => 7,
			)
		);
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'times' => 1,
				'args'  => array( 7, 'linker_commerce_figures_refused', 'comms' ),
			)
		);

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'Wi-Fi', $written['figures']['comms']['value'] );
		$this->assertArrayNotHasKey( 'citation', $written['figures']['comms'] );
	}

	/**
	 * A page of zero is no citation: the row keeps its previous entry.
	 */
	public function test_a_page_below_one_is_refused(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'LAN',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page'     => '0',
			)
		);
		$written = array();
		$this->mock_write( $written );
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => 7,
			)
		);
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'times' => 1,
				'args'  => array( 7, 'linker_commerce_figures_refused', 'comms' ),
			)
		);

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'Wi-Fi', $written['figures']['comms']['value'] );
	}

	/**
	 * A document that is not one of this product's documents is no citation.
	 */
	public function test_a_document_outside_the_products_list_is_refused(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'LAN',
				'document' => 'https://de-linker.com/wp-content/uploads/2099/01/someone-elses.pdf',
				'page'     => '3',
			)
		);
		$written = array();
		$this->mock_write( $written );
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => 7,
			)
		);
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'times' => 1,
				'args'  => array( 7, 'linker_commerce_figures_refused', 'comms' ),
			)
		);

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'Wi-Fi', $written['figures']['comms']['value'] );
		$this->assertArrayNotHasKey( 'citation', $written['figures']['comms'] );
	}

	/**
	 * An unchanged value without a citation stays as it is: the box does not
	 * invent one.
	 */
	public function test_an_unchanged_value_keeps_its_lack_of_citation(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'Wi-Fi',
				'document' => '',
				'page'     => '',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 'Wi-Fi', $written['figures']['comms']['value'] );
		$this->assertArrayNotHasKey( 'citation', $written['figures']['comms'] );
	}

	/**
	 * The citation of an unchanged value can be completed.
	 */
	public function test_a_missing_citation_can_be_added_to_an_unchanged_value(): void {
		$this->row(
			'comms',
			array(
				'value'    => 'Wi-Fi',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page'     => '7',
			)
		);
		$written = array();
		$this->mock_write( $written );

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertSame( 7, $written['figures']['comms']['citation']['page'] );
	}

	/**
	 * A wrong nonce writes nothing.
	 */
	public function test_a_missing_nonce_writes_nothing(): void {
		unset( $_POST['linker_commerce_figures_nonce'] );
		$this->row(
			'comms',
			array(
				'value'    => 'LAN',
				'document' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page'     => '7',
			)
		);
		WP_Mock::userFunction( 'current_user_can' )->never();
		WP_Mock::userFunction( 'update_post_meta' )->never();

		( new FiguresMetaBox() )->save( self::PRODUCT );

		$this->assertConditionsMet();
	}

	/**
	 * The box renders one row per figure, the documents as the citation's
	 * dropdown and the citation's page.
	 */
	public function test_render_shows_rows_documents_and_pages(): void {
		$this->mock_reads();
		WP_Mock::passthruFunction( 'wp_nonce_field' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::userFunction(
			'selected',
			array(
				'args'   => array( '*', '*', false ),
				'return' => ' selected',
			)
		);
		ob_start();
		( new FiguresMetaBox() )->render( self::PRODUCT );
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'name="linker_figures[mppt_voltage_range_v][value]"', $html );
		$this->assertStringContainsString( 'name="linker_figures[comms][document]"', $html );
		$this->assertStringContainsString( 'value="2"', $html );
		$this->assertStringContainsString( 'SAJ H2 Datasheet (EN)', $html );
	}

	/**
	 * The notice prints the keys the save redirected back with, and nothing
	 * without them.
	 */
	public function test_the_notice_names_the_refused_keys(): void {
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::userFunction(
			'__',
			array(
				'args'   => array( 'Figures %s kept their previous value: a changed value needs the document and the page it is printed on.', 'linker-commerce' ),
				'return' => 'Figures %s kept their previous value: a changed value needs the document and the page it is printed on.',
			)
		);
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => 7,
			)
		);
		WP_Mock::userFunction(
			'get_user_meta',
			array(
				'args'            => array( 7, 'linker_commerce_figures_refused', true ),
				'return_in_order' => array( 'comms', '' ),
			)
		);
		WP_Mock::userFunction(
			'delete_user_meta',
			array(
				'times' => 1,
				'args'  => array( 7, 'linker_commerce_figures_refused' ),
			)
		);

		ob_start();
		( new FiguresMetaBox() )->notice_refused();
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'notice-error', $html );
		$this->assertStringContainsString( 'comms', $html );

		ob_start();
		( new FiguresMetaBox() )->notice_refused();
		$this->assertSame( '', (string) ob_get_clean() );
	}

	/**
	 * Puts one row into the request.
	 *
	 * @param string                $key   Figure key.
	 * @param array<string, string> $row   value/unit/document/page.
	 */
	private function row( string $key, array $row ): void {
		$_POST[ "linker_figures[{$key}][value]" ]    = $row['value'] ?? '';
		$_POST[ "linker_figures[{$key}][unit]" ]     = $row['unit'] ?? '';
		$_POST[ "linker_figures[{$key}][document]" ] = $row['document'] ?? '';
		$_POST[ "linker_figures[{$key}][page]" ]     = $row['page'] ?? '';
	}

	/**
	 * Mocks the reads: the permission, the revision checks, the figures and
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
				'args'   => array( self::PRODUCT, '_tv_b2b_figures', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => (string) json_encode( self::FIGURES ),
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
							'url'   => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
							'title' => 'SAJ H2 Datasheet (EN)',
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
	 * @param array<string, mixed> $written Receives the saved figures.
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
				'args'   => array( self::PRODUCT, '_tv_b2b_figures', '*' ),
				'return' => static function ( int $id, string $key, string $json ) use ( &$written ): bool {
					$written['figures'] = json_decode( $json, true );

					return true;
				},
			)
		);
	}
}

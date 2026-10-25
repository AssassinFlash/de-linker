<?php
/**
 * Native source confirmation, withdrawal and package quantity boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Publication\PackageContents;
use Linker\Commerce\Products\Publication\PackageContentsEditor;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The fixture is a transport declaration, not a manufacturer's packing list.
 *
 * @covers \Linker\Commerce\Products\Publication\PackageContents
 * @covers \Linker\Commerce\Products\Publication\PackageContentsEditor
 */
final class PackageContentsTest extends TestCase {
	/** Native gettext remains outside these data-boundary assertions. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__' )->andReturnArg( 0 );
	}

	/** Explicitly synthetic current authority.
	 *
	 * @return array<string,mixed>
	 */
	private function manifest(): array {
		return array(
			'products'  => array( array( 'product_id' => 41 ) ),
			'documents' => array(
				array(
					'document_id'       => 'doc-a',
					'document_revision' => str_repeat( 'a', 64 ),
					'blob_sha256'       => str_repeat( 'b', 64 ),
					'product_ids'       => array( 41 ),
					'url'               => 'https://de-linker.com/manual.pdf',
				),
			),
		);
	}

	/** Native form shape with explicit source confirmation.
	 *
	 * @return array<string,mixed>
	 */
	private function draft(): array {
		return array(
			'complete' => '1',
			'items'    => array(
				array(
					'id'          => 'fixture-meter',
					'label'       => array(
						'en' => 'Fixture meter',
						'de' => 'Beispielzähler',
					),
					'quantity'    => '1',
					'unit'        => 'piece',
					'role'        => 'meter',
					'document_id' => 'doc-a',
					'page'        => '2',
					'confirm'     => '1',
				),
			),
		);
	}

	/** One authority flow, including stale bytes and explicit reconfirmation. */
	public function test_native_confirmation_and_document_withdrawal_share_one_authority(): void {
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( static fn ( string $url, int $part ): mixed => parse_url( $url, $part ) );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) );
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => trim( $value ) );
		$manifest                       = $this->manifest();
		$draft                          = $this->draft();
		$stored                         = PackageContentsEditor::prepare( 41, $draft, '', $manifest );
		$length                         = $draft;
		$length['items'][0]['quantity'] = '0.00001';
		$length['items'][0]['unit']     = 'm';
		$this->assertSame( 0.00001, PackageContentsEditor::prepare( 41, $length, '', $manifest )['items'][0]['quantity'] );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			static function ( int $owner, string $key, bool $single ) use ( &$stored ): mixed {
				return 41 === $owner && PackageContents::META_KEY === $key && $single ? $stored : '';
			}
		);
		$this->assertSame( 'documented', PackageContents::projection( 41, $manifest )['status'] );
		$this->assertSame( str_repeat( 'b', 64 ), $stored['items'][0]['source']['blob_sha256'] );
		$draft['items'][0]['confirm']                  = '';
		$manifest['documents'][0]['document_revision'] = str_repeat( 'c', 64 );
		$this->assertSame( $stored, PackageContentsEditor::prepare( 41, $draft, $stored, $manifest ) );
		$this->assertSame(
			array(
				'status' => 'unresolved',
				'items'  => array(),
			),
			PackageContents::projection( 41, $manifest )
		);
		$draft['items'][0]['confirm'] = '1';
		$stored                       = PackageContentsEditor::prepare( 41, $draft, $stored, $manifest );
		$this->assertSame( 'documented', PackageContents::projection( 41, $manifest )['status'] );
		$manifest['documents'][0]['product_ids'] = array( 42 );
		$this->assertSame( 'unresolved', PackageContents::projection( 41, $manifest )['status'] );
		$this->expectException( \RuntimeException::class );
		PackageContentsEditor::prepare( 41, array( 'items' => array() ), $stored, $manifest );
	}


	/**
	 * Validate original decimal text before a float can erase the violation.
	 *
	 * @dataProvider invalid_quantities
	 * @param string $quantity Original operator input.
	 * @param string $unit Declared unit.
	 */
	public function test_count_and_transport_boundaries_do_not_round_the_input( string $quantity, string $unit ): void {
		$draft                         = $this->draft();
		$draft['items'][0]['quantity'] = $quantity;
		$draft['items'][0]['unit']     = $unit;
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => $value );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value ): string => (string) json_encode( $value ) );
		$this->expectException( \RuntimeException::class );
		PackageContentsEditor::prepare( 41, $draft, '', $this->manifest() );
	}

	/**
	 * Specific original-text regressions, not a parameter combination matrix.
	 *
	 * @return array<string,array{string,string}>
	 */
	public static function invalid_quantities(): array {
		return array(
			'fractional piece'           => array( '0.5', 'piece' ),
			'fraction rounded to whole'  => array( '1.00000000000000001', 'pair' ),
			'rounded below safe ceiling' => array( '9007199254740991.01', 'm' ),
			'length precision loss'      => array( '1.00000000000000001', 'm' ),
		);
	}
}

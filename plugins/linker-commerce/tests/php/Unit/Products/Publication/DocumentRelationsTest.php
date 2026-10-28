<?php
/**
 * Normal Woo document maintenance supersedes earlier source associations.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Removing the final explicit association cannot be undone by old citations.
 *
 * @covers \Linker\Commerce\Products\Publication
 */
final class DocumentRelationsTest extends TestCase {
	/** Each relation read resolves one source, without retaining it for the next read. */
	public function test_relation_read_resolves_identity_once_and_next_read_uses_current_source(): void {
		$source = 12;
		$reads  = 0;
		WP_Mock::userFunction( 'has_filter', array( 'return' => true ) );
		$this->filter_returns(
			'linker_commerce_facts_product_id',
			new \WP_Mock\InvokedFilterValue(
				static function () use ( &$source, &$reads ): int {
					++$reads;
					return $source;
				}
			),
			array( 22 )
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): mixed => match ( $key ) {
					EngineeringData::DOCUMENTS_META_KEY => array( array( 'url' => 'https://example.test/source-' . $id . '.pdf' ) ),
					'_linker_documents_managed' => '',
					default => '',
				},
			)
		);
		$this->assertSame( array( array( 'url' => 'https://example.test/source-12.pdf' ) ), Publication::document_rows( 22 ) );
		$this->assertSame( 1, $reads, 'One relation assembly must not repeatedly resolve the same native identity.' );
		$source = 13;
		$this->assertSame( array( array( 'url' => 'https://example.test/source-13.pdf' ) ), Publication::document_rows( 22 ) );
		$this->assertSame( 2, $reads, 'The next read must resolve its current source again.' );
	}

	/**
	 * Legacy associations remain stored but no longer grant publication rights.
	 *
	 * @dataProvider maintained_lists
	 * @param array<int,array<string,string>> $rows Normal Woo-maintained list.
	 */
	public function test_maintained_list_is_the_complete_authority( array $rows ): void {
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_get_attachment_url', array( 'return' => 'https://example.test/old-acf.pdf' ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): mixed => match ( $key ) {
					EngineeringData::DOCUMENTS_META_KEY => $rows,
					'_linker_documents_managed' => '1',
					SelectionFacts::FIGURES_META_KEY => array( array( 'citation' => array( 'url' => 'https://example.test/old-figure.pdf' ) ) ),
					'_delinker_datasheet_url' => 'https://example.test/old-datasheet.pdf',
					'_delinker_manual_url' => 'https://example.test/old-manual.pdf',
					'_tv_legacy_acf_json' => array( 'downloads' => array( array( 'download_file' => 123 ) ) ),
					default => '',
				},
			)
		);
		$this->assertSame( $rows, Publication::document_rows( 12 ) );
	}

	/**
	 * Empty, last-row deletion and replacement all retain normal Woo authority.
	 *
	 * @return array<string,array{array<int,array<string,string>>}>
	 */
	public static function maintained_lists(): array {
		return array(
			'empty list'       => array( array() ),
			'replacement list' => array( array( array( 'url' => 'https://example.test/new.pdf' ) ) ),
		);
	}
}

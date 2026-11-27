<?php
/**
 * Public equipment references follow document publication immediately.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication\Module;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Reference page cache invalidation at the native PDF metadata boundary.
 *
 * @covers \Linker\Commerce\Products\Publication\Module
 */
final class ReferenceCacheTest extends TestCase {
	/** Withdrawing the PDF must expire already-rendered model and matrix pages. */
	public function test_withdrawing_a_pdf_purges_public_reference_pages(): void {
		$pdf = new \WP_Post(
			(object) array(
				'ID'             => 340,
				'post_type'      => 'attachment',
				'post_mime_type' => 'application/pdf',
			)
		);
		WP_Mock::userFunction( 'get_post' )->with( 340 )->andReturn( $pdf );
		WP_Mock::userFunction( 'update_option' )->andReturn( true );
		WP_Mock::expectAction( 'litespeed_purge', 'PT.product' );
		( new Module() )->metadata_changed( 1, 340, '_linker_document_public' );
		$this->assertConditionsMet();
	}
}

<?php
/**
 * Publication cache policy for full, partial and withdrawn document URLs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Original PDF URLs and byte ranges follow current native permissions.
 *
 * @covers \Linker\Commerce\Products\Publication\DocumentAccess
 */
final class DocumentAccessCacheTest extends TestCase {
	use CurrentFaqProduct;

	/** Release this test's generated upload directory. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Published metadata and validators describe the bytes behind this URL. */
	public function test_full_file_is_cacheable_and_partial_or_pinned_results_are_not(): void {
		$this->current_faq_product( 12, array() );
		$url  = home_url() . '/wp-content/uploads/2026/manual.pdf';
		$file = DocumentFiles::resolve( $url );
		self::assertNotNull( $file );
		WP_Mock::userFunction( 'attachment_url_to_postid' )->with( $url )->andReturn( 31 );
		WP_Mock::userFunction( 'get_post_meta' )->with( 31, '_linker_document_public', true )->andReturn( '1' );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ][0]['lang'] = 'DE/EN';
		$access = new DocumentAccess();
		$full   = $access->response( $file, 'GET' );
		self::assertTrue( $full['cacheable'] );
		self::assertSame( 200, $full['status'] );
		self::assertEqualsCanonicalizing( array( 'LK.pdf', 'LK.prod.12', 'LK.att.31', 'LK.pdf.' . substr( hash( 'sha256', '2026/manual.pdf' ), 0, 12 ) ), $full['tags'] );
		self::assertSame( 'en, de-DE', $full['headers']['Content-Language'] );
		self::assertSame( '"' . substr( $file['blob_sha256'], 0, 16 ) . '"', $full['headers']['ETag'] );
		self::assertSame( gmdate( 'D, d M Y H:i:s', (int) filemtime( $file['path'] ) ) . ' GMT', $full['headers']['Last-Modified'] );
		self::assertSame( 'public, max-age=86400, stale-while-revalidate=3600', $full['headers']['Cache-Control'] );
		foreach ( array( $access->response( $file, 'GET', '', $file['blob_sha256'] ), $access->response( $file, 'GET', '', '', false ) ) as $pinned ) {
			self::assertSame( 200, $pinned['status'] );
			self::assertFalse( $pinned['cacheable'] );
			self::assertSame( array(), $pinned['tags'] );
			self::assertSame( 'no-store, private, max-age=0', $pinned['headers']['Cache-Control'] );
		}
		$partial = $access->response( $file, 'GET', 'bytes=3-8' );
		self::assertSame( 206, $partial['status'] );
		self::assertFalse( $partial['cacheable'] );
		self::assertSame( 3, $partial['start'] );
		self::assertSame( 6, $partial['length'] );
	}

	/** Native release metadata, not an earlier successful response, decides the next result. */
	public function test_withdrawal_blocks_alias_and_primary_and_does_not_publish_denial(): void {
		$this->current_faq_product( 12, array() );
		$url       = home_url() . '/wp-content/uploads/2026/manual.pdf';
		$alias_url = home_url() . '/wp-content/uploads/2026/manual-alias.pdf';
		$file      = DocumentFiles::resolve( $url );
		self::assertNotNull( $file );
		copy( $file['path'], dirname( $file['path'] ) . '/manual-alias.pdf' );
		$alias = DocumentFiles::resolve( $alias_url );
		self::assertNotNull( $alias );
		$this->current_faq_meta[ EngineeringData::DOCUMENTS_META_KEY ][0]['aliases'] = array( $alias_url );
		$visible = '1';
		WP_Mock::userFunction( 'attachment_url_to_postid' )->with( $url )->andReturn( 51 );
		WP_Mock::userFunction( 'get_post_meta' )->with( 51, '_linker_document_public', true )->andReturnUsing(
			static function () use ( &$visible ): string {
				return $visible;
			}
		);
		$access = new DocumentAccess();
		self::assertContains( 'LK.att.51', $access->response( $alias, 'GET' )['tags'] );
		$visible = '0';
		foreach ( array( $file, $alias ) as $requested ) {
			$denied = $access->response( $requested, 'GET' );
			self::assertSame( 410, $denied['status'] );
			self::assertSame( 'no-store, private, max-age=0', $denied['headers']['Cache-Control'] );
			self::assertSame( 'noindex, nofollow', $denied['headers']['X-Robots-Tag'] );
			self::assertFalse( $denied['cacheable'] );
			self::assertSame( array(), $denied['tags'] );
		}
	}
}

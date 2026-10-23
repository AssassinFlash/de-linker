<?php
/**
 * Managed file identity and original-URL rewrite boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Tests\Support\ManagedDocumentFixture;
use Linker\Commerce\Tests\TestCase;

/** @covers \Linker\Commerce\Products\Publication\DocumentFiles */
final class DocumentFilesTest extends TestCase {
	use ManagedDocumentFixture;

	/** Provide real managed PDF bytes. */
	public function setUp(): void {
		parent::setUp();
		$this->managed_documents( array( '2026/manual.pdf', '2026/alias.pdf', 'proforma/private.pdf', 'solution-reports/private.pdf' ) );
	}

	/** Reclaim test files immediately. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** Equal bytes do not merge document permission identities. */
	public function test_equal_sha_keeps_distinct_url_identity(): void {
		$one = DocumentFiles::resolve( rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf' );
		$two = DocumentFiles::resolve( rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/alias.pdf' );
		self::assertNotNull( $one );
		self::assertNotNull( $two );
		self::assertSame( $one['blob_sha256'], $two['blob_sha256'] );
		self::assertNotSame( DocumentFiles::id( $one['url'] ), DocumentFiles::id( $two['url'] ) );
	}

	/** Escaping paths, unrelated hosts and private owner files are never public. */
	public function test_unsafe_or_private_paths_fail_closed(): void {
		foreach ( array( '/wp-content/uploads/2026/../2026/manual.pdf', '/wp-content/uploads/%2e%2e/manual.pdf', '/wp-content/uploads/proforma/private.pdf', '/wp-content/uploads/solution-reports/private.pdf', '/wp-content/uploads/2026/missing.pdf' ) as $path ) {
			self::assertNull( DocumentFiles::resolve( rtrim( home_url(), '/' ) . $path ), $path );
		}
		self::assertNull( DocumentFiles::resolve( 'https://vendor.example/wp-content/uploads/2026/manual.pdf' ) );
		self::assertNull( DocumentFiles::resolve( rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf?override=1' ) );
	}

	/** Same path keeps identity while changed bytes replace its content version. */
	public function test_content_replacement_changes_hash_without_reassigning_identity(): void {
		$url    = rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf';
		$before = DocumentFiles::resolve( $url );
		self::assertNotNull( $before );
		file_put_contents( $before['path'], "%PDF-1.4\nreplacement\n%%EOF" );
		$after = DocumentFiles::resolve( $url );
		self::assertNotNull( $after );
		self::assertSame( DocumentFiles::id( $before['url'] ), DocumentFiles::id( $after['url'] ) );
		self::assertNotSame( $before['blob_sha256'], $after['blob_sha256'] );
	}

	/** The native gate precedes WordPress's existing-file bypass. */
	public function test_original_url_gate_precedes_static_shortcut(): void {
		$rules = "RewriteEngine On\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteRule . /index.php [L]\n";
		$after = ( new DocumentAccess() )->rewrite_rules( $rules );
		self::assertStringContainsString( 'linker_public_document=$1 [END,NC]', $after );
		self::assertLessThan( strpos( $after, 'REQUEST_FILENAME' ), strpos( $after, 'linker_public_document=' ) );
	}
}

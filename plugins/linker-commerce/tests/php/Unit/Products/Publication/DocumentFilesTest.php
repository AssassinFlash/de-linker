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

/**
 * File and rewrite permissions operate on actual bytes and paths.
 *
 * @covers \Linker\Commerce\Products\Publication\DocumentFiles
 */
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
		$metadata = $one;
		unset( $metadata['blob_sha256'] );
		self::assertSame( $metadata, DocumentFiles::locate( $one['url'] ) );
		self::assertSame( $one['blob_sha256'], $two['blob_sha256'] );
		self::assertNotSame( DocumentFiles::id( $one['url'] ), DocumentFiles::id( $two['url'] ) );
	}

	/** Escaping paths, unrelated hosts and private owner files are never public. */
	public function test_unsafe_or_private_paths_fail_closed(): void {
		foreach ( array( '/wp-content/uploads/2026/../2026/manual.pdf', '/wp-content/uploads/%2e%2e/manual.pdf', '/wp-content/uploads/proforma/private.pdf', '/wp-content/uploads/solution-reports/private.pdf', '/wp-content/uploads/2026/missing.pdf' ) as $path ) {
			self::assertNull( DocumentFiles::resolve( rtrim( home_url(), '/' ) . $path ), $path );
			self::assertNull( DocumentFiles::locate( rtrim( home_url(), '/' ) . $path ), $path );
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

	/**
	 * A second assembly in one request reuses unchanged bytes, and a rewritten
	 * file still hashes afresh: the reused key covers mtime, size and inode.
	 */
	public function test_unchanged_bytes_are_not_read_twice_in_one_request(): void {
		$url = rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf';

		DocumentFiles::begin_read();
		$first = DocumentFiles::resolve( $url );
		DocumentFiles::end_read();
		self::assertNotNull( $first );

		DocumentFiles::begin_read();
		$reused = DocumentFiles::resolve( $url );
		DocumentFiles::end_read();
		self::assertNotNull( $reused );
		self::assertSame( $first['blob_sha256'], $reused['blob_sha256'] );

		// An in-place edit can keep the inode, size and second-resolution timestamps.
		file_put_contents( $first['path'], "%PDF-1.4\nchanged\n%%EOF" );

		DocumentFiles::begin_read();
		$fresh = DocumentFiles::resolve( $url );
		DocumentFiles::end_read();
		self::assertNotNull( $fresh );
		self::assertNotSame( $first['blob_sha256'], $fresh['blob_sha256'] );
	}

	/** Full manifest requests reuse stable bytes but immediately see same-size edits. */
	public function test_manifest_hashes_are_reused_across_requests_until_the_file_changes(): void {
		$file = $this->publication_uploads . '/2026/manual.pdf';
		// The stable identity must predate the whole-second stat interval.
		sleep( 1 );
		$first = $this->manifest_hash_request( array() );
		self::assertSame( 1, $first['hash_calls'] );
		self::assertSame( 1, $first['writes'] );
		self::assertSame( hash_file( 'sha256', $file ), $first['sha'] );

		$unchanged = $this->manifest_hash_request( $first['cache'] );
		self::assertSame( 0, $unchanged['hash_calls'] );
		self::assertSame( 0, $unchanged['writes'] );
		self::assertSame( $first['sha'], $unchanged['sha'] );
		$download = $this->manifest_hash_request( $first['cache'], false );
		self::assertSame( 1, $download['hash_calls'] );
		self::assertSame( $first['sha'], $download['sha'] );
		self::assertSame( 0, $download['writes'] );

		$mtime = filemtime( $file );
		$old   = file_get_contents( $file );
		self::assertIsInt( $mtime );
		self::assertIsString( $old );
		file_put_contents( $file, str_replace( 'fixture', 'FIXTURE', $old ) );
		touch( $file, $mtime );
		$changed = $this->manifest_hash_request( $unchanged['cache'] );
		self::assertSame( 1, $changed['hash_calls'] );
		self::assertSame( hash_file( 'sha256', $file ), $changed['sha'] );
		self::assertNotSame( $first['sha'], $changed['sha'] );

		file_put_contents( $file, str_replace( 'FIXTURE', 'fIxTuRe', (string) file_get_contents( $file ) ) );
		touch( $file, $mtime );
		$again = $this->manifest_hash_request( $changed['cache'] );
		self::assertSame( 1, $again['hash_calls'] );
		self::assertSame( hash_file( 'sha256', $file ), $again['sha'] );
		self::assertNotSame( $changed['sha'], $again['sha'] );
	}

	/** A file changed while it is hashed cannot be returned or cached. */
	public function test_changed_during_hash_is_unavailable_until_read_again(): void {
		$file = $this->publication_uploads . '/2026/manual.pdf';
		$old  = file_get_contents( $file );
		self::assertIsString( $old );
		sleep( 1 );
		$racing = $this->manifest_hash_request( array(), true, str_replace( 'fixture', 'FIXTURE', $old ) );
		self::assertSame( 1, $racing['hash_calls'] );
		self::assertNull( $racing['sha'] );
		self::assertSame( array(), $racing['cache'] );
		$next = $this->manifest_hash_request( $racing['cache'] );
		self::assertSame( 1, $next['hash_calls'] );
		self::assertSame( hash_file( 'sha256', $file ), $next['sha'] );
		self::assertNotSame( hash( 'sha256', $old ), $next['sha'] );

		// A recent file still needs the same before/after check, even when it is
		// too recent to populate the cross-request cache.
		file_put_contents( $file, $old . "\nrecent" );
		$recent = $this->manifest_hash_request( $next['cache'], true, $old . "\nchanged" );
		self::assertSame( 1, $recent['hash_calls'] );
		self::assertNull( $recent['sha'] );
		self::assertSame( array(), $recent['cache'] );

		// Direct downloads must also reject a changed file and read bytes afresh.
		$download = $this->manifest_hash_request( $next['cache'], false, $old . "\ndownload" );
		self::assertSame( 1, $download['hash_calls'] );
		self::assertNull( $download['sha'] );
		self::assertSame( 0, $download['writes'] );
		$fresh = $this->manifest_hash_request( $next['cache'], false );
		self::assertSame( 1, $fresh['hash_calls'] );
		self::assertSame( hash_file( 'sha256', $file ), $fresh['sha'] );
	}

	/**
	 * Run one resolver invocation in a fresh PHP process with the previous option.
	 *
	 * @param mixed       $cache Previous test option.
	 * @param bool        $manifest Whether this is a full manifest.
	 * @param string|null $after_hash Optional file replacement after hashing.
	 * @return array<string,mixed>
	 */
	private function manifest_hash_request( mixed $cache, bool $manifest = true, ?string $after_hash = null ): array {
		$fixture = dirname( __DIR__, 4 ) . '/fixtures/publication-hash-cache.php';
		$process = proc_open( array( PHP_BINARY, $fixture ), array( array( 'pipe', 'r' ), array( 'pipe', 'w' ), array( 'pipe', 'w' ) ), $pipes ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Isolate the resolver's request-local state in this test.
		self::assertIsResource( $process );
		fwrite(
			$pipes[0],
			(string) json_encode(
				array(
					'uploads'    => $this->publication_uploads,
					'cache'      => $cache,
					'manifest'   => $manifest,
					'after_hash' => $after_hash,
				),
				JSON_THROW_ON_ERROR
			)
		);
		fclose( $pipes[0] );
		$output = stream_get_contents( $pipes[1] );
		$error  = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), (string) $error );
		$result = json_decode( (string) $output, true, 512, JSON_THROW_ON_ERROR );
		self::assertIsArray( $result );
		return $result;
	}

	/** The native gate precedes WordPress's existing-file bypass. */
	public function test_original_url_gate_precedes_static_shortcut(): void {
		$rules = "RewriteEngine On\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteRule . /index.php [L]\n";
		$after = ( new DocumentAccess() )->rewrite_rules( $rules );
		self::assertStringContainsString( 'linker_public_document=$1 [END,NC,QSA]', $after );
		self::assertLessThan( strpos( $after, 'REQUEST_FILENAME' ), strpos( $after, 'linker_public_document=' ) );
	}

	/** Unreadable current authority cannot stream an allowed stale document. */
	public function test_authority_failure_is_unavailable_without_pdf_bytes(): void {
		\WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( false );
		$file     = DocumentFiles::resolve( rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf' );
		$response = ( new DocumentAccess() )->response( $file, 'GET' );
		self::assertSame( 503, $response['status'] );
		self::assertSame( 0, $response['length'] );
	}

	/** An old source link cannot return replacement bytes or bypass permission. */
	public function test_recorded_file_version_is_checked_before_current_permission(): void {
		$file = DocumentFiles::resolve( rtrim( home_url(), '/' ) . '/wp-content/uploads/2026/manual.pdf' );
		self::assertNotNull( $file );
		$access = new DocumentAccess();
		foreach ( array( str_repeat( '0', 64 ), 'invalid' ) as $sha ) {
			$response = $access->response( $file, 'GET', '', $sha );
			self::assertSame( 410, $response['status'] );
			self::assertSame( 0, $response['length'] );
		}
		\WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( false );
		self::assertSame( 503, $access->response( $file, 'GET', '', $file['blob_sha256'] )['status'] );
	}
}

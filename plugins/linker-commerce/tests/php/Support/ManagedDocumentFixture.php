<?php
/**
 * Real local files for unit tests that exercise the publication resolver.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use WP_Mock;

/** Unit fixtures use the same path boundary and byte hashing as WordPress. */
trait ManagedDocumentFixture {
	/** Temporary uploads root, removed after each test. */
	private string $publication_uploads = '';

	/**
	 * Provide native upload/path helpers backed by real temporary files.
	 *
	 * @param list<string> $paths Relative PDF paths.
	 */
	private function managed_documents( array $paths ): void {
		$this->publication_uploads = sys_get_temp_dir() . '/linker-publication-' . bin2hex( random_bytes( 8 ) );
		foreach ( $paths as $path ) {
			$target = $this->publication_uploads . '/' . $path;
			if ( ! is_dir( dirname( $target ) ) ) {
				mkdir( dirname( $target ), 0700, true );
			}
			file_put_contents( $target, "%PDF-1.4\nfixture\n%%EOF" );
		}
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			fn (): array => array(
				'basedir' => $this->publication_uploads,
				'baseurl' => rtrim( home_url(), '/' ) . '/wp-content/uploads',
			)
		)->byDefault();
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( static fn ( string $url, int $part = -1 ) => parse_url( $url, $part ) )->byDefault();
	}

	/** Remove only this test's bounded generated files. */
	private function remove_managed_documents(): void {
		if ( '' === $this->publication_uploads ) {
			return;
		}
		$iterator = new \RecursiveIteratorIterator( new \RecursiveDirectoryIterator( $this->publication_uploads, \FilesystemIterator::SKIP_DOTS ), \RecursiveIteratorIterator::CHILD_FIRST );
		foreach ( $iterator as $file ) {
			if ( $file->isDir() ) {
				rmdir( $file->getPathname() );
			} else {
				unlink( $file->getPathname() );
			}
		}
		rmdir( $this->publication_uploads );
	}
}

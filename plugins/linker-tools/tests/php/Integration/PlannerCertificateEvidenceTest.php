<?php
/**
 * Native current-file permission enriches owned historical metadata only.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Planner\CertificateEvidence;
use PHPUnit\Framework\TestCase;

/**
 * Recorded source identities never override current native permissions.
 *
 * @covers \Linker\Tools\Planner\CertificateEvidence
 */
final class PlannerCertificateEvidenceTest extends TestCase {
	/** Byte replacement, withdrawal and metadata-only changes stay distinct. */
	public function test_current_access_preserves_recorded_identity(): void {
		$uploads = wp_upload_dir();
		$temp    = tempnam( $uploads['basedir'], 'linker-certificate-' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_tempnam -- confined disposable fixture.
		self::assertIsString( $temp );
		$path = $temp . '.pdf';
		rename( $temp, $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.rename_rename -- own empty fixture.
		file_put_contents( $path, "%PDF-1.4\nfixture\n%%EOF" ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- own synthetic fixture, no product mutation.
		try {
			$sha      = hash_file( 'sha256', $path );
			$document = array(
				'document_id'       => 'fixture-document',
				'document_revision' => 'recorded-revision',
				'blob_sha256'       => $sha,
				'url'               => $uploads['baseurl'] . '/' . basename( $path ),
				'product_ids'       => array( 7 ),
			);
			$recorded = array( 'documents' => array( $document ) );
			$current  = array(
				'products'  => array(
					array(
						'product_id' => 7,
						'documents'  => array( 'fixture-document' ),
					),
				),
				'documents' => array( array_merge( $document, array( 'document_revision' => 'new-metadata-revision' ) ) ),
			);
			$view     = CertificateEvidence::current_access( $recorded, $current );
			self::assertSame( 'available', $view['documents'][0]['access']['status'] );
			self::assertStringContainsString( 'linker_document_sha256=' . $sha, $view['documents'][0]['access']['url'] );
			self::assertSame( 'recorded-revision', $view['documents'][0]['document_revision'] );
			self::assertArrayNotHasKey( 'access', $recorded['documents'][0] );
			$current['documents'][0]['blob_sha256'] = str_repeat( '0', 64 );
			self::assertSame( 'source_changed', CertificateEvidence::current_access( $recorded, $current )['documents'][0]['access']['status'] );
			$current['products'] = array();
			self::assertSame( 'unavailable', CertificateEvidence::current_access( $recorded, $current )['documents'][0]['access']['status'] );
			self::assertNull( CertificateEvidence::current_access( $recorded, null )['documents'][0]['access']['url'] );
		} finally {
			unlink( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- own confined fixture reclaimed immediately.
		}
	}
}

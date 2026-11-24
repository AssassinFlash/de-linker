<?php
/**
 * Localized labels and ownership of shared published manuals.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\LiveDocuments;
use WP_Mock;
use WP_Mock\Tools\TestCase;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

/** Source identity and localized display are checked independently. */
final class LiveDocumentsTest extends TestCase {
	/** The file owner may be a sibling; the label follows the checked target model. */
	public function test_shared_manual_labels_and_permissions(): void {
		WP_Mock::userFunction( '__', array( 'return' => static fn( string $text ): string => $text ) );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- Implement the native function in the WP_Mock fixture.
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $part ): mixed => parse_url( $url, $part ) ) );
		$products = array();
		foreach ( array(
			1 => 'CB2-57.3-HV5',
			2 => 'CB2-100.3-HV5',
		) as $id => $model ) {
			$products[] = array(
				'product_id'           => $id,
				'model'                => $model,
				'published_locale_ids' => array( $id + 100 ),
			);
		}
		foreach ( array(
			'Quick-Installation-Guide_EN' => array( 'Quick installation guide', 'Kurzanleitung zur Installation' ),
			'User-Manual_EN_V0.0'         => array( 'User manual', 'Benutzerhandbuch' ),
		) as $file => $purposes ) {
			$url      = 'https://de-linker.test/wp-content/uploads/2026/10/SAJ_CB2_57.3-100.3-HV5_' . $file . '.pdf';
			$document = array(
				'document_id'       => 'd1',
				'document_revision' => 'v1',
				'url'               => $url,
				'product_ids'       => array( 1, 2 ),
				'type'              => 'manual',
				'lang'              => 'en',
			);
			$manifest = array(
				'documents' => array( $document ),
				'products'  => $products,
			);
			$block    = array(
				'url'                 => $url . '#page=1',
				'document_id'         => 'd1',
				'document_revision'   => 'v1',
				'label'               => 'Manual',
				'evidence_product_id' => 1,
			);
			foreach ( array( 'en', 'de' ) as $i => $locale ) {
				$result = LiveDocuments::present( $block, $manifest, array( 102 ), $locale );
				self::assertSame( $block['url'], $result['url'] );
				self::assertStringContainsString( 'CB2-100.3-HV5 · ' . $purposes[ $i ], $result['label'] );
				self::assertStringNotContainsString( 'CB2-57.3-HV5', $result['label'] );
				self::assertStringEndsWith( ( 'de' === $locale ? 'S.' : 'p.' ) . "\u{00a0}1", $result['label'] );
			}
			self::assertNull( LiveDocuments::present( $block, $manifest, array( 999 ), 'en' )['url'] );
			$block['evidence_product_id'] = 999;
			self::assertNull( LiveDocuments::present( $block, $manifest, array( 2 ), 'en' )['url'] );
		}
	}
}

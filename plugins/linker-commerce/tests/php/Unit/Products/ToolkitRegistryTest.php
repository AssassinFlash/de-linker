<?php
/**
 * The November engineering toolkit files approved for publication.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\ToolkitRegistry;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Public engineering toolkit registry.
 *
 * @covers \Linker\Commerce\Products\ToolkitRegistry
 */
final class ToolkitRegistryTest extends TestCase {
	/** Every public URL serves its exact approved language edition. */
	public function test_approved_editions_match_original_bytes(): void {
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://linker.test' );
		$approved = array(
			'linker-b2b-storage-inverter-comparison-2026-en.pdf' => array( 1856569, '45edccfcc550a00652d716b0b17000059c3d5bf681fc292187fa8e8237cf2ce4', 'en' ),
			'linker-gewerbe-heimspeicher-vergleich-2026-de.pdf' => array( 1860444, 'c9b5761fe8fc06c8b0acf95333d4aedc23d3cb85d570baae4d1e2d7985bced8c', 'de-DE' ),
			'linker-inverter-battery-compatibility-list-2026-11-en.pdf' => array( 362635, 'a60abc4c091c9326ad2f8ec3e4ae72cc3c2d392345861d5682e136241dfb7fc9', 'en' ),
			'linker-speicher-freigabeliste-kompatibilitaet-2026-11-de.pdf' => array( 367300, 'dcad7e2a35c3a41ebdd4881dd7d72c8221279f3cd7cd285a0df15348ac57080f', 'de-DE' ),
			'linker-ci-storage-project-intake-sheet-en.pdf' => array( 326737, '4631d8ec3b9388c465275c6663f358ee4aa2d2a04b94c1cff6216293e8b5b0d7', 'en' ),
			'linker-projekterfassungsbogen-gewerbespeicher-de.pdf' => array( 334050, '2d61b49c0908fe0b122ccaff4c8290bcb205065d569b06a4d99f492b223581d3', 'de-DE' ),
			'linker-load-profile-template-15min-en.csv' => array( 5067, 'ab90f6dd1d70da533780906d91cdfb01360a87a02fae05c37aa8700e3fe21d4b', 'en' ),
			'linker-vorlage-lastgang-15min-de.csv'      => array( 5226, '67fd9931c1890004c1cacf602ce7f587dafb59dc36e2a2abeec54b342314f29c', 'de-DE' ),
		);
		$items    = ToolkitRegistry::all();
		self::assertSame( array_keys( $approved ), array_column( $items, 'filename' ) );
		foreach ( $items as $asset ) {
			$name                            = $asset['filename'];
			list( $bytes, $hash, $language ) = $approved[ $name ];
			self::assertSame( $bytes, filesize( $asset['path'] ) );
			self::assertSame( $hash, hash_file( 'sha256', $asset['path'] ) );
			self::assertSame( $hash, $asset['sha256'] );
			self::assertSame( $bytes, $asset['bytes'] );
			self::assertSame( $language, $asset['content_language'] );
			self::assertSame( str_ends_with( $name, '.pdf' ) ? 'application/pdf' : 'text/csv; charset=utf-8', $asset['mime'] );
			self::assertSame( 'https://linker.test/downloads/engineering-toolkit/' . $name, $asset['url'] );
			self::assertSame( $asset, ToolkitRegistry::find_by_filename( $name ) );
		}
		self::assertCount( 6, ToolkitRegistry::pdfs() );
		foreach ( array( 'en', 'de' ) as $lang ) {
			$cards = ToolkitRegistry::cards_for_locale( $lang );
			self::assertSame( array( 'comparison', 'compatibility', 'intake', 'load-profile' ), array_column( $cards, 'suite' ) );
			foreach ( $cards as $card ) {
				self::assertSame( $lang, $card['lang'] );
				self::assertNotSame( $lang, $card['alt_lang'] );
				self::assertSame( ToolkitRegistry::find_by_filename( $card['alt_filename'] )['url'] ?? null, $card['alt_url'] );
			}
		}
		self::assertNull( ToolkitRegistry::find_by_filename( '../' . $items[0]['filename'] ) );
		self::assertNull( ToolkitRegistry::find_by_filename( 'absent.pdf' ) );
	}
}

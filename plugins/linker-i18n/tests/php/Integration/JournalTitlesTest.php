<?php
/**
 * Concise discovery labels and full reading titles through HTTP.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions.strip_tags_strip_tags -- HTTP driver runs outside WordPress.

/**
 * Native discovery labels observed through their public HTTP pages.
 *
 * @coversNothing
 */
final class JournalTitlesTest extends SiteTestCase {

	/** Editorial card labels do not replace full native document titles. */
	public function test_discovery_is_concise_and_the_reader_keeps_the_full_title(): void {
		$cases = array(
			array( '/blog/', '/hybrid-inverter-vs-ac-coupled-storage/', 'Hybrid inverter or AC storage?', 'Pairing inverters and batteries', 'Sizing home storage for backup', 'How to Choose Between a Hybrid Inverter and an AC-Coupled Storage Setup', 'Planning commercial battery storage' ),
			array( '/de/blog/', '/de/hybridwechselrichter-vs-ac-speicher/', 'Hybridwechselrichter oder AC-Speicher?', 'Wechselrichter und Batterie kombinieren', 'Heimspeicher für Notstrom auslegen', 'So wählen Sie zwischen einem Hybrid-Wechselrichter und einer AC-gekoppelten Speicherlösung', 'Gewerbespeicher planen' ),
		);
		foreach ( $cases as $case ) {
			$index = self::get( $case[0] );
			self::assertSame( 200, $index['status'] );
			preg_match_all( '#<article class="journal-card">(.*?)</article>#s', $index['body'], $cards );
			self::assertCount( 10, $cards[1] );
			foreach ( array_slice( $case, 2, 3 ) as $position => $label ) {
				preg_match( '#<h3>(.*?)</h3>#s', $cards[1][ $position ], $heading );
				self::assertSame( $label, html_entity_decode( trim( strip_tags( $heading[1] ?? '' ) ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
			}
			preg_match( '#<h3>(.*?)</h3>#s', $cards[1][9], $heading );
			self::assertSame( $case[6], html_entity_decode( trim( strip_tags( $heading[1] ?? '' ) ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ), 'Entity-formatted C&I titles still receive their reviewed discovery label.' );
			$reader = self::get( $case[1] );
			self::assertSame( 200, $reader['status'] );
			preg_match( '#<h1[^>]*>(.*?)</h1>#s', $reader['body'], $heading );
			self::assertSame( $case[5], html_entity_decode( trim( strip_tags( $heading[1] ?? '' ) ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
			self::assertStringContainsString( '<title>' . $case[5] . ' | Linker</title>', $reader['body'] );
		}
	}
}

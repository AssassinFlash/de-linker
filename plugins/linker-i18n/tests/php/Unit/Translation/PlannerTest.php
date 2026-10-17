<?php
/**
 * Incremental translation follows English without manual approval locks.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\Aligner;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Planner;
use Linker\I18n\Translation\Segmenter;
use WP_Mock\Tools\TestCase;

/**
 * Checks incremental updates and recovery of historical locks.
 *
 * @covers \Linker\I18n\Translation\Planner
 * @covers \Linker\I18n\Translation\FieldPlan
 */
final class PlannerTest extends TestCase {

	private const ENGLISH = '<p>First paragraph.</p><p>Second paragraph.</p>';
	private const GERMAN  = '<p>Erster Absatz.</p><p>Zweiter Absatz.</p>';

	/**
	 * Builds a planner over the real segmenter and aligner.
	 */
	private function planner(): Planner {
		return new Planner( new Segmenter( new HtmlTokenizer() ), new Aligner() );
	}

	/**
	 * Last successful translation of the two paragraphs.
	 *
	 * @return array{src: list<string>, out: list<string>, conflict: bool}
	 */
	private function unit(): array {
		return array(
			'src'      => $this->planner()->split( self::ENGLISH, true )->hashes(),
			'out'      => $this->planner()->split( self::GERMAN, true )->hashes(),
			'conflict' => false,
		);
	}

	/**
	 * Missing German is translated; German without a baseline is adopted as-is.
	 */
	public function test_missing_baseline_keeps_existing_german(): void {
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, null, null, false )->missing() );
		$plan = $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), null, false );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( self::GERMAN, $plan->render( array() ) );
	}

	/**
	 * An unchanged English field keeps the German byte for byte.
	 */
	public function test_unchanged_english_keeps_german(): void {
		$plan = $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), $this->unit(), false );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( self::GERMAN, $plan->render( array() ) );
	}

	/**
	 * Only changed English goes to the model, even after a German manual edit.
	 */
	public function test_changed_english_replaces_a_manually_edited_german_segment(): void {
		$english = str_replace( 'Second', 'Updated second', self::ENGLISH );
		$german  = str_replace( 'Zweiter Absatz.', 'Von Hand bearbeitet.', self::GERMAN );
		$plan    = $this->planner()->plan( $english, true, array( $german, true ), $this->unit(), false );
		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertSame( '<p>Erster Absatz.</p><p>Aktualisierter Absatz.</p>', $plan->render( array( 1 => 'Aktualisierter Absatz.' ) ) );
	}

	/**
	 * A manual edit in an unchanged segment does not cause extra model work.
	 */
	public function test_unchanged_manual_german_survives_another_segments_change(): void {
		$english = str_replace( 'Second', 'Updated second', self::ENGLISH );
		$german  = str_replace( 'Erster Absatz.', 'Manueller erster Absatz.', self::GERMAN );
		$plan    = $this->planner()->plan( $english, true, array( $german, true ), $this->unit(), false );
		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertStringContainsString( 'Manueller erster Absatz.', $plan->render( array( 1 => 'Aktualisiert.' ) ) );
	}

	/**
	 * Structural changes retain the entire German field as a visible exception.
	 */
	public function test_insertions_and_deletions_preserve_german(): void {
		$removed = $this->planner()->plan( '<p>First paragraph.</p>', true, array( self::GERMAN, true ), $this->unit(), false );
		$this->assertSame( array(), $removed->missing() );
		$this->assertTrue( $removed->mismatch );
		$this->assertSame( self::GERMAN, $removed->render( array() ) );
		$inserted = $this->planner()->plan( '<p>New paragraph.</p>' . self::ENGLISH, true, array( self::GERMAN, true ), $this->unit(), false );
		$this->assertTrue( $inserted->mismatch );
		$this->assertSame( array(), $inserted->missing() );
		$this->assertSame( self::GERMAN, $inserted->render( array() ) );
	}

	/**
	 * Historical flags never force a rewrite. Unalignable changed English is blocked.
	 */
	public function test_historical_conflicts_and_unalignable_fields_are_preserved(): void {
		$unit             = $this->unit();
		$unit['conflict'] = true;
		$this->assertSame( array(), $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), $unit, false )->missing() );
		$plan = $this->planner()->plan( str_replace( 'First', 'Changed', self::ENGLISH ), true, array( '<p>Neu strukturiert.</p>', true ), $this->unit(), false );
		$this->assertTrue( $plan->mismatch );
		$this->assertSame( '<p>Neu strukturiert.</p>', $plan->render( array() ) );
	}

	/**
	 * Even legacy forced jobs cannot erase existing German.
	 */
	public function test_force_preserves_existing_german(): void {
		$this->assertSame( array(), $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), $this->unit(), true )->missing() );
	}

	/**
	 * Existing German inline markup remains valid when another segment changes.
	 */
	public function test_german_with_different_inline_markup_is_kept_verbatim(): void {
		$english     = '<p><strong>First paragraph.</strong></p><p>Updated second paragraph.</p>';
		$unit        = $this->unit();
		$unit['src'] = $this->planner()->split( '<p><strong>First paragraph.</strong></p><p>Second paragraph.</p>', true )->hashes();
		$plan        = $this->planner()->plan( $english, true, array( self::GERMAN, true ), $unit, false );
		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertSame( '<p>Erster Absatz.</p><p>Neu.</p>', $plan->render( array( 1 => 'Neu.' ) ) );
	}

	/**
	 * Changing one sentence does not normalise the untouched German sentence's bytes.
	 */
	public function test_only_one_sentence_inside_a_paragraph_changes(): void {
		$original = '<p>First sentence. Second sentence.</p>';
		$german   = '<p class="manual">Erster  Satz. Zweiter Satz.</p>';
		$unit     = array(
			'src'      => $this->planner()->split( $original, true )->hashes(),
			'out'      => array(),
			'conflict' => true,
		);
		$plan     = $this->planner()->plan( str_replace( 'Second', 'New second', $original ), true, array( $german, true ), $unit, false );
		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertSame( '<p class="manual">Erster  Satz. Neuer zweiter Satz.</p>', $plan->render( array( 1 => 'Neuer zweiter Satz.' ) ) );
	}

	/**
	 * Localisation applies to newly translated fragments, never preserved German.
	 */
	public function test_new_fragments_only_are_localised(): void {
		$english = '<p>First sentence.</p><p>Second sentence.</p>';
		$german  = '<p><a href="/products/">Manueller Link.</a></p><p>Zweiter Satz.</p>';
		$unit    = array(
			'src'      => $this->planner()->split( $english, true )->hashes(),
			'out'      => array(),
			'conflict' => false,
		);
		$plan    = $this->planner()->plan( str_replace( 'Second', 'New second', $english ), true, array( $german, true ), $unit, false );
		$seen    = array();
		$output  = $plan->render(
			array( 1 => 'Neu.' ),
			static function ( string $html ) use ( &$seen ): string {
				$seen[] = $html;
				return $html;
			}
		);
		$this->assertSame( array( 'Neu.' ), $seen );
		$this->assertSame( '<p><a href="/products/">Manueller Link.</a></p><p>Neu.</p>', $output );
	}
}

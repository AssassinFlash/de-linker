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
	 * Missing German and missing baseline both require a complete translation.
	 */
	public function test_missing_baseline_translates_every_segment(): void {
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, null, null, false )->missing() );
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), null, false )->missing() );
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
	 * Deleting English removes its German; inserting English translates only it.
	 */
	public function test_insertions_and_deletions_reuse_aligned_segments(): void {
		$removed = $this->planner()->plan( '<p>First paragraph.</p>', true, array( self::GERMAN, true ), $this->unit(), false );
		$this->assertSame( array(), $removed->missing() );
		$this->assertSame( '<p>Erster Absatz.</p>', $removed->render( array() ) );
		$inserted = $this->planner()->plan( '<p>New paragraph.</p>' . self::ENGLISH, true, array( self::GERMAN, true ), $this->unit(), false );
		$this->assertSame( array( 0 ), $inserted->missing() );
		$this->assertSame( '<p>Neu.</p>' . self::GERMAN, $inserted->render( array( 0 => 'Neu.' ) ) );
	}

	/**
	 * Historical conflicts and changed German structures are rebuilt from English.
	 */
	public function test_historical_conflicts_and_unalignable_fields_are_retranslated(): void {
		$unit             = $this->unit();
		$unit['conflict'] = true;
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), $unit, false )->missing() );
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, array( '<p>Neu strukturiert.</p>', true ), $this->unit(), false )->missing() );
	}

	/**
	 * Explicit retranslation rebuilds all segments.
	 */
	public function test_force_translates_everything(): void {
		$this->assertSame( array( 0, 1 ), $this->planner()->plan( self::ENGLISH, true, array( self::GERMAN, true ), $this->unit(), true )->missing() );
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
		$this->assertSame( '<p><strong>Erster Absatz.</strong></p><p>Neu.</p>', $plan->render( array( 1 => 'Neu.' ) ) );
	}
}

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
	 * An empty German field accepted in a baseline stays empty while English is unchanged.
	 */
	public function test_unchanged_english_does_not_fill_an_adopted_empty_field(): void {
		$plan = $this->planner()->plan( self::ENGLISH, true, null, $this->unit(), false );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( '', $plan->render( array() ) );
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
	 * Anchored insertions/deletions keep shifted German slots and their exact markup.
	 *
	 * @dataProvider sentence_edits
	 * @param string             $old Previous English.
	 * @param string             $german Human German.
	 * @param string             $next Current English.
	 * @param string             $expected Expected German.
	 * @param array<int, string> $translations Only new/changed sentences.
	 * @param bool               $blocked Whether alignment is ambiguous.
	 */
	public function test_sentence_edits( string $old, string $german, string $next, string $expected, array $translations, bool $blocked = false ): void {
		$unit = array(
			'src'      => $this->planner()->split( $old, true )->hashes(),
			'out'      => array(),
			'conflict' => false,
		);
		$plan = $this->planner()->plan( $next, true, array( $german, true ), $unit, false );
		$this->assertSame( $blocked, $plan->mismatch );
		$this->assertSame( array_keys( $translations ), $plan->missing() );
		$this->assertSame( $expected, $plan->render( $translations ) );
	}

	/**
	 * Sentence positions include ordinary text, complete paragraphs and shifted attributes.
	 *
	 * @return array<string, array{string, string, string, string, array<int, string>, bool}>
	 */
	public function sentence_edits(): array {
		return array(
			'paragraph prepend'               => array( self::ENGLISH, self::GERMAN, '<p>New paragraph.</p>' . self::ENGLISH, '<p>Neu.</p>' . self::GERMAN, array( 0 => 'Neu.' ), false ),
			'paragraph append'                => array( self::ENGLISH, self::GERMAN, self::ENGLISH . '<p>New paragraph.</p>', self::GERMAN . '<p>Neu.</p>', array( 2 => 'Neu.' ), false ),
			'paragraph deletion'              => array( self::ENGLISH, self::GERMAN, '<p>First paragraph.</p>', '<p>Erster Absatz.</p>', array(), false ),
			'middle insertion'                => array( '<p>First. Last.</p>', "<p class='manual'>Erster  Satz. Letzter Satz.</p>", '<p>First. New. Last.</p>', "<p class='manual'>Erster  Satz. Neu. Letzter Satz.</p>", array( 1 => 'Neu.' ), false ),
			'last insertion'                  => array( '<p>First.</p>', "<p class='manual'>Erster  Satz.</p>", '<p>First. New.</p>', "<p class='manual'>Erster  Satz. Neu.</p>", array( 1 => 'Neu.' ), false ),
			'first insertion'                 => array( '<p>First.</p>', '<p>Erster.</p>', '<p>New. First.</p>', '<p>Neu. Erster.</p>', array( 0 => 'Neu.' ), false ),
			'middle deletion'                 => array( '<p>First. Middle. Last.</p>', '<p>Erster  Satz. Mitte. Letzter Satz.</p>', '<p>First. Last.</p>', '<p>Erster  Satz. Letzter Satz.</p>', array(), false ),
			'last deletion'                   => array( '<p>First. Last.</p>', '<p>Erster  Satz. Letzter.</p>', '<p>First.</p>', '<p>Erster  Satz.</p>', array(), false ),
			'wrapped insertion'               => array( '<p>First. Last.</p>', '<p>Erster. Letzter.</p>', '<p>First. New <strong>sentence</strong>. Last.</p>', '<p>Erster. Neuer <strong>Satz</strong>. Letzter.</p>', array( 1 => 'Neuer <t1>Satz</t1>.' ), false ),
			'shifted replacement attributes'  => array(
				"<p>First.</p><p>Second <a title='Download'>sentence</a>.</p>",
				"<p>Erster.</p><p>Zweiter <a title='Herunterladen'>Satz</a>.</p>",
				"<p>New.</p><p>First.</p><p>Changed <a title='Download'>sentence</a>.</p>",
				"<p>Neu.</p><p>Erster.</p><p>Geänderter <a title='Herunterladen'>Satz</a>.</p>",
				array(
					0 => 'Neu.',
					3 => 'Geänderter <t1>Satz</t1>.',
				),
				false,
			),
			'media between deleted sentences' => array( "<p>Alpha.</p><img src='/keep.png'><p>Beta.</p><p>Gamma.</p>", "<p>Alpha DE.</p><img src='/keep-de.png'><p>Beta DE.</p><p>Gamma DE.</p>", "<img src='/keep.png'><p>Gamma.</p>", "<img src='/keep-de.png'><p>Gamma DE.</p>", array(), false ),
			'attribute anchor'                => array( '<p aria-label="Old">Alpha.</p>', "<p aria-label='Alt'>Alpha DE.</p>", '<p>New.</p><p aria-label="Old">Alpha.</p>', "<p>Neu.</p><p aria-label='Alt'>Alpha DE.</p>", array( 0 => 'Neu.' ), false ),
			'insert attributed paragraph'     => array(
				'<p>Alpha.</p>',
				'<p>Alpha DE.</p>',
				'<p title="New heading">New.</p><p>Alpha.</p>',
				'<p title="Neue Überschrift">Neu.</p><p>Alpha DE.</p>',
				array(
					0 => 'Neue Überschrift',
					1 => 'Neu.',
				),
				false,
			),
			'delete attributed paragraph'     => array( '<p title="Old heading">Old.</p><p>Alpha.</p>', "<p title='Alte Überschrift'>Alt.</p><p>Alpha DE.</p>", '<p>Alpha.</p>', '<p>Alpha DE.</p>', array(), false ),
			'whole list insertion'            => array( '<p>Alpha.</p>', '<p>Alpha DE.</p>', '<ul><li>New.</li></ul><p>Alpha.</p>', '<ul><li>Neu.</li></ul><p>Alpha DE.</p>', array( 0 => 'Neu.' ), false ),
			'list item insertion'             => array( '<ul><li>Alpha.</li><li>Last.</li></ul>', '<ul><li>Alpha DE.</li><li>Letzter.</li></ul>', '<ul><li>Alpha.</li><li>New.</li><li>Last.</li></ul>', '<ul><li>Alpha DE.</li><li>Neu.</li><li>Letzter.</li></ul>', array( 1 => 'Neu.' ), false ),
			'incompatible list context'       => array( '<ul><li>Alpha.</li><li>Last.</li></ul>', '<p>Alpha DE.</p><p>Letzter.</p>', '<ul><li>Alpha.</li><li>New.</li><li>Last.</li></ul>', '<p>Alpha DE.</p><p>Letzter.</p>', array(), true ),
			'insert sentence with line break' => array( '<p>Alpha.</p>', '<p>Alpha DE.</p>', '<p>New<br>sentence.</p><p>Alpha.</p>', '<p>Neuer<br>Satz.</p><p>Alpha DE.</p>', array( 0 => 'Neuer<t1/>Satz.' ), false ),
			'reorder'                         => array( self::ENGLISH, self::GERMAN, '<p>Second paragraph.</p><p>First paragraph.</p>', self::GERMAN, array(), true ),
			'no anchor'                       => array( self::ENGLISH, self::GERMAN, '<p>New.</p>', self::GERMAN, array(), true ),
			'ambiguous repeated anchor'       => array( '<p>Same. Same.</p>', '<p>Eins. Zwei.</p>', '<p>Same. New. Same.</p>', '<p>Eins. Zwei.</p>', array(), true ),
		);
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

	/**
	 * An untouched attribute keeps its original quote style byte for byte.
	 */
	public function test_unchanged_attribute_bytes_are_not_normalised(): void {
		$english = "<p>First.</p><img alt='Battery'><p>Second.</p>";
		$german  = "<p>Erste.</p><img alt='Batterie'><p>Zweite.</p>";
		$unit    = array(
			'src'      => $this->planner()->split( $english, true )->hashes(),
			'out'      => array(),
			'conflict' => false,
		);
		$plan    = $this->planner()->plan( str_replace( 'Second', 'Changed second', $english ), true, array( $german, true ), $unit, false );
		$this->assertSame( array( 2 ), $plan->missing() );
		$this->assertSame( "<p>Erste.</p><img alt='Batterie'><p>Neu.</p>", $plan->render( array( 2 => 'Neu.' ) ) );
	}

	/**
	 * Translating a sentence may not replace its unchanged German title with English.
	 */
	public function test_changed_sentence_keeps_its_existing_german_attribute(): void {
		$english = "<p>First <a title='Download'>sentence</a>.</p>";
		$german  = "<p>Erster <a title='Herunterladen'>Satz</a>.</p>";
		$unit    = array(
			'src'      => $this->planner()->split( $english, true )->hashes(),
			'out'      => array(),
			'conflict' => false,
		);
		$plan    = $this->planner()->plan( str_replace( 'First', 'Changed first', $english ), true, array( $german, true ), $unit, false );
		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertSame( "<p>Geänderter <a title='Herunterladen'>Satz</a>.</p>", $plan->render( array( 1 => 'Geänderter <t1>Satz</t1>.' ) ) );
	}

	/**
	 * Inline sentence boundaries that cannot be split safely are visible exceptions.
	 */
	public function test_ambiguous_inline_sentence_boundary_preserves_the_whole_field(): void {
		$english = '<p>First sentence. <strong>Second sentence.</strong></p>';
		$german  = '<p>Erster Satz. <strong>Zweiter Satz.</strong></p>';
		$unit    = array(
			'src'      => $this->planner()->split( $english, true )->hashes(),
			'out'      => array(),
			'conflict' => false,
		);
		$plan    = $this->planner()->plan( str_replace( 'Second', 'Changed second', $english ), true, array( $german, true ), $unit, false );
		$this->assertTrue( $plan->mismatch );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( $german, $plan->render( array() ) );
	}

	/**
	 * Product 4107's excerpt baseline is the paragraph fingerprint from before
	 * sentence splitting. The text is unchanged, so the field stays German.
	 */
	public function test_a_paragraph_baseline_keeps_the_unchanged_product_excerpt(): void {
		$english   = '<p>SAJ H2-10K-T3 is a three-phase hybrid inverter with 10,000 W rated AC power and 11,000 VA maximum apparent power. It has three MPPTs for up to 20,000 Wp of PV, two battery inputs for 180–800 V LiFePO4 batteries and a backup output.</p>';
		$german    = '<p>Der SAJ H2-10K-T3 bleibt. Der zweite Satz bleibt.</p>';
		$segmenter = new Segmenter( new HtmlTokenizer() );
		$this->assertSame( array( '53e272e58a49121b2105e0d7dc457d28b40c875b' ), $segmenter->block_hashes( $english, true ) );
		$this->assertCount( 2, $this->planner()->split( $english, true )->segments );
		$plan = $this->planner()->plan(
			$english,
			true,
			array( $german, true ),
			array(
				'src'      => array( '53e272e58a49121b2105e0d7dc457d28b40c875b' ),
				'out'      => array( 'old-paragraph' ),
				'conflict' => false,
			),
			false
		);
		$this->assertFalse( $plan->mismatch );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( $german, $plan->render( array() ) );
	}

	/**
	 * A real edit of a paragraph-level field still cannot be aligned and stays blocked.
	 */
	public function test_a_changed_paragraph_baseline_stays_blocked(): void {
		$english = '<p>First sentence stays. Second sentence stays.</p>';
		$german  = '<p>Erster Satz bleibt. Zweiter Satz bleibt.</p>';
		$plan    = $this->planner()->plan(
			str_replace( 'Second', 'Changed second', $english ),
			true,
			array( $german, true ),
			array(
				'src'      => ( new Segmenter( new HtmlTokenizer() ) )->block_hashes( $english, true ),
				'out'      => array( 'old-paragraph' ),
				'conflict' => false,
			),
			false
		);
		$this->assertTrue( $plan->mismatch );
		$this->assertSame( $german, $plan->render( array() ) );
	}
}

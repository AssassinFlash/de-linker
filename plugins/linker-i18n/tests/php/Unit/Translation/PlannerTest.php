<?php
/**
 * Tests for the field planner.
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
 * Tests for Planner and FieldPlan: what of the German stays, what is translated.
 *
 * @covers \Linker\I18n\Translation\Planner
 * @covers \Linker\I18n\Translation\FieldPlan
 */
final class PlannerTest extends TestCase {

	private const ENGLISH = "<h3>GoodWe GW10K-EHA-G20</h3>\n<ul>\n<li><strong>Rated AC power:</strong> 10 kW</li>\n<li>Backup power: 10.0 kVA</li>\n<li>Ingress protection: IP66</li>\n</ul>";

	private const GERMAN = "<h3>GoodWe GW10K-EHA-G20</h3>\n<ul>\n<li><strong>Nenn-AC-Leistung:</strong> 10 kW</li>\n<li>Notstromleistung: 10,0 kVA</li>\n<li>Schutzart: IP66</li>\n</ul>";

	/**
	 * The planner.
	 *
	 * @var Planner
	 */
	private Planner $planner;

	/**
	 * Sets up the planner.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->planner = new Planner( new Segmenter( new HtmlTokenizer() ), new Aligner() );
	}

	/**
	 * The state after the German was written from the English.
	 *
	 * @param string $english English HTML.
	 * @param string $german  German HTML.
	 * @return array{src: list<string>, out: list<string>, conflict: bool}
	 */
	private function unit( string $english, string $german ): array {
		return array(
			'src'      => $this->planner->split( $english, true )->hashes(),
			'out'      => $this->planner->split( $german, true )->hashes(),
			'conflict' => false,
		);
	}

	/**
	 * Without German every segment is translated.
	 */
	public function test_no_german_translates_everything(): void {
		$plan = $this->planner->plan( self::ENGLISH, true, null, null, array(), false );

		$this->assertSame( array( 0, 1, 2, 3 ), $plan->missing() );
	}

	/**
	 * German nobody recorded (a person wrote it) is kept, all of it reviewed.
	 */
	public function test_unrecorded_german_is_kept_as_reviewed(): void {
		$plan = $this->planner->plan( self::ENGLISH, true, array( self::GERMAN, true ), null, array(), false );

		$this->assertSame( self::GERMAN, $plan->render( array() ) );
		$this->assertSame( '*', $plan->reviewed );
		$this->assertFalse( $plan->conflict );
	}

	/**
	 * Unchanged English keeps the German as it is.
	 */
	public function test_unchanged_english_keeps_german(): void {
		$plan = $this->planner->plan( self::ENGLISH, true, array( self::GERMAN, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( self::GERMAN, $plan->render( array() ) );
	}

	/**
	 * One changed English segment: only it is translated, the others keep
	 * their German, printed with the English markup.
	 */
	public function test_changed_segment_is_the_only_one_translated(): void {
		$english = str_replace( 'Backup power: 10.0 kVA', 'Backup power: 12.0 kVA', self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( self::GERMAN, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertSame( array( 2 ), $plan->missing() );
		$this->assertSame(
			"<h3>GoodWe GW10K-EHA-G20</h3>\n<ul>\n<li><strong>Nenn-AC-Leistung:</strong> 10 kW</li>\n<li>Notstromleistung: 12,0 kVA</li>\n<li>Schutzart: IP66</li>\n</ul>",
			$plan->render( array( 2 => 'Notstromleistung: 12,0 kVA' ) )
		);
	}

	/**
	 * A segment a person edited is detected and kept when the English beside it changes.
	 */
	public function test_person_edit_is_kept_when_other_segments_change(): void {
		$edited  = str_replace( 'Notstromleistung', 'Notstrom-Nennleistung', self::GERMAN );
		$english = str_replace( 'Ingress protection', 'Protection class', self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $edited, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertFalse( $plan->conflict );
		$this->assertSame( array( 3 ), $plan->missing() );
		$this->assertSame( array( 2 ), $plan->reviewed );
		$this->assertStringContainsString( 'Notstrom-Nennleistung: 10,0 kVA', $plan->render( array( 3 => 'Schutzklasse: <k1/>' ) ) );
	}

	/**
	 * When the English of an edited segment changes, the segment stays and
	 * waits for a review, remembering the English it was made from.
	 */
	public function test_english_change_under_a_person_edit_holds_the_segment(): void {
		$edited  = str_replace( 'Notstromleistung', 'Notstrom-Nennleistung', self::GERMAN );
		$english = str_replace( 'Backup power: 10.0 kVA', 'Backup power: 12.0 kVA', self::ENGLISH );
		$unit    = $this->unit( self::ENGLISH, self::GERMAN );

		$plan = $this->planner->plan( $english, true, array( $edited, true ), $unit, array(), false );

		$this->assertTrue( $plan->conflict );
		$this->assertSame( array(), $plan->missing() );
		$this->assertSame( $edited, $plan->render( array() ) );
		$this->assertSame( array( 2 => $unit['src'][2] ), $plan->held );
		$this->assertSame( array( 2 ), $plan->reviewed );
	}

	/**
	 * While an edited segment is held, the changed segment beside it follows
	 * the English.
	 */
	public function test_neighbour_follows_the_english_while_a_segment_is_held(): void {
		$edited  = str_replace( 'Notstromleistung', 'Notstrom-Nennleistung', self::GERMAN );
		$english = str_replace( array( 'Backup power: 10.0 kVA', 'Ingress protection' ), array( 'Backup power: 12.0 kVA', 'Protection class' ), self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $edited, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertTrue( $plan->conflict );
		$this->assertSame( array( 3 ), $plan->missing() );
		$this->assertSame(
			"<h3>GoodWe GW10K-EHA-G20</h3>\n<ul>\n<li><strong>Nenn-AC-Leistung:</strong> 10 kW</li>\n<li>Notstrom-Nennleistung: 10,0 kVA</li>\n<li>Schutzklasse: IP66</li>\n</ul>",
			$plan->render( array( 3 => 'Schutzklasse: <k1/>' ) )
		);
	}

	/**
	 * When the English of an edited segment is removed, old and new segments
	 * no longer pair up: the whole field stays for a review.
	 */
	public function test_removed_english_under_a_person_edit_keeps_the_field(): void {
		$edited  = str_replace( 'Notstromleistung', 'Notstrom-Nennleistung', self::GERMAN );
		$english = str_replace( "<li>Backup power: 10.0 kVA</li>\n", '', self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $edited, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertTrue( $plan->conflict );
		$this->assertSame( $edited, $plan->render( array() ) );
		$this->assertTrue( $plan->unit['conflict'] ?? false );
	}

	/**
	 * A segment added at the top moves the reviewed index with it.
	 */
	public function test_reviewed_index_follows_inserted_segments(): void {
		$edited  = str_replace( 'Schutzart', 'Schutzart (IEC 60529)', self::GERMAN );
		$english = str_replace( '<ul>', "<ul>\n<li>Phase: single-phase</li>", self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $edited, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertSame( array( 1 ), $plan->missing() );
		$this->assertSame( array( 4 ), $plan->reviewed );
	}

	/**
	 * A person who changed the German's structure reviewed the whole field.
	 */
	public function test_structure_change_reviews_the_field(): void {
		$restructured = str_replace( "<li>Schutzart: IP66</li>\n", '', self::GERMAN );
		$english      = str_replace( '10 kW', '12 kW', self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $restructured, true ), $this->unit( self::ENGLISH, self::GERMAN ), array(), false );

		$this->assertTrue( $plan->conflict );
		$this->assertSame( '*', $plan->reviewed );
	}

	/**
	 * Forcing translates everything, edits or not.
	 */
	public function test_force_translates_everything(): void {
		$plan = $this->planner->plan( self::ENGLISH, true, array( self::GERMAN, true ), $this->unit( self::ENGLISH, self::GERMAN ), array( 1 ), true );

		$this->assertSame( array( 0, 1, 2, 3 ), $plan->missing() );
	}

	/**
	 * German whose inline markup differs from the English (the old plugin's)
	 * is kept byte for byte rather than printed with the wrong markup.
	 */
	public function test_german_with_other_markup_is_kept_verbatim(): void {
		$german  = str_replace( '<strong>Nenn-AC-Leistung:</strong>', 'Nenn-AC-Leistung:', self::GERMAN );
		$english = str_replace( 'IP66', 'IP67', self::ENGLISH );

		$plan = $this->planner->plan( $english, true, array( $german, true ), $this->unit( self::ENGLISH, $german ), array(), false );

		$this->assertSame( array( 3 ), $plan->missing() );
		$this->assertStringContainsString( '<li>Nenn-AC-Leistung: 10 kW</li>', $plan->render( array( 3 => 'Schutzart: <k1/>' ) ) );
	}
}

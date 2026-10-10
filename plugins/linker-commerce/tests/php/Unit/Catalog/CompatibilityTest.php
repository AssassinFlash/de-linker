<?php
/**
 * Tests for the compatibility contract's pattern matching.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\Compatibility;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Compatibility: the shipped data/compatibility.json decides the
 * known pairs the way the old contract's cells did, with the #14 engine's
 * join semantics — every matching pair applies, the verdict is the most
 * restrictive one (docs/specs/8-engineering-data.md, decisions in
 * docs/specs/8-decisions.md §6).
 *
 * @covers \Linker\Commerce\Catalog\Compatibility
 */
final class CompatibilityTest extends TestCase {

	/**
	 * Ten known inverter-and-battery pairs decide to the verdict their old
	 * contract cell states, including released_with_accessory and
	 * not_released (the ticket's acceptance line).
	 *
	 * @dataProvider known_pairs
	 *
	 * @param string      $inverter The inverter model (pa_model).
	 * @param string      $battery  The battery model (pa_model).
	 * @param string|null $verdict  The verdict, null when no entry matches.
	 */
	public function test_known_pairs_decide_their_verdict( string $inverter, string $battery, ?string $verdict ): void {
		$answer = Compatibility::for_models( $inverter, $battery );

		if ( null === $verdict ) {
			$this->assertNull( $answer );

			return;
		}
		$this->assertNotNull( $answer );
		$this->assertSame( $verdict, $answer['verdict'] );
		$this->assertNotSame( array(), $answer['conditions'] );
		$this->assertNotSame( array(), $answer['documents'] );
	}

	/**
	 * The pairs: model names as the products' pa_model terms state them.
	 *
	 * @return list<array{string, string, string|null}>
	 */
	public function known_pairs(): array {
		return array(
			// gw-et-5-10|pyl-fh2: one_way -> released with the one-way condition.
			array( 'GW10K-ET', 'FH9637M', 'released' ),
			// gw-et-5-10|gw-lynx-d: listed.
			array( 'GW10K-ET', 'LX D5.0-10', 'released' ),
			// gw-et-5-10|pyl-fh1: not_listed -> not_released.
			array( 'GW10K-ET', 'FH48074', 'not_released' ),
			// saj-h2-t3|saj-bat: the B2 set runs through the BC2-HV1 control module.
			array( 'H2-10K-T3', 'B2-10.0-HV1', 'released_with_accessory' ),
			array( 'H2-10K-T3', 'BU2-5.0-HV1', 'released_with_accessory' ),
			// eco-po|eco-po-b: every tower takes the battery base article.
			array( 'EF HD-P1-5K-S1', 'EF BD-5.1-S1', 'released_with_accessory' ),
			// eco-ocean2-p3|eco-ocean2-bat: listed; the junction box is a condition of cascading.
			array( 'EF HD-P3-10K0-S2', 'EF BD-5-S2', 'released' ),
			// gw-etr-125k: listed and one_way.
			array( 'GW125K-ETR-G10', 'GW261.2-BAT-LCD-G10', 'released' ),
			array( 'GW125K-ETR-G10', 'GW208.9-BAT-LCD-G10', 'released' ),
			// saj-ek90-hs5|saj-ek90-bu5: the EK90 box is in the model names themselves.
			array( 'EK90 HS5-8K-T3-X', 'EK90 BU5-6.0-TV', 'released' ),
			// saj-hs2|saj-bat, scoped to BU2-5.0-HV1/5.
			array( 'HS2-10K-T2-X', 'BU2-5.0-HV1', 'released' ),
			// saj-hs2 with a battery family no cell releases for it.
			array( 'HS2-10K-T2-X', 'FH9637M', 'not_released' ),
			// gw-esa-eha|gw-esa-bat-g20: the ESA's own modules.
			array( 'GW5K-ETA-G20', 'GW6.0-BAT-D-G20', 'released' ),
			// An inverter the contract does not know answers nothing.
			array( 'GEN24 5.0', 'FH9637M', null ),
		);
	}

	/**
	 * Conditions are bilingual objects (the file folds the old parallel
	 * arrays), and documents are the slim {url, page?} references.
	 */
	public function test_conditions_are_bilingual_and_documents_are_slim(): void {
		$answer = Compatibility::for_models( 'GW10K-ET', 'FH9637M' );

		$this->assertNotNull( $answer );
		foreach ( $answer['conditions'] as $condition ) {
			$this->assertNotSame( '', $condition['en'] );
			$this->assertNotSame( '', $condition['de'] );
		}
		foreach ( $answer['documents'] as $document ) {
			$this->assertStringStartsWith( 'https://de-linker.com/', $document['url'] );
			$keys = array_keys( $document );
			$this->assertNotContains( 'title', $keys, 'documents carry no titles' );
			$this->assertNotContains( 'title_de', $keys, 'documents carry no German titles' );
		}
	}

	/**
	 * A released_with_accessory answer names the accessory the documents
	 * require: model pattern, quantity and what it is per.
	 */
	public function test_released_with_accessory_names_its_accessory(): void {
		$answer = Compatibility::for_models( 'H2-10K-T3', 'B2-10.0-HV1' );

		$this->assertNotNull( $answer );
		$this->assertSame(
			array(
				'model'    => '^BC2-HV1$',
				'quantity' => 1,
				'per'      => 'system',
			),
			$answer['accessories'][0]
		);
		$ecoflow = Compatibility::for_models( 'EF HD-P1-5K-S1', 'EF BD-5.1-S1' );
		$this->assertNotNull( $ecoflow );
		$this->assertSame( '^EF BD-B-S1$', $ecoflow['accessories'][0]['model'] );
		$this->assertSame( 'stack', $ecoflow['accessories'][0]['per'] );
	}

	/**
	 * The model-level entry joins with its family entry, the way the engine
	 * reads the file: the OCEAN 2 battery-model condition is part of the
	 * answer beside the family constraint.
	 */
	public function test_the_model_level_entry_joins_its_family_entry(): void {
		$answer = Compatibility::for_models( 'EF HD-P3-10K0-S2', 'EF BD-5-S2' );

		$this->assertNotNull( $answer );
		$joined = implode( "\n", array_column( $answer['conditions'], 'en' ) );
		$this->assertStringContainsString( 'The OCEAN 2 three-phase datasheet (p. 3) lists EF BD-5-S2 for its battery system.', $joined );
		$this->assertStringContainsString( 'junction box EF BD-JC-S2', $joined );
	}

	/**
	 * When entries that match disagree, the most restrictive verdict wins
	 * (not_released < released_with_accessory < released): the one-module
	 * B2-5.0 answers released_with_accessory even though a model-level
	 * entry repeats the family release.
	 */
	public function test_the_most_restrictive_verdict_wins(): void {
		$answer = Compatibility::for_models( 'H2-10K-T3', 'B2-5.0-HV1' );

		$this->assertNotNull( $answer );
		$this->assertSame( 'released_with_accessory', $answer['verdict'] );
		// The one-module voltage caveat is part of the joined conditions.
		$joined = implode( "\n", array_column( $answer['conditions'], 'en' ) );
		$this->assertStringContainsString( 'B2-5.0', $joined );
		$this->assertStringContainsString( '115.2 V', $joined );
	}

	/**
	 * Every pattern of the file compiles: a malformed pattern would be loud
	 * in production (PHP warns) and match nothing here, so it must be seen.
	 */
	public function test_every_pattern_of_the_file_compiles(): void {
		$patterns = array();
		foreach ( Compatibility::pairs() as $pair ) {
			$patterns[] = (string) $pair['inverter'];
			$patterns[] = (string) $pair['battery'];
		}
		$this->assertNotEmpty( $patterns );
		foreach ( $patterns as $index => $pattern ) {
			// The point is the compile failure; the silencer hides PHP's warning so it can be asserted instead.
			// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged
			$result = @preg_match( '{' . $pattern . '}', 'anything' );
			$this->assertNotFalse( $result, "pattern #{$index} of the file does not compile: {$pattern}" );
		}
	}

	/**
	 * Every verdict the file states is one of the three.
	 */
	public function test_the_file_states_known_verdicts(): void {
		$verdicts = array();
		foreach ( Compatibility::pairs() as $pair ) {
			$verdicts[ $pair['verdict'] ] = true;
		}
		$this->assertSame( array(), array_values( array_diff( array_keys( $verdicts ), Compatibility::VERDICTS ) ) );
		$this->assertSame( array( 'released', 'not_released', 'released_with_accessory' ), array_keys( $verdicts ) );
	}

	/**
	 * Every on-sale ETR model hits the parallel_controller requirement: one
	 * SEC3000C per system. The pattern matches the bare pa_model name — a
	 * brand prefix would leave all six without the requirement.
	 *
	 * @dataProvider on_sale_etr_models
	 *
	 * @param string $inverter The inverter model (pa_model).
	 */
	public function test_the_parallel_controller_requirement_hits_every_on_sale_etr( string $inverter ): void {
		$answer = Compatibility::requirements( $inverter, 'parallel_controller' );

		$this->assertCount( 1, $answer, "exactly one parallel_controller requirement for {$inverter}" );
		$this->assertSame( 'parallel_controller', $answer[0]['kind'] );
		$this->assertFalse( (bool) $answer[0]['included'] );
		$this->assertSame(
			array(
				'model'    => '^SEC3000C$',
				'quantity' => 1,
				'per'      => 'system',
			),
			$answer[0]['accessories'][0]
		);
		$this->assertNotSame( array(), $answer[0]['conditions'] );
		$this->assertNotSame( array(), $answer[0]['documents'] );
	}

	/**
	 * The six on-sale ETR models, as the products' pa_model terms state them.
	 *
	 * @return list<list<string>>
	 */
	public function on_sale_etr_models(): array {
		return array(
			array( 'GW80K-ETR-G10' ),
			array( 'GW99.99K-ETR-G10' ),
			array( 'GW100K-ETR-G10' ),
			array( 'GW110K-ETR-G10' ),
			array( 'GW124.99K-ETR-G10' ),
			array( 'GW125K-ETR-G10' ),
		);
	}

	/**
	 * Two products decide through their pa_model terms, the way the feed
	 * names them.
	 */
	public function test_for_products_reads_the_model_terms(): void {
		$this->mock_model( 4107, 'H2-10K-T3' );
		$this->mock_model( 2067, 'B2-10.0-HV1' );

		$answer = Compatibility::for_products( 4107, 2067 );

		$this->assertNotNull( $answer );
		$this->assertSame( 'released_with_accessory', $answer['verdict'] );
	}

	/**
	 * A product without a model term answers nothing.
	 */
	public function test_for_products_without_a_model_answers_nothing(): void {
		$this->mock_model( 4107, 'H2-10K-T3' );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'args'   => array( 2067, 'pa_model' ),
				'return' => false,
			)
		);

		$this->assertNull( Compatibility::for_products( 4107, 2067 ) );
	}

	/**
	 * Mocks the product's single pa_model term.
	 *
	 * @param int    $id   Product ID.
	 * @param string $name The term's name.
	 */
	private function mock_model( int $id, string $name ): void {
		$term       = new \stdClass();
		$term->slug = strtolower( (string) preg_replace( '/[^a-z0-9]+/i', '-', $name ) );
		$term->name = $name;
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'args'   => array( $id, 'pa_model' ),
				'return' => array( $term ),
			)
		);
	}
}

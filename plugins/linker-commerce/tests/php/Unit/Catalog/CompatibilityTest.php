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
 * known pairs the way the old contract's cells did (docs/specs/
 * 8-engineering-data.md, decisions in docs/specs/8-decisions.md).
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
	 * @param string      $inverter "<brand> <model>" of the inverter.
	 * @param string      $battery "<brand> <model>" of the battery.
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
		$this->assertSame( count( $answer['conditions'] ), count( $answer['conditions_de'] ) );
	}

	/**
	 * The pairs: model names as the products' pa_model terms state them.
	 *
	 * @return list<array{string, string, string|null}>
	 */
	public function known_pairs(): array {
		return array(
			// gw-et-5-10|pyl-fh2: one_way -> released with the one-way condition.
			array( 'GoodWe GW10K-ET', 'Pylontech FH9637M', 'released' ),
			// gw-et-5-10|gw-lynx-d: listed.
			array( 'GoodWe GW10K-ET', 'GoodWe LX D5.0-10', 'released' ),
			// gw-et-5-10|pyl-fh1: not_listed -> not_released.
			array( 'GoodWe GW10K-ET', 'Pylontech FH48074', 'not_released' ),
			// saj-h2-t3|saj-bat: the B2 set runs through the BC2-HV1 control module.
			array( 'SAJ H2-10K-T3', 'SAJ B2-10.0-HV1', 'released_with_accessory' ),
			array( 'SAJ H2-10K-T3', 'SAJ BU2-5.0-HV1', 'released_with_accessory' ),
			// eco-po|eco-po-b: every tower takes the battery base article.
			array( 'EcoFlow EF HD-P1-5K-S1', 'EcoFlow EF BD-5.1-S1', 'released_with_accessory' ),
			// eco-ocean2-p3|eco-ocean2-bat: listed; the junction box is a condition of cascading.
			array( 'EcoFlow EF HD-P3-10K0-S2', 'EcoFlow EF BD-5-S2', 'released' ),
			// gw-etr-125k: listed and one_way.
			array( 'GoodWe GW125K-ETR-G10', 'GoodWe GW261.2-BAT-LCD-G10', 'released' ),
			array( 'GoodWe GW125K-ETR-G10', 'GoodWe GW208.9-BAT-LCD-G10', 'released' ),
			// saj-ek90-hs5|saj-ek90-bu5: the EK90 box is in the model names themselves.
			array( 'SAJ EK90 HS5-8K-T3-X', 'SAJ EK90 BU5-6.0-TV', 'released' ),
			// saj-hs2|saj-bat, scoped to BU2-5.0-HV1/5.
			array( 'SAJ HS2-10K-T2-X', 'SAJ BU2-5.0-HV1', 'released' ),
			// saj-hs2 with a battery family no cell releases for it.
			array( 'SAJ HS2-10K-T2-X', 'Pylontech FH9637M', 'not_released' ),
			// gw-esa-eha|gw-esa-bat-g20: the ESA's own modules.
			array( 'GoodWe GW5K-ETA-G20', 'GoodWe GW6.0-BAT-D-G20', 'released' ),
			// An inverter the contract does not know answers nothing.
			array( 'Fronius GEN24 5.0', 'Pylontech FH9637M', null ),
		);
	}

	/**
	 * A model-level entry decides before its family entry: the OCEAN 2
	 * three-phase battery-model condition, not the family constraint, is the
	 * first condition.
	 */
	public function test_the_model_level_entry_decides_before_its_family_entry(): void {
		$answer = Compatibility::for_models( 'EcoFlow EF HD-P3-10K0-S2', 'EcoFlow EF BD-5-S2' );

		$this->assertNotNull( $answer );
		$this->assertSame( 'The OCEAN 2 three-phase datasheet (p. 3) lists EF BD-5-S2 for its battery system.', $answer['conditions'][0] );
	}

	/**
	 * The one-module B2-5.0 stays inside the H2 cell's release only with its
	 * voltage caveat stated, as the old constraint did.
	 */
	public function test_the_one_module_b2_carries_its_voltage_caveat(): void {
		$answer = Compatibility::for_models( 'SAJ H2-10K-T3', 'SAJ B2-5.0-HV1' );

		$this->assertNotNull( $answer );
		$this->assertSame( 'released_with_accessory', $answer['verdict'] );
		$joined = implode( "\n", $answer['conditions'] );
		$this->assertStringContainsString( 'B2-5.0', $joined );
		$this->assertStringContainsString( '115.2 V', $joined );
	}

	/**
	 * Every verdict the file states is one of the three, and every pair names
	 * its documents as our hosted URLs.
	 */
	public function test_the_file_states_known_verdicts_and_hosted_documents(): void {
		$verdicts = array();
		foreach ( Compatibility::pairs() as $pair ) {
			$verdicts[ $pair['verdict'] ] = true;
			foreach ( $pair['documents'] as $document ) {
				$this->assertStringStartsWith( 'https://de-linker.com/', (string) $document['url'] );
			}
		}
		$this->assertSame( array(), array_values( array_diff( array_keys( $verdicts ), Compatibility::VERDICTS ) ) );
		$this->assertSame( array( 'released', 'not_released', 'released_with_accessory' ), array_keys( $verdicts ) );
	}

	/**
	 * Two products decide through their pa_brand and pa_model terms, the way
	 * the feed names them.
	 */
	public function test_for_products_reads_the_brand_and_model_terms(): void {
		$this->mock_terms( 4107, 'pa_model', 'H2-10K-T3' );
		$this->mock_terms( 4107, 'pa_brand', 'SAJ' );
		$this->mock_terms( 2067, 'pa_model', 'B2-10.0-HV1' );
		$this->mock_terms( 2067, 'pa_brand', 'SAJ' );

		$answer = Compatibility::for_products( 4107, 2067 );

		$this->assertNotNull( $answer );
		$this->assertSame( 'released_with_accessory', $answer['verdict'] );
	}

	/**
	 * A product without a model term answers nothing.
	 */
	public function test_for_products_without_a_model_answers_nothing(): void {
		$this->mock_terms( 4107, 'pa_model', 'H2-10K-T3' );
		$this->mock_terms( 4107, 'pa_brand', 'SAJ' );
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
	 * Mocks the product's single term of a taxonomy.
	 *
	 * @param int    $id       Product ID.
	 * @param string $taxonomy Taxonomy.
	 * @param string $name     The term's name.
	 */
	private function mock_terms( int $id, string $taxonomy, string $name ): void {
		$term       = new \stdClass();
		$term->slug = strtolower( (string) preg_replace( '/[^a-z0-9]+/i', '-', $name ) );
		$term->name = $name;
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'args'   => array( $id, $taxonomy ),
				'return' => array( $term ),
			)
		);
	}
}

<?php
/**
 * Tests for the translation validator and the language rules.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\Validator;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Validator and Rules, with the plugin's own glossary and banned words.
 *
 * @covers \Linker\I18n\Translation\Validator
 * @covers \Linker\I18n\Translation\Rules
 */
final class ValidatorTest extends TestCase {

	/**
	 * The validator with data/glossary-de.json and data/banned-de.json.
	 *
	 * @var Validator
	 */
	private Validator $validator;

	/**
	 * Splits English into segments.
	 *
	 * @var Segmenter
	 */
	private Segmenter $segmenter;

	/**
	 * Sets up the validator.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->validator = new Validator( Rules::load( dirname( __DIR__, 4 ) . '/data' ) );
		$this->segmenter = new Segmenter( new HtmlTokenizer() );
	}

	/**
	 * English, a German answer, and what the validator says about it.
	 *
	 * @return array<string, array{string, string, list<string>}>
	 */
	public function provide_answers(): array {
		return array(
			'good'                     => array( '<p><strong>Rated AC power:</strong> 20.0 kW</p>', '<t1>AC-Nennleistung:</t1> 20,0 kW', array() ),
			'thousands either way'     => array( '<p>Rated power 29,999 W</p>', 'Nennleistung 29.999 W', array() ),
			'thousands with a space'   => array( '<p>Rated power 29,999 W</p>', 'Nennleistung 29 999 W', array() ),
			'empty'                    => array( '<p>Rated power</p>', '  ', array( 'empty translation' ) ),
			'placeholder lost'         => array( '<p><strong>Rated AC power:</strong> 10 kW</p>', 'AC-Nennleistung: 10 kW', array( 'placeholders changed' ) ),
			'placeholder doubled'      => array( '<p>The GW10K-ET</p>', 'Der <k1/> <k1/>', array( 'placeholders changed' ) ),
			'pair crossed'             => array( '<p><strong>A</strong> and <em>B</em></p>', '<t1>A</t3> und <t3>B</t1>', array( 'placeholders changed' ) ),
			'figure changed'           => array( '<p>Up to 10 kW</p>', 'Bis zu 12 kW', array( 'figures changed' ) ),
			'figure dropped'           => array( '<p>10 kW backup</p>', 'Notstrom', array( 'figures changed' ) ),
			'glossary missed'          => array( '<p>Download the datasheet</p>', 'Laden Sie das Dokument herunter', array( 'glossary: "datasheet" must be "Datenblatt"' ) ),
			'glossary plural'          => array( '<p>Hybrid inverters</p>', 'Hybridwechselrichter', array() ),
			'name changed'             => array( '<p>Contact Linker</p>', 'Kontakt zu Linkers', array() ),
			'name dropped'             => array( '<p>Ask GoodWe</p>', 'Fragen Sie den Hersteller', array( 'name changed: "GoodWe"' ) ),
			'banned cart'              => array( '<p>Add to cart</p>', 'In den Warenkorb legen', array( 'banned word: "Warenkorb"' ) ),
			'banned compound'          => array( '<p>Your cart page</p>', 'Ihre Warenkorbseite', array( 'banned word: "Warenkorb"' ) ),
			'informal'                 => array( '<p>You can order</p>', 'Du kannst bestellen', array( 'banned word: "du"' ) ),
			'du inside a word is fine' => array( '<p>Product</p>', 'Produkt', array() ),
		);
	}

	/**
	 * The validator's verdict.
	 *
	 * @dataProvider provide_answers
	 *
	 * @param string             $english  English HTML.
	 * @param string             $german   German answer for its first segment.
	 * @param array<int, string> $expected Problems.
	 */
	public function test_problems( string $english, string $german, array $expected ): void {
		$segment = $this->segmenter->html( $english )->segments[0];

		$this->assertSame( $expected, $this->validator->problems( $segment, $german ) );
	}

	/**
	 * A glossary term matches as a whole word, with a plural s, a space or a hyphen.
	 */
	public function test_glossary_matching(): void {
		$this->assertTrue( Rules::uses( 'peak shaving', 'Peak-shaving for C&I' ) );
		$this->assertTrue( Rules::uses( 'inverter', 'Two inverters' ) );
		$this->assertFalse( Rules::uses( 'inverter', 'microinverter' ) );
		$this->assertFalse( Rules::uses( 'product', 'production' ) );
	}

	/**
	 * Missing data files stop the plugin loudly instead of translating unchecked.
	 */
	public function test_missing_rules_are_an_error(): void {
		WP_Mock::passthruFunction( 'esc_html' );
		$this->expectException( \RuntimeException::class );

		Rules::load( __DIR__ );
	}
}

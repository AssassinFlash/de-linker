<?php
/**
 * Tests for linker/size-hint.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\SizeHint;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for SizeHint: the configurator URL, not a second engine.
 *
 * @covers \Linker\Commerce\Abilities\SizeHint
 */
final class SizeHintTest extends TestCase {

	/**
	 * Home URL and query arguments behave as WordPress does for these values.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => static fn ( string $path = '' ): string => 'https://de-linker.com' . $path,
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static function ( array $query, string $url ): string {
					return $url . '?' . http_build_query( $query );
				},
			)
		);
	}

	/**
	 * Pre-fills the Solution Configurator; does not call the engine.
	 */
	public function test_builds_the_configurator_url(): void {
		$result = ( new SizeHint() )->execute(
			array(
				'pv_kwp'          => 10,
				'annual_load_kwh' => 4000,
				'phase'           => 3,
				'backup'          => 'needed',
				'plz'             => '80538',
			)
		);

		$this->assertStringContainsString( '/solution-configurator/', $result['configurator_url'] );
		$this->assertStringContainsString( 'pv_kwp=10', $result['configurator_url'] );
		$this->assertStringContainsString( 'annual_kwh=4000', $result['configurator_url'] );
		$this->assertStringContainsString( 'phase=3', $result['configurator_url'] );
		$this->assertStringContainsString( 'plz=80538', $result['configurator_url'] );
		$this->assertStringContainsString( '10 kWp PV', $result['summary'] );
		$this->assertStringNotContainsString( 'lang', $result['configurator_url'] );
		$this->assertTrue( ( new SizeHint() )->can_execute() );
		$schema = ( new SizeHint() )->args()['output_schema'];
		$this->assertSame( array( 'summary', 'configurator_url' ), $schema['required'] );
	}

	/**
	 * An empty call, and a call that only carries the service language, both
	 * open the configurator with no query (#393). lang is not a stated field.
	 */
	public function test_empty_object_and_lang_are_accepted(): void {
		$schema = ( new SizeHint() )->args()['input_schema'];

		$this->assertSame( array(), $schema['default'] );
		$this->assertFalse( $schema['additionalProperties'] );
		$this->assertSame( array(), $schema['required'] ?? array() );
		$this->assertSame(
			array(
				'type' => 'string',
				'enum' => array( 'en', 'de' ),
			),
			$schema['properties']['lang']
		);

		$bare     = ( new SizeHint() )->execute( array() );
		$with_en  = ( new SizeHint() )->execute( array( 'lang' => 'en' ) );
		$with_de  = ( new SizeHint() )->execute( array( 'lang' => 'de' ) );
		$expected = array(
			'summary'          => 'Open the Solution Configurator.',
			'configurator_url' => 'https://de-linker.com/solution-configurator/',
		);
		$this->assertSame( $expected, $bare );
		$this->assertSame( $expected, $with_en );
		$this->assertSame( $expected, $with_de );

		$stated = ( new SizeHint() )->execute(
			array(
				'lang'   => 'en',
				'pv_kwp' => 12,
			)
		);
		$this->assertSame(
			'https://de-linker.com/solution-configurator/?pv_kwp=12',
			$stated['configurator_url']
		);
		$this->assertStringNotContainsString( 'lang=', $stated['configurator_url'] );
	}

	/**
	 * A German hint keeps the English path (#393).
	 *
	 * The execute() method drops lang. The URL for the matrix fields with lang=de
	 * is the same string as the English hint, and that string is
	 * /solution-configurator/, not /de/loesungskonfigurator/. A change that
	 * emits the German path, or that keeps lang in the query, contradicts
	 * the ruling. It needs a new ruling before it ships. Record:
	 * docs/acceptance/2026-10-21/458/.
	 */
	public function test_a_german_hint_drops_lang_and_keeps_the_english_path(): void {
		$stated  = array(
			'pv_kwp'          => 10,
			'annual_load_kwh' => 4500,
			'phase'           => 3,
			'backup'          => 'needed',
			'plz'             => '80538',
		);
		$english = ( new SizeHint() )->execute( $stated );
		$german  = ( new SizeHint() )->execute(
			array(
				'lang'            => 'de',
				'pv_kwp'          => 10,
				'annual_load_kwh' => 4500,
				'phase'           => 3,
				'backup'          => 'needed',
				'plz'             => '80538',
			)
		);
		$path    = 'https://de-linker.com/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538';

		$this->assertSame( $english, $german );
		$this->assertSame( $path, $german['configurator_url'] );
		$this->assertStringNotContainsString( 'lang', $german['configurator_url'] );
		$this->assertStringNotContainsString( '/de/', $german['configurator_url'] );
		$this->assertSame( $path, $english['configurator_url'] );
	}

	/**
	 * The query mapping genie looks up (#365 round 2).
	 *
	 * The file services/genie/tests/fixtures/size-hint-urls.json is produced
	 * by this class (home_url https://de-linker.com, add_query_arg as
	 * http_build_query, the doubles above). The Python tests read that file
	 * and do not reimplement (string)(float), the annual_kwh rename, or the
	 * whitelist.
	 */
	public function test_the_committed_fixture_is_the_query_mapping(): void {
		$path    = dirname( __DIR__, 6 ) . '/services/genie/tests/fixtures/size-hint-urls.json';
		$fixture = json_decode( (string) file_get_contents( $path ), true );
		$this->assertIsArray( $fixture );
		$this->assertNotEmpty( $fixture['cases'] );
		foreach ( $fixture['cases'] as $case ) {
			$result = ( new SizeHint() )->execute( $case['input'] );
			$this->assertSame( $case['configurator_url'], $result['configurator_url'] );
		}
	}
}

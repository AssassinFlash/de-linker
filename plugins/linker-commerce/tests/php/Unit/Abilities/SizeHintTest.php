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
		$this->assertTrue( ( new SizeHint() )->can_execute() );
		$schema = ( new SizeHint() )->args()['output_schema'];
		$this->assertSame( array( 'summary', 'configurator_url' ), $schema['required'] );
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

<?php
/**
 * Retired design writes retain a localized, read-only recovery destination.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Planning;

use Linker\Commerce\Planning\LegacyRoutes;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Neither legacy save nor draft requests can create or recalculate a solution.
 *
 * @covers \Linker\Commerce\Planning\LegacyRoutes
 */
final class LegacyRoutesTest extends TestCase {

	/** Only route registration and native page lookup are available to the callback. */
	public function test_retired_writes_return_the_native_project_entry(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'solution-configurator' )->andReturn( new WP_Post( (object) array( 'ID' => 80 ) ) );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'de' );
		WP_Mock::userFunction( 'pll_get_post' )->with( 80, 'de' )->andReturn( 800 );
		WP_Mock::userFunction( 'get_permalink' )->with( 800 )->andReturn( 'https://example.test/de/loesungskonfigurator/' );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . http_build_query( $query ) ) );
		$registered = array();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times'  => 2,
				'return' => static function ( string $route_namespace, string $path, array $args ) use ( &$registered ): bool {
					$registered[ $path ] = $args;
					return true;
				},
			)
		);
		( new LegacyRoutes() )->register();
		$this->assertSame( array( '/solutions', '/solutions/draft' ), array_keys( $registered ) );
		$result = ( $registered['/solutions']['callback'] )();
		$this->assertSame( 'linker_planner_required', $result->get_error_code() );
		$this->assertSame( 410, $result->get_error_data()['status'] );
		$this->assertSame( 'https://example.test/de/loesungskonfigurator/', $result->get_error_data()['configurator_url'] );
		$this->assertSame( 'https://example.test/de/loesungskonfigurator/?saved_solution=45', LegacyRoutes::url( 45 ) );
	}
}

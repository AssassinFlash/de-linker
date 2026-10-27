<?php
/**
 * Stale public calculator clients cannot reach an upstream service.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Configurator\EngineProxy;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Retired endpoints are cheap responses, without calculation or PDF generation.
 *
 * @covers \Linker\Tools\Configurator\EngineProxy
 */
final class EngineProxyTest extends TestCase {

	/** No HTTP, filesystem, stock or cart double is installed: none may be called. */
	public function test_old_proxy_returns_retirement_without_upstream_work(): void {
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => null ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn ( string $path = '' ): string => 'https://example.test' . $path ) );
		$result = EngineProxy::forward();
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_planner_required', $result->get_error_code() );
		$this->assertSame( 410, $result->get_error_data()['status'] );
	}
}

<?php
/**
 * Tests for the site search's scope.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\SearchScope;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;
use WP_Query;

/**
 * Tests for SearchScope: a main search that names no post type is narrowed to
 * blog posts, an explicit request keeps control (ticket #68, live recheck
 * families 17 and 23).
 *
 * @covers \Linker\Commerce\Products\SearchScope
 */
final class SearchScopeTest extends TestCase {


	/**
	 * What the last query was set to, when the scope set its post type.
	 *
	 * @var mixed
	 */
	private mixed $scoped = null;

	/**
	 * The scope listens on pre_get_posts.
	 */
	public function test_registers_the_query_filter(): void {
		$scope = new SearchScope();
		WP_Mock::expectActionAdded( 'pre_get_posts', array( $scope, 'scope' ) );
		$scope->register();
		$this->assertConditionsMet();
	}

	/**
	 * An implicit search of the main query becomes blog posts; an explicit
	 * post type is left alone. Products stay out: the results page is the
	 * blog template (2026-10-14 live recheck, families 17 and 23).
	 */
	public function test_implicit_search_is_scoped(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		$scope = new SearchScope();

		$scope->scope( $this->query( null ) );
		$this->assertSame( array( 'post' ), $this->scoped, 'No post type named: the search is blog posts only.' );

		$this->scoped = null;
		$scope->scope( $this->query( '' ) );
		$this->assertSame( array( 'post' ), $this->scoped, 'An empty post type is the implicit case.' );

		$scope->scope( $this->query( 'any' ) );
		$this->assertSame( array( 'post' ), $this->scoped, '"any" is the implicit case.' );

		$scope->scope( $this->query( array() ) );
		$this->assertSame( array( 'post' ), $this->scoped, 'An empty post-type list is the implicit case.' );

		$scope->scope( $this->query( array( 'any' ) ) );
		$this->assertSame( array( 'post' ), $this->scoped, 'A list that names "any" is the implicit case.' );

		$this->scoped = null;
		$scope->scope( $this->query( array( 'product' ) ) );
		$this->assertNull( $this->scoped, 'A request that names its post type keeps control.' );

		$scope->scope( $this->query( array( 'post', 'page' ) ) );
		$this->assertNull( $this->scoped, 'A list that names its post types keeps control.' );

		$scope->scope( $this->query( 'product' ) );
		$this->assertNull( $this->scoped, 'An explicit product search is not rewritten to posts.' );
	}

	/**
	 * A query that is not the main search stays untouched.
	 */
	public function test_other_queries_stay_untouched(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		$scope = new SearchScope();

		$scope->scope( $this->query( null, main: true, search: false ) );
		$this->assertNull( $this->scoped, 'A query that is not a search is not scoped.' );

		$scope->scope( $this->query( null, main: false, search: true ) );
		$this->assertNull( $this->scoped, 'A secondary search is not scoped.' );
	}

	/**
	 * A query mock that names a post type or none; what set() narrowed it to
	 * lands in $this->scoped.
	 *
	 * @param mixed $post_type What the query says.
	 * @param bool  $main      Whether it is the main query.
	 * @param bool  $search    Whether it is a search.
	 */
	private function query( mixed $post_type, bool $main = true, bool $search = true ): WP_Query {
		$this->scoped = null;
		$query        = Mockery::mock( WP_Query::class );
		$query->allows( 'is_main_query' )->andReturn( $main );
		$query->allows( 'is_search' )->andReturn( $search );
		$query->allows( 'get' )->with( 'post_type' )->andReturn( $post_type );
		$query->allows( 'set' )->andReturnUsing(
			function ( string $key, mixed $value ): void {
				if ( 'post_type' === $key ) {
					$this->scoped = $value;
				}
			}
		);
		return $query;
	}
}

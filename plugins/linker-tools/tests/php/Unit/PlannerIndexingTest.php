<?php
/**
 * Private workspace URLs and the public tool keep distinct native SEO policies.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Indexing;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Indexing policy never reads project facts or grants project access.
 *
 * @covers \Linker\Tools\Planner\Indexing
 */
final class PlannerIndexingTest extends TestCase {

	/** Native LC page, language twin, carried input and shortcode boundaries. */
	public function test_private_queries_do_not_change_the_public_tool_or_other_pages(): void {
		$post = new \WP_Post( (object) array( 'ID' => 6693 ) );
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_page', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => static function () use ( &$post ): \WP_Post {
					return $post;
				},
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'solution-configurator' ),
				'return' => new \WP_Post( (object) array( 'ID' => 3302 ) ),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post_translations',
			array(
				'return' => array(
					'en' => 3302,
					'de' => 6693,
				),
			)
		);
		WP_Mock::userFunction( 'has_shortcode', array( 'return' => static fn( string $content, string $name ): bool => str_contains( $content, '[' . $name . ']' ) ) );
		WP_Mock::userFunction( 'wp_get_nocache_headers', array( 'return' => array( 'Last-Modified' => false ) ) );
		$before = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore test-owned request names; no form data is consumed.
		try {
			$policy = new Indexing();
			$_GET   = array( 'project' => 'private-fixture' );
			$this->assertSame( 'noindex, nofollow, nosnippet', $policy->headers( array() )['X-Robots-Tag'] );
			$this->assertSame( 'existing-site-policy', $policy->headers( array( 'Referrer-Policy' => 'existing-site-policy' ) )['Referrer-Policy'] );
			$this->assertFalse( $policy->headers( array( 'Last-Modified' => 'earlier' ) )['Last-Modified'] );
			$this->assertSame(
				array(
					'noindex'   => true,
					'nofollow'  => true,
					'nosnippet' => true,
				),
				$policy->robots(
					array(
						'index'  => true,
						'follow' => true,
					)
				)
			);
			$this->assertSame( '1', $policy->noindex( '' ) );
			$this->assertSame( array( 'noindex', 'nofollow', 'nosnippet' ), $policy->seopress_robots( array( 'index', 'follow', 'noindex' ) ) );
			$this->assertTrue( $policy->canonical( false ) );
			$this->assertSame( array(), $policy->hreflangs( array( 'en' => 'public' ) ) );

			$_GET = array(
				'step'       => 'roof',
				'utm_source' => 'fixture',
			);
			$this->assertSame( array( 'Cache-Control' => 'existing' ), $policy->headers( array( 'Cache-Control' => 'existing' ) ) );
			$this->assertSame( array( 'index' => true ), $policy->robots( array( 'index' => true ) ) );
			$this->assertSame( '', $policy->noindex( '' ) );
			$this->assertSame( array( 'en' => 'public' ), $policy->hreflangs( array( 'en' => 'public' ) ) );

			$_GET = array( 'run' => array() );
			$this->assertSame( '1', $policy->noindex( '' ), 'Invalid query values must not escape private indexing.' );
			$_GET = array( 'plz' => '50667' );
			$this->assertSame( '1', $policy->noindex( '' ), 'Carried site inputs are private too.' );

			$post = new \WP_Post( (object) array( 'ID' => 777 ) );
			$this->assertSame( array(), $policy->headers( array() ), 'An unrelated page keeps its policy.' );
			$post->post_content = '[linker_planner]';
			$this->assertSame( '1', $policy->noindex( '' ), 'Independent native mounts share the policy.' );
		} finally {
			$_GET = $before;
		}
	}
}

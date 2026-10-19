<?php
/**
 * Tests for dropping Genie's cached page when the page is saved (#405).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\PageCache;
use Linker\Tools\Genie\Proxy;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * Tests for PageCache, with WordPress functions mocked.
 *
 * @covers \Linker\Tools\Genie\PageCache
 */
final class PageCacheTest extends TestCase {

	/**
	 * The calls the fetch double received: URL, body, headers.
	 *
	 * @var list<array{0: string, 1: array<string, mixed>, 2: array<string, string>}>
	 */
	private array $calls = array();

	/**
	 * Permalinks by post or term ID, changed by a test when a slug changes.
	 *
	 * @var array<int, string>
	 */
	private array $links = array();

	/**
	 * Post translations by source ID. Empty means the post is its own twin.
	 *
	 * @var array<int, array<string, int>>
	 */
	private array $post_translations = array();

	/**
	 * Post IDs that are revisions.
	 *
	 * @var list<int>
	 */
	private array $revisions = array();

	/**
	 * The Genie service address; '' when the site has none.
	 *
	 * @var string
	 */
	private string $service = 'http://127.0.0.1:8890/';

	/**
	 * What `did_action( 'shutdown' )` answers. 1 means the save is already on shutdown.
	 *
	 * @var int
	 */
	private int $on_shutdown = 0;

	/**
	 * Sets up an empty call list.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->calls             = array();
		$this->links             = array();
		$this->post_translations = array();
		$this->revisions         = array();
		$this->service           = 'http://127.0.0.1:8890/';
		$this->on_shutdown       = 0;
	}

	/**
	 * A published product and its German twin are dropped together, on shutdown.
	 */
	public function test_a_published_post_and_its_twin_are_dropped_on_shutdown(): void {
		$this->links             = array(
			4107 => 'http://site.test/product/old-name/',
			8200 => 'http://site.test/de/produkt/old-name/',
		);
		$this->post_translations = array(
			4107 => array(
				'en' => 4107,
				'de' => 8200,
			),
		);
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->before_post_saved( 4107 );
		$this->links[4107] = 'http://site.test/product/new-name/';
		$cache->post_saved( 4107, $this->post( 4107 ), true, $this->post( 4107 ) );
		$this->assertSame( array(), $this->calls, 'the save itself does not wait on the service' );
		$cache->send();

		$this->assertSame(
			array(
				array(
					'http://127.0.0.1:8890/pages/invalidate',
					array(
						'paths' => array(
							'/product/old-name/',
							'/de/produkt/old-name/',
							'/product/new-name/',
						),
					),
					array( Proxy::TOKEN_HEADER => 'token' ),
				),
			),
			$this->calls
		);
		$this->assertConditionsMet();
	}

	/**
	 * A revision and a draft are not pages an anonymous visitor was shown.
	 */
	public function test_a_revision_or_a_draft_is_not_dropped(): void {
		$this->revisions = array( 9 );
		$this->wordPress();
		$cache = $this->cache();

		$cache->post_saved( 9, $this->post( 9 ), true, null );
		$cache->post_saved( 10, $this->post( 10, 'draft' ), true, null );
		$cache->send();

		$this->assertSame( array(), $this->calls );
		$this->assertConditionsMet();
	}

	/**
	 * Unpublishing drops the page that was public, so the old text does not linger.
	 */
	public function test_unpublishing_drops_the_page_that_was_public(): void {
		$this->links = array( 551 => 'http://site.test/blog/post/' );
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->post_saved( 551, $this->post( 551, 'draft', 'post' ), true, $this->post( 551, 'publish', 'post' ) );
		$cache->send();

		$this->assertSame( array( '/blog/post/' ), $this->calls[0][1]['paths'] );
		$this->assertConditionsMet();
	}

	/**
	 * A category and its German twin are dropped. A menu, which is not a public archive, is not.
	 */
	public function test_a_viewable_term_and_its_twin_are_dropped(): void {
		$this->links = array(
			44 => 'http://site.test/product-category/inverters/',
			45 => 'http://site.test/de/produktkategorie/wechselrichter/',
		);
		$this->wordPress();
		WP_Mock::userFunction( 'is_taxonomy_viewable' )->andReturnUsing(
			static fn( string $taxonomy ): bool => 'product_cat' === $taxonomy
		);
		WP_Mock::userFunction( 'pll_get_term_translations' )->andReturn(
			array(
				'en' => 44,
				'de' => 45,
			)
		);
		WP_Mock::userFunction( 'get_term_link' )->andReturnUsing(
			function ( int $id, string $taxonomy ) {
				unset( $taxonomy );
				return $this->links[ $id ];
			}
		);
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->term_saved( 44, 70, 'product_cat' );
		$cache->term_saved( 3, 1, 'nav_menu' );
		$cache->send();

		$this->assertSame(
			array( '/product-category/inverters/', '/de/produktkategorie/wechselrichter/' ),
			$this->calls[0][1]['paths']
		);
		$this->assertConditionsMet();
	}

	/**
	 * The translator's write happens on shutdown of its own request: the drop
	 * is sent then, without waiting for another shutdown.
	 */
	public function test_a_save_during_shutdown_is_sent_immediately(): void {
		$this->links       = array( 551 => 'http://site.test/blog/post/' );
		$this->on_shutdown = 1;
		$this->wordPress();
		$cache = $this->cache();

		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );

		$this->assertSame( array( '/blog/post/' ), $this->calls[0][1]['paths'] );
		$this->assertConditionsMet();
	}

	/**
	 * No service address: nothing is called and the save is not an error.
	 * No token: nothing is called either. A refused call is not fatal.
	 */
	public function test_a_missing_service_does_not_fail_the_save(): void {
		$this->links   = array( 551 => 'http://site.test/blog/post/' );
		$this->service = '';
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );
		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );
		$cache->send();
		$this->assertSame( array(), $this->calls );
		$this->assertConditionsMet();
	}

	/**
	 * A site with no shared token does not call the service.
	 */
	public function test_without_a_token_nothing_is_called(): void {
		$this->links = array( 551 => 'http://site.test/blog/post/' );
		$this->wordPress();
		$cache = new PageCache( $this->fetch(), '' );
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );
		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );
		$cache->send();
		$this->assertSame( array(), $this->calls );
		$this->assertConditionsMet();
	}

	/**
	 * The service refusing the call does not fail the save.
	 */
	public function test_a_refused_call_does_not_fail_the_save(): void {
		$this->links = array( 551 => 'http://site.test/blog/post/' );
		$this->wordPress();
		$cache = $this->cache(
			function ( string $url, array $body, array $headers ): int {
				$this->calls[] = array( $url, $body, $headers );
				return 503;
			}
		);
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );
		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );
		$cache->send();
		$this->assertCount( 1, $this->calls );
		$this->assertConditionsMet();
	}

	/**
	 * The WordPress functions every save touches, with harmless defaults.
	 */
	private function wordPress(): void {
		WP_Mock::userFunction( 'wp_is_post_revision' )->andReturnUsing(
			fn( int $id ): bool => in_array( $id, $this->revisions, true )
		);
		WP_Mock::userFunction( 'wp_is_post_autosave' )->andReturn( false );
		WP_Mock::userFunction( 'is_post_type_viewable' )->andReturn( true );
		WP_Mock::userFunction( 'get_post' )->andReturnUsing(
			fn( int $id ): WP_Post => $this->post( $id )
		);
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing(
			fn( int $id ): string => $this->links[ $id ] ?? "http://site.test/p/{$id}/"
		);
		WP_Mock::userFunction( 'pll_get_post_translations' )->andReturnUsing(
			fn( int $id ): array => $this->post_translations[ $id ] ?? array( 'en' => $id )
		);
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing(
			static function ( string $url ): array|false {
				$parsed = parse_url( $url ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- test double of wp_parse_url.
				return false === $parsed ? false : $parsed;
			}
		);
		WP_Mock::userFunction( 'did_action' )->andReturnUsing(
			fn( string $hook ): int => 'shutdown' === $hook ? $this->on_shutdown : 0
		);
		WP_Mock::userFunction( 'get_option' )->andReturnUsing(
			function ( string $option, mixed $fallback = '' ): string {
				unset( $option, $fallback );
				return $this->service;
			}
		);
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing(
			static fn( mixed $thing ): bool => $thing instanceof \WP_Error
		);
	}

	/**
	 * A page cache that records its HTTP call and answers 200.
	 *
	 * @param callable( string, array<string, mixed>, array<string, string> ): int|null $fetch Replacement fetch.
	 */
	private function cache( ?callable $fetch = null ): PageCache {
		return new PageCache( $fetch ?? $this->fetch(), 'token' );
	}

	/**
	 * Records the call and answers 200.
	 *
	 * @return callable( string, array<string, mixed>, array<string, string> ): int
	 */
	private function fetch(): callable {
		return function ( string $url, array $body, array $headers ): int {
			$this->calls[] = array( $url, $body, $headers );
			return 200;
		};
	}

	/**
	 * A post as the save hooks receive it.
	 *
	 * @param int    $id     Post ID.
	 * @param string $status Post status.
	 * @param string $type   Post type.
	 */
	private function post( int $id, string $status = 'publish', string $type = 'product' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'          => $id,
				'post_type'   => $type,
				'post_status' => $status,
				'post_name'   => 'name',
			)
		);
	}
}

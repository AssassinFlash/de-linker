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
	 * Post type by ID. Unset IDs are products.
	 *
	 * @var array<int, string>
	 */
	private array $types = array();

	/**
	 * `page_for_posts`. 0 means the site has no posts page.
	 *
	 * @var int
	 */
	private int $posts_page = 0;

	/**
	 * `show_on_front`: `page` or `posts`.
	 *
	 * @var string
	 */
	private string $show_on_front = 'page';

	/**
	 * WooCommerce shop page ID. 0 means there is no shop page.
	 *
	 * @var int
	 */
	private int $shop_page = 0;

	/**
	 * Term IDs by post ID and taxonomy.
	 *
	 * @var array<int, array<string, list<int>>>
	 */
	private array $object_terms = array();

	/**
	 * Term translations by source ID.
	 *
	 * @var array<int, array<string, int>>
	 */
	private array $term_translations = array();

	/**
	 * Term IDs by term_taxonomy_id. The two are not the same number.
	 *
	 * @var array<int, int>
	 */
	private array $term_taxonomy = array();

	/**
	 * Post type archive links. Unset types have none.
	 *
	 * @var array<string, string>
	 */
	private array $archives = array();

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
		$this->types             = array();
		$this->posts_page        = 0;
		$this->show_on_front     = 'page';
		$this->shop_page         = 0;
		$this->object_terms      = array();
		$this->term_translations = array();
		$this->term_taxonomy     = array();
		$this->archives          = array();
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
		$this->links             = array(
			44 => 'http://site.test/product-category/inverters/',
			45 => 'http://site.test/de/produktkategorie/wechselrichter/',
		);
		$this->term_translations = array(
			44 => array(
				'en' => 44,
				'de' => 45,
			),
		);
		$this->wordPress();
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
	 * A product save drops the shop and the categories it leaves and joins.
	 */
	public function test_a_product_save_drops_the_shop_and_both_categories(): void {
		$this->links             = array(
			4107 => 'http://site.test/product/old-name/',
			8200 => 'http://site.test/de/produkt/old-name/',
			90   => 'http://site.test/shop/',
			91   => 'http://site.test/de/shop/',
			44   => 'http://site.test/product-category/inverters/',
			45   => 'http://site.test/de/produktkategorie/wechselrichter/',
			46   => 'http://site.test/product-category/batteries/',
		);
		$this->post_translations = array(
			4107 => array(
				'en' => 4107,
				'de' => 8200,
			),
			90   => array(
				'en' => 90,
				'de' => 91,
			),
		);
		$this->types             = array(
			4107 => 'product',
			8200 => 'product',
		);
		$this->shop_page         = 90;
		$this->object_terms      = array(
			4107 => array(
				'product_cat' => array( 44 ),
			),
		);
		$this->term_translations = array(
			44 => array(
				'en' => 44,
				'de' => 45,
			),
		);
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->before_post_saved( 4107 );
		$this->links[4107]                       = 'http://site.test/product/new-name/';
		$this->object_terms[4107]['product_cat'] = array( 46 );
		$cache->post_saved( 4107, $this->post( 4107 ), true, $this->post( 4107 ) );
		$cache->send();

		$this->assertSame(
			array(
				'/product/old-name/',
				'/shop/',
				'/de/shop/',
				'/product-category/inverters/',
				'/de/produktkategorie/wechselrichter/',
				'/de/produkt/old-name/',
				'/product/new-name/',
				'/product-category/batteries/',
			),
			$this->calls[0][1]['paths']
		);
		foreach ( $this->calls[0][1]['paths'] as $path ) {
			$this->assertStringNotContainsString( '?', $path );
		}
		$this->assertConditionsMet();
	}

	/**
	 * A category-only save never calls wp_update_post. The new archive is already
	 * assigned; the replaced archive arrives only as a previous term_taxonomy_id.
	 *
	 * `$terms` is the caller's slug list. `$tt_ids` are strings, as WooCommerce's
	 * `term_exists()` values are. `$old_tt_ids` are integers, as `fields => tt_ids` is.
	 */
	public function test_a_category_only_save_drops_the_old_and_new_archives(): void {
		$this->category_move_fixture();
		$this->object_terms[4107]['product_cat'] = array( 46 );
		$this->wordPress();
		$this->mock_term_taxonomy_lookup();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->object_terms_set( 4107, array( 'batteries' ), array( '702' ), 'product_cat', false, array( 700 ) );
		$cache->send();

		$this->assertSame(
			array(
				'/product/inverter/',
				'/shop/',
				'/de/shop/',
				'/product-category/batteries/',
				'/de/produkt/inverter/',
				'/product-category/inverters/',
				'/de/produktkategorie/wechselrichter/',
			),
			$this->calls[0][1]['paths']
		);
		$this->assertConditionsMet();
	}

	/**
	 * The block editor updates the post, then assigns terms. The after-save hook
	 * still sees the old category; the new archive is named only by the assignment.
	 */
	public function test_a_block_editor_save_drops_both_category_archives(): void {
		$this->category_move_fixture();
		$this->object_terms[4107]['product_cat'] = array( 44 );
		$this->wordPress();
		$this->mock_term_taxonomy_lookup();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->before_post_saved( 4107 );
		$cache->post_saved( 4107, $this->post( 4107 ), true, $this->post( 4107 ) );
		$this->object_terms[4107]['product_cat'] = array( 46 );
		$cache->object_terms_set( 4107, array( 46 ), array( '702' ), 'product_cat', false, array( 700 ) );
		$cache->send();

		$this->assertSame(
			array(
				'/product/inverter/',
				'/shop/',
				'/de/shop/',
				'/product-category/inverters/',
				'/de/produktkategorie/wechselrichter/',
				'/de/produkt/inverter/',
				'/product-category/batteries/',
			),
			$this->calls[0][1]['paths']
		);
		$this->assertConditionsMet();
	}

	/**
	 * A stale relationship cache still lists the old category. The requested
	 * term_taxonomy_id is what names the new archive.
	 */
	public function test_requested_term_taxonomy_ids_name_the_new_archive_when_the_cache_is_stale(): void {
		$this->category_move_fixture();
		$this->object_terms[4107]['product_cat'] = array( 44 );
		$this->wordPress();
		$this->mock_term_taxonomy_lookup();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->object_terms_set( 4107, array( 'batteries' ), array( '702' ), 'product_cat', false, array( 700 ) );
		$cache->send();

		$this->assertContains( '/product-category/batteries/', $this->calls[0][1]['paths'] );
		$this->assertContains( '/product-category/inverters/', $this->calls[0][1]['paths'] );
		$this->assertConditionsMet();
	}

	/**
	 * Permalinks, shop and twins for a product moving from inverters to batteries.
	 *
	 * Term 44 is term_taxonomy_id 700. Term 46 is term_taxonomy_id 702. A handler
	 * that treats the action's ids as term ids looks up the wrong archives.
	 */
	private function category_move_fixture(): void {
		$this->links             = array(
			4107 => 'http://site.test/product/inverter/',
			8200 => 'http://site.test/de/produkt/inverter/',
			90   => 'http://site.test/shop/',
			91   => 'http://site.test/de/shop/',
			44   => 'http://site.test/product-category/inverters/',
			45   => 'http://site.test/de/produktkategorie/wechselrichter/',
			46   => 'http://site.test/product-category/batteries/',
		);
		$this->post_translations = array(
			4107 => array(
				'en' => 4107,
				'de' => 8200,
			),
			90   => array(
				'en' => 90,
				'de' => 91,
			),
		);
		$this->types             = array(
			4107 => 'product',
			8200 => 'product',
		);
		$this->shop_page         = 90;
		$this->term_translations = array(
			44 => array(
				'en' => 44,
				'de' => 45,
			),
		);
		$this->term_taxonomy     = array(
			700 => 44,
			702 => 46,
		);
	}

	/**
	 * `get_term_by( 'term_taxonomy_id' )` for the category-move fixture.
	 */
	private function mock_term_taxonomy_lookup(): void {
		WP_Mock::userFunction( 'get_term_by' )->andReturnUsing(
			function ( string $field, mixed $value, string $taxonomy = '' ): \WP_Term|false {
				unset( $taxonomy );
				if ( 'term_taxonomy_id' !== $field ) {
					return false;
				}
				$term_id = $this->term_taxonomy[ (int) $value ] ?? 0;
				if ( $term_id <= 0 ) {
					return false;
				}
				return new \WP_Term(
					(object) array(
						'term_id'  => $term_id,
						'taxonomy' => 'product_cat',
					)
				);
			}
		);
	}

	/**
	 * A blog post drops the posts page, its category and its tag, with twins.
	 */
	public function test_a_blog_post_drops_the_index_and_its_terms(): void {
		$this->links             = array(
			551 => 'http://site.test/blog/post/',
			552 => 'http://site.test/de/blog/beitrag/',
			12  => 'http://site.test/blog/',
			13  => 'http://site.test/de/blog/',
			7   => 'http://site.test/category/news/',
			8   => 'http://site.test/de/kategorie/news/',
			9   => 'http://site.test/tag/hybrid/',
		);
		$this->types             = array(
			551 => 'post',
			552 => 'post',
		);
		$this->post_translations = array(
			551 => array(
				'en' => 551,
				'de' => 552,
			),
			12  => array(
				'en' => 12,
				'de' => 13,
			),
		);
		$this->posts_page        = 12;
		$this->object_terms      = array(
			551 => array(
				'category' => array( 7 ),
				'post_tag' => array( 9 ),
			),
		);
		$this->term_translations = array(
			7 => array(
				'en' => 7,
				'de' => 8,
			),
		);
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );
		$cache->send();

		$this->assertSame(
			array(
				'/blog/post/',
				'/blog/',
				'/de/blog/',
				'/category/news/',
				'/de/kategorie/news/',
				'/tag/hybrid/',
				'/de/blog/beitrag/',
			),
			$this->calls[0][1]['paths']
		);
		$this->assertConditionsMet();
	}

	/**
	 * Saving a page does not drop the shop or the blog index.
	 */
	public function test_a_page_save_does_not_drop_the_shop_or_the_blog_index(): void {
		$this->links             = array(
			3  => 'http://site.test/about/',
			12 => 'http://site.test/blog/',
			90 => 'http://site.test/shop/',
		);
		$this->types             = array( 3 => 'page' );
		$this->posts_page        = 12;
		$this->shop_page         = 90;
		$this->post_translations = array(
			3 => array( 'en' => 3 ),
		);
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->post_saved( 3, $this->post( 3, 'publish', 'page' ), true, null );
		$cache->send();

		$this->assertSame( array( '/about/' ), $this->calls[0][1]['paths'] );
		$this->assertConditionsMet();
	}

	/**
	 * When the front page is the post list, each language's home is the blog index.
	 */
	public function test_a_post_on_a_posts_front_drops_each_language_home(): void {
		$this->links         = array( 551 => 'http://site.test/hello/' );
		$this->types         = array( 551 => 'post' );
		$this->show_on_front = 'posts';
		$this->wordPress();
		WP_Mock::userFunction( 'pll_languages_list' )->andReturn( array( 'en', 'de' ) );
		WP_Mock::userFunction( 'pll_home_url' )->andReturnUsing(
			static fn( string $language ): string => 'de' === $language ? 'http://site.test/de/' : 'http://site.test/'
		);
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->post_saved( 551, $this->post( 551, 'publish', 'post' ), true, null );
		$cache->send();

		$this->assertSame( array( '/hello/', '/', '/de/' ), $this->calls[0][1]['paths'] );
		$this->assertConditionsMet();
	}

	/**
	 * More paths than the cache holds go out as two requests.
	 */
	public function test_more_paths_than_the_cache_holds_go_in_two_requests(): void {
		$map = array();
		for ( $id = 1; $id <= 257; $id++ ) {
			$this->links[ $id ] = "http://site.test/page/{$id}/";
			$this->types[ $id ] = 'page';
			$map[ 'l' . $id ]   = $id;
		}
		$this->post_translations = array( 1 => $map );
		$this->wordPress();
		$cache = $this->cache();
		WP_Mock::expectActionAdded( 'shutdown', array( $cache, 'send' ) );

		$cache->post_saved( 1, $this->post( 1, 'publish', 'page' ), true, null );
		$cache->send();

		$this->assertCount( 2, $this->calls );
		$this->assertCount( PageCache::MAX_PATHS, $this->calls[0][1]['paths'] );
		$this->assertCount( 1, $this->calls[1][1]['paths'] );
		$this->assertSame( '/page/1/', $this->calls[0][1]['paths'][0] );
		$this->assertSame( '/page/257/', $this->calls[1][1]['paths'][0] );
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
			fn( int $id ): WP_Post => $this->post( $id, 'publish', $this->types[ $id ] ?? 'product' )
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
			function ( string $option, mixed $fallback = '' ): mixed {
				if ( Proxy::OPTION === $option ) {
					return $this->service;
				}
				if ( 'page_for_posts' === $option ) {
					return $this->posts_page;
				}
				if ( 'show_on_front' === $option ) {
					return $this->show_on_front;
				}
				return $fallback;
			}
		);
		WP_Mock::userFunction( 'is_taxonomy_viewable' )->andReturnUsing(
			static fn( string $taxonomy ): bool => in_array( $taxonomy, array( 'category', 'post_tag', 'product_cat' ), true )
		);
		WP_Mock::userFunction( 'taxonomy_exists' )->andReturnUsing(
			static fn( string $taxonomy ): bool => in_array( $taxonomy, array( 'category', 'post_tag', 'product_cat' ), true )
		);
		WP_Mock::userFunction( 'pll_get_term_translations' )->andReturnUsing(
			fn( int $id ): array => $this->term_translations[ $id ] ?? array( 'en' => $id )
		);
		WP_Mock::userFunction( 'get_term_link' )->andReturnUsing(
			function ( int $id, string $taxonomy ): string {
				unset( $taxonomy );
				return $this->links[ $id ] ?? "http://site.test/term/{$id}/";
			}
		);
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturnUsing(
			function ( int $id, string $taxonomy, array $args = array() ): array {
				unset( $args );
				return $this->object_terms[ $id ][ $taxonomy ] ?? array();
			}
		);
		WP_Mock::userFunction( 'wc_get_page_id' )->andReturnUsing(
			fn( string $page ): int => 'shop' === $page ? $this->shop_page : 0
		);
		WP_Mock::userFunction( 'get_post_type_archive_link' )->andReturnUsing(
			fn( string $type ): string|false => $this->archives[ $type ] ?? false
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

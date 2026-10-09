<?php
/**
 * The German URLs of the fixture, against the live site's.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions -- these tests run outside WordPress.

/**
 * Every German page, post, product and product category of the fixture
 * answers at the live site's German URL, in German, with Polylang's hreflang
 * pair and a canonical of its own; English segments under /de/ are 404.
 *
 * @coversNothing
 */
final class UrlsTest extends SiteTestCase {

	/**
	 * The local URLs and states, read once.
	 *
	 * @var array<string, array{de: string, en: string, status: string, note: string}>
	 */
	private static array $local = array();

	/**
	 * The fixture objects: kind, live ID, the live German and English URLs,
	 * the German title, the live German h1 when the fixture holds the German
	 * body it comes from, and whether the URL is an archive (a page of posts
	 * or products), where WordPress itself writes no canonical link.
	 *
	 * @return list<array{kind: string, live_id: int, de_url: string, en_url: string, title: string, h1: string|null, archive: bool}>
	 */
	private static function fixture(): array {
		$read     = static function ( string $name ): array {
			$data = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/live/' . $name ), true );
			return is_array( $data ) ? $data : array();
		};
		$site     = $read( 'site.json' );
		$archives = array( (int) $site['page_for_posts'], (int) $site['woocommerce_shop_page_id'] );
		$objects  = array();
		foreach ( array( 'pages.json', 'posts.json' ) as $file ) {
			foreach ( $read( $file ) as $post ) {
				$objects[] = array(
					'kind'    => (string) $post['type'],
					'live_id' => (int) $post['id'],
					'de_url'  => (string) $post['live']['de_url'],
					'en_url'  => (string) $post['live']['en_url'],
					'title'   => (string) $post['de']['title'],
					'h1'      => null === $post['de']['content_rendered'] ? null : (string) $post['live']['de']['h1'],
					'archive' => 'page' === $post['type'] && in_array( (int) $post['id'], $archives, true ),
				);
			}
		}
		foreach ( $read( 'products.json' ) as $product ) {
			$objects[] = array(
				'kind'    => 'product',
				'live_id' => (int) $product['id'],
				'de_url'  => (string) $product['live']['de_url'],
				'en_url'  => (string) $product['live']['en_url'],
				'title'   => (string) $product['meta']['_linker_de_title'],
				'h1'      => null,
				'archive' => false,
			);
		}
		foreach ( $read( 'product-categories.json' ) as $category ) {
			$objects[] = array(
				'kind'    => 'product_cat',
				'live_id' => (int) $category['id'],
				'de_url'  => (string) $category['live']['de_url'],
				'en_url'  => (string) $category['live']['en_url'],
				'title'   => (string) $category['live']['de']['h1'],
				'h1'      => null,
				'archive' => true,
			);
		}
		return $objects;
	}

	/**
	 * The path of a URL.
	 *
	 * @param string $url URL.
	 */
	private static function path( string $url ): string {
		return (string) preg_replace( '#^https?://[^/]+#', '', $url );
	}

	/**
	 * The text of every h1 of a page, tags dropped.
	 *
	 * @param string $html HTML.
	 * @return list<string>
	 */
	private static function headings( string $html ): array {
		preg_match_all( '#<h1\b[^>]*>(.*?)</h1>#s', $html, $matches );
		$out = array();
		foreach ( $matches[1] as $inner ) {
			$out[] = trim( (string) preg_replace( '/\s+/u', ' ', html_entity_decode( strip_tags( $inner ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) ) );
		}
		return $out;
	}

	/**
	 * The local German and English URLs and translation status of the fixture objects, by live ID.
	 *
	 * @return array<string, array{de: string, en: string, status: string, note: string}>
	 */
	private static function local(): array {
		if ( array() !== self::$local ) {
			return self::$local;
		}
		$local = self::php(
			'
			$out = array();
			foreach ( array( "page", "post", "product" ) as $type ) {
				foreach ( get_posts( array( "post_type" => $type, "post_status" => "publish", "numberposts" => -1, "lang" => "en", "meta_key" => "_linker_fixture_id" ) ) as $post ) {
					$german = pll_get_post( $post->ID, "de" );
					$out[ $type . ":" . get_post_meta( $post->ID, "_linker_fixture_id", true ) ] = array(
						"de"     => $german ? get_permalink( $german ) : "",
						"en"     => get_permalink( $post ),
						"status" => (string) get_post_meta( $post->ID, "_linker_i18n_status", true ),
						"note"   => (string) get_post_meta( $post->ID, "_linker_i18n_note", true ),
					);
				}
			}
			foreach ( get_terms( array( "taxonomy" => "product_cat", "hide_empty" => false, "lang" => "en", "meta_key" => "_linker_fixture_id" ) ) as $term ) {
				$german = pll_get_term( $term->term_id, "de" );
				$out[ "product_cat:" . get_term_meta( $term->term_id, "_linker_fixture_id", true ) ] = array(
					"de"     => $german ? get_term_link( $german ) : "",
					"en"     => get_term_link( $term ),
					"status" => (string) get_term_meta( $term->term_id, "_linker_i18n_status", true ),
					"note"   => (string) get_term_meta( $term->term_id, "_linker_i18n_note", true ),
				);
			}
			return $out;
			'
		);
		self::assertIsArray( $local );
		self::$local = $local;
		return $local;
	}

	/**
	 * Each German URL is the live one and answers 200 in German: html lang
	 * de-DE, the German title as a heading, the live German h1 where the
	 * fixture has the body, no canonical but its own and the hreflang pair
	 * with x-default on the English URL. Objects without German body in
	 * the fixture are pending, and say so.
	 */
	public function test_german_urls_are_the_live_ones_and_german(): void {
		$local = self::local();
		foreach ( self::fixture() as $object ) {
			$key = $object['kind'] . ':' . $object['live_id'];
			$this->assertArrayHasKey( $key, $local, $key . ' was not seeded.' );
			$here = $local[ $key ];
			$path = self::path( $object['de_url'] );
			$this->assertSame( $path, self::path( $here['de'] ), $key . ': German URL' );
			$this->assertSame( self::path( $object['en_url'] ), self::path( $here['en'] ), $key . ': English URL' );

			$page = self::get( $path );
			if ( 302 === $page['status'] ) {
				// WooCommerce sends an empty checkout to the cart: it must stay German.
				$this->assertStringStartsWith( self::$site . '/de/', $page['headers']['location'] ?? '', $key . ': redirect' );
				continue;
			}
			$this->assertSame( 200, $page['status'], $key . ': ' . $path );
			$this->assertSame( '<html lang="de-DE">', self::tag( $page['body'], 'html' ), $key . ': html lang' );
			$this->assertContains( $object['title'], self::headings( $page['body'] ), $key . ': German title' );
			if ( null !== $object['h1'] ) {
				$this->assertContains( $object['h1'], self::headings( $page['body'] ), $key . ': live German h1' );
			}
			// WordPress writes the canonical link of single pages; on archives SEOPress does in production.
			$canonical = self::tag( $page['body'], 'link', 'rel="canonical"' );
			if ( ! $object['archive'] || null !== $canonical ) {
				$this->assertSame( '<link rel="canonical" href="' . self::$site . $path . '" />', $canonical, $key . ': canonical' );
			}
			$this->assertSame(
				array(
					'en'        => $here['en'],
					'de'        => self::$site . $path,
					'x-default' => $here['en'],
				),
				self::hreflangs( $page['body'] ),
				$key . ': hreflang'
			);
			if ( 'pending' === $here['status'] ) {
				$this->assertSame( 'no German for post_content', $here['note'], $key . ': pending without the German body' );
			} else {
				$this->assertSame( 'synced', $here['status'], $key . ': status' );
			}
		}
	}

	/**
	 * The English URLs answer in English with the same pair.
	 */
	public function test_english_urls_are_english(): void {
		$local = self::local();
		foreach ( self::fixture() as $object ) {
			$here = $local[ $object['kind'] . ':' . $object['live_id'] ];
			$page = self::get( self::path( $here['en'] ) );
			if ( 302 === $page['status'] ) {
				$this->assertStringStartsNotWith( self::$site . '/de/', $page['headers']['location'] ?? '', $here['en'] );
				continue;
			}
			$this->assertSame( 200, $page['status'], $here['en'] );
			$this->assertSame( '<html lang="en-US">', self::tag( $page['body'], 'html' ), $here['en'] );
			$this->assertSame(
				array(
					'en'        => $here['en'],
					'de'        => $here['de'],
					'x-default' => $here['en'],
				),
				self::hreflangs( $page['body'] ),
				$here['en']
			);
		}
	}

	/**
	 * An English segment under /de/ and a German one without it are 404,
	 * not a second copy of the page (and not a redirect).
	 */
	public function test_wrong_language_segments_are_404(): void {
		$local   = self::local();
		$checked = 0;
		foreach ( self::fixture() as $object ) {
			$here    = $local[ $object['kind'] . ':' . $object['live_id'] ];
			$english = self::path( $here['en'] );
			$german  = self::path( $here['de'] );
			if ( '/' === $english || '/de' . $english === $german ) {
				continue; // The front page, and pages whose slug is the same in both languages.
			}
			foreach ( array( '/de' . $english, (string) preg_replace( '#^/de/#', '/', $german ) ) as $wrong ) {
				$this->assertSame( 404, self::get( $wrong )['status'], $wrong );
				++$checked;
			}
		}
		$this->assertGreaterThan( 30, $checked );
	}

	/**
	 * The sitemap index lists one sitemap per language and type; the German
	 * product sitemap lists exactly the German product URLs.
	 */
	public function test_sitemaps_per_language(): void {
		$index = self::get( '/wp-sitemap.xml' );
		$this->assertSame( 200, $index['status'] );
		$this->assertStringContainsString( '<loc>' . self::$site . '/wp-sitemap-posts-product-1.xml</loc>', $index['body'] );
		$this->assertStringContainsString( '<loc>' . self::$site . '/de/wp-sitemap-posts-product-1.xml</loc>', $index['body'] );
		$this->assertStringContainsString( '<loc>' . self::$site . '/de/wp-sitemap-taxonomies-product_cat-1.xml</loc>', $index['body'] );

		$expected = array(
			'de' => array(),
			'en' => array(),
		);
		foreach ( self::local() as $key => $here ) {
			if ( str_starts_with( $key, 'product:' ) ) {
				$expected['de'][] = $here['de'];
				$expected['en'][] = $here['en'];
			}
		}
		foreach ( array(
			'de' => '/de/wp-sitemap-posts-product-1.xml',
			'en' => '/wp-sitemap-posts-product-1.xml',
		) as $language => $path ) {
			$sitemap = self::get( $path );
			$this->assertSame( 200, $sitemap['status'], $path );
			preg_match_all( '#<loc>([^<]+)</loc>#', $sitemap['body'], $matches );
			$listed = $matches[1];
			sort( $listed );
			sort( $expected[ $language ] );
			$this->assertSame( $expected[ $language ], $listed, $path );
		}
	}

	/**
	 * The browser's language never redirects: / stays English for a German
	 * browser, /de/ is the German front page.
	 */
	public function test_no_redirect_by_browser_language(): void {
		$english = self::get( '/', array( 'Accept-Language' => 'de-DE,de;q=0.9' ) );
		$this->assertSame( 200, $english['status'] );
		$this->assertSame( '<html lang="en-US">', self::tag( $english['body'], 'html' ) );

		$german = self::get( '/de/', array( 'Accept-Language' => 'en-US,en;q=0.9' ) );
		$this->assertSame( 200, $german['status'] );
		$this->assertSame( '<html lang="de-DE">', self::tag( $german['body'], 'html' ) );
	}

	/**
	 * Pages search engines do not index carry no hreflang: 404s and search
	 * results (WordPress marks those noindex).
	 */
	public function test_no_hreflang_on_404_and_search(): void {
		foreach ( array( '/de/gibt-es-nicht-xyz/', '/de/?s=Wechselrichter', '/?s=inverter' ) as $path ) {
			$this->assertSame( array(), self::hreflangs( self::get( $path )['body'] ), $path );
		}
	}
}

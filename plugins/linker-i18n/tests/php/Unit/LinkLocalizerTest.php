<?php
/**
 * Tests for links to German pages.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Translation\HtmlTokenizer;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for LinkLocalizer.
 *
 * @covers \Linker\I18n\LinkLocalizer
 */
final class LinkLocalizerTest extends TestCase {

	/**
	 * Native URL lookup can return zero under the frontend's filtered home URL.
	 *
	 * @var bool
	 */
	private bool $unresolved_posts = false;

	/**
	 * Polylang can return the current language's twin for an English URL query.
	 *
	 * @var bool
	 */
	private bool $translated_posts = false;

	/**
	 * A direct native page lookup must still respect publication and password state.
	 *
	 * @var string
	 */
	private string $page_status = 'publish';

	/**
	 * Password-protected pages are not public contact sources.
	 *
	 * @var string
	 */
	private string $page_password = '';

	/**
	 * The localizer on a site where /contact/ (33) has the German page
	 * /de/kontakt/ (58), the category accessories (46) Zubehör (150), the
	 * shop page products (15) produkte (42).
	 */
	private function localizer(): LinkLocalizer {
		PolylangDouble::mock(
			array(
				11 => 'en',
				22 => 'de',
				33 => 'en',
				58 => 'de',
				15 => 'en',
				42 => 'de',
			),
			array(
				11 => 22,
				33 => 58,
				15 => 42,
			),
			array(
				46  => 'en',
				150 => 'de',
				300 => 'de',
				301 => 'en',
			),
			array(
				46  => 150,
				301 => 300,
			),
			'en',
			array(),
			array_fill_keys(
				array( 11, 22, 33, 58, 15, 42 ),
				array(
					'post_type'     => 'page',
					'post_status'   => $this->page_status,
					'post_password' => $this->page_password,
				)
			)
		);
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- stands in for wp_parse_url.
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn( string $path = '' ) => rtrim( PolylangDouble::HOME, '/' ) . $path ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction(
			'url_to_postid',
			array(
				'return' => function ( string $url ): int {
					$id = array(
						PolylangDouble::HOME . 'contact/'  => 33,
						PolylangDouble::HOME . 'de/kontakt/' => 58,
						PolylangDouble::HOME . 'products/' => 15,
						PolylangDouble::HOME . 'de/produkte/' => 42,
					)[ $url ] ?? 0;
					return $this->unresolved_posts ? 0 : ( $this->translated_posts ? ( array(
						33 => 58,
						15 => 42,
					)[ $id ] ?? $id ) : $id );
				},
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'return' => function ( string $path ) {
					$id = array(
						'contact'  => 33,
						'kontakt'  => 58,
						'products' => 15,
						'produkte' => 42,
					)[ $path ] ?? 0;
					return $id > 0 ? PolylangDouble::post(
						$id,
						array(
							'post_type'     => 'page',
							'post_status'   => $this->page_status,
							'post_password' => $this->page_password,
						)
					) : null;
				},
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( int $id ) => array(
					11 => PolylangDouble::HOME,
					22 => PolylangDouble::HOME . 'de/',
					33 => PolylangDouble::HOME . 'contact/',
					58 => PolylangDouble::HOME . 'de/kontakt/',
					15 => PolylangDouble::HOME . 'products/',
					42 => PolylangDouble::HOME . 'de/produkte/',
				)[ $id ] ?? false,
			)
		);
		WP_Mock::userFunction(
			'wc_get_permalink_structure',
			array( 'return' => array( 'category_rewrite_slug' => 'product-category' ) )
		);
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static function ( array $args ) {
					$slugs = array(
						'accessories'     => 46,
						'zubehoer'        => 150,
						'system-design'   => 301,
						'systemauslegung' => 300,
					);
					return isset( $slugs[ $args['slug'] ] ) ? array( PolylangDouble::term( $slugs[ $args['slug'] ] ) ) : array();
				},
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					unset( $taxonomy );
					return array(
						150 => PolylangDouble::HOME . 'de/produkt-kategorie/zubehoer/',
						46  => PolylangDouble::HOME . 'product-category/accessories/',
						300 => PolylangDouble::HOME . 'de/kategorie/systemauslegung/',
						301 => PolylangDouble::HOME . 'category/system-design/',
					)[ $id ] ?? false;
				},
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn( string $name ) => array(
					'woocommerce_shop_page_id' => '15',
					'page_on_front'            => '11',
				)[ $name ] ?? '',
			)
		);
		WP_Mock::userFunction( 'is_taxonomy_viewable', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_page_uri',
			array(
				'return' => static fn( int $id ) => array(
					15 => 'products',
					42 => 'produkte',
				)[ $id ] ?? false,
			)
		);
		return new LinkLocalizer( new Languages(), new HtmlTokenizer() );
	}

	/**
	 * Links of the site go to the German page; others are left as they are.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function provide_urls(): array {
		$home = PolylangDouble::HOME;
		return array(
			'absolute page'     => array( $home . 'contact/', $home . 'de/kontakt/' ),
			'relative page'     => array( '/contact/#form', '/de/kontakt/#form' ),
			'query kept'        => array( $home . 'contact/?ref=footer', $home . 'de/kontakt/?ref=footer' ),
			'category'          => array( '/product-category/accessories/', '/de/produkt-kategorie/zubehoer/' ),
			'shop'              => array( $home . 'products/', $home . 'de/produkte/' ),
			'home'              => array( $home, $home . 'de/' ),
			'already German'    => array( $home . 'de/kontakt/', $home . 'de/kontakt/' ),
			'no German page'    => array( $home . 'imprint/', $home . 'imprint/' ),
			'external'          => array( 'https://www.goodwe.com/', 'https://www.goodwe.com/' ),
			'mail'              => array( 'mailto:sales@de-linker.com', 'mailto:sales@de-linker.com' ),
			'anchor'            => array( '#top', '#top' ),
			'protocol-relative' => array( '//cdn.example.test/x.js', '//cdn.example.test/x.js' ),
		);
	}

	/**
	 * The German URL.
	 *
	 * @dataProvider provide_urls
	 *
	 * @param string $url      URL.
	 * @param string $expected German URL.
	 */
	public function test_url( string $url, string $expected ): void {
		$this->assertSame( $expected, $this->localizer()->url( $url ) );
	}

	/**
	 * A link in either language becomes the target language's page: the
	 * render-time fallback asks for the request's own language, while the
	 * translation workflow keeps asking for German.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public function provide_target_urls(): array {
		$home = PolylangDouble::HOME;
		return array(
			'English page to German'          => array( $home . 'contact/', 'de', $home . 'de/kontakt/' ),
			'German page to English'          => array( $home . 'de/kontakt/', 'en', $home . 'contact/' ),
			'German page to English, query'   => array( '/de/kontakt/?ref=footer#form', 'en', '/contact/?ref=footer#form' ),
			'English page to German, query'   => array( '/contact/?ref=footer#form', 'de', '/de/kontakt/?ref=footer#form' ),
			'English page stays English'      => array( $home . 'contact/', 'en', $home . 'contact/' ),
			'German page stays German'        => array( $home . 'de/kontakt/', 'de', $home . 'de/kontakt/' ),
			'English home to German'          => array( $home, 'de', $home . 'de/' ),
			'German home to English'          => array( $home . 'de/', 'en', $home ),
			'German category to English'      => array( '/de/produkt-kategorie/zubehoer/', 'en', '/product-category/accessories/' ),
			'English category to German'      => array( '/product-category/accessories/', 'de', '/de/produkt-kategorie/zubehoer/' ),
			'retired category to German'      => array( '/product-category/residential-storage/res-accessories/', 'de', '/de/produkt-kategorie/zubehoer/' ),
			'German blog category to English' => array( '/de/kategorie/systemauslegung/', 'en', '/category/system-design/' ),
			'English blog category to German' => array( '/category/system-design/', 'de', '/de/kategorie/systemauslegung/' ),
			'German shop to English'          => array( '/de/produkte/', 'en', '/products/' ),
			'English shop to German'          => array( '/products/', 'de', '/de/produkte/' ),
		);
	}

	/**
	 * The URL in the target language.
	 *
	 * @dataProvider provide_target_urls
	 *
	 * @param string $url      URL.
	 * @param string $language Target language.
	 * @param string $expected Target URL.
	 */
	public function test_url_in_the_target_language( string $url, string $language, string $expected ): void {
		$this->assertSame( $expected, $this->localizer()->url( $url, $language ) );
	}

	/**
	 * The render-time fallback localizes HTML for the request's language.
	 */
	public function test_localize_html_in_the_target_language(): void {
		$this->assertSame(
			'<p><a href="/contact/">Contact</a> and <a href="https://www.goodwe.com/">GoodWe</a></p>',
			$this->localizer()->localize( '<p><a href="/de/kontakt/">Contact</a> and <a href="https://www.goodwe.com/">GoodWe</a></p>', 'en' )
		);
	}

	/**
	 * In HTML only the href of links changes.
	 */
	public function test_localize_html(): void {
		$this->assertSame(
			'<p>Write to <a class="btn" href="/de/kontakt/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>',
			$this->localizer()->localize( '<p>Write to <a class="btn" href="/contact/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>' )
		);
	}

	/** Marked handoffs localize their source even when the destination is already German. */
	public function test_contact_source_follows_the_rendered_language_without_changing_other_bytes(): void {
		$home   = PolylangDouble::HOME;
		$source = $home . 'products/?q=SAJ+5&brand=saj#model';
		$target = $home . 'de/produkte/?q=SAJ+5&brand=saj#model';
		$prefix = '<script>const icon="\\u003csvg"; const path=/\\s+/g;</script><a data-linker-contact=\'{"url":"' . $home . 'products/"}\' href="/de/kontakt/?intent=offer&amp;source=';
		$suffix = '&amp;source_id=15&amp;search=PV%20%2B+storage&amp;filters%5Bbrand%5D=saj#form">Contact</a><img src="/products/x.png">';
		$this->assertSame(
			$prefix . rawurlencode( $target ) . $suffix,
			$this->localizer()->localize( $prefix . rawurlencode( $source ) . $suffix, 'de' )
		);
	}

	/** Home paths follow native Polylang roots in both directions. */
	public function test_contact_home_sources_work_in_both_directions(): void {
		$home  = PolylangDouble::HOME;
		$cases = array(
			'de' => array( '/contact/', $home, '/de/kontakt/', $home . 'de/' ),
			'en' => array( '/de/kontakt/', $home . 'de/', '/contact/', $home ),
		);
		foreach ( $cases as $language => $values ) {
			$this->assertSame(
				'<a data-linker-contact="" href="' . $values[2] . '?source=' . rawurlencode( $values[3] ) . '">Contact</a>',
				$this->localizer()->localize( '<a data-linker-contact="" href="' . $values[0] . '?source=' . rawurlencode( $values[1] ) . '">Contact</a>', $language )
			);
		}
	}

	/** The public URL API and unmarked links retain their established query contract. */
	public function test_unmarked_contact_query_is_unchanged(): void {
		$query = '?source=' . rawurlencode( PolylangDouble::HOME );
		$this->assertSame( '/de/kontakt/' . $query, $this->localizer()->url( '/contact/' . $query ) );
		$this->assertSame( '<a href="/de/kontakt/' . $query . '">Contact</a>', $this->localizer()->localize( '<a href="/contact/' . $query . '">Contact</a>' ) );
	}

	/** A source that the Contact boundary rejects must not become a valid same-origin URL. */
	public function test_contact_does_not_repair_foreign_credentialed_or_unknown_sources(): void {
		foreach ( array( 'https://elsewhere.test/products/', 'http://example.test:8080/products/', 'https://example.test/products/', 'http://user@example.test/products/', '//example.test/products/', '/products/', 'javascript:alert(1)', PolylangDouble::HOME . 'unknown/' ) as $source ) {
			$html = '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $source ) . '">Contact</a>';
			$this->assertSame( $html, $this->localizer()->localize( $html ) );
		}
		foreach ( array( 'http://example.test:8080/contact/', 'http://user@example.test/contact/', 'https://elsewhere.test/contact/', '//example.test/contact/' ) as $destination ) {
			$html = '<a data-linker-contact="" href="' . $destination . '?source=' . rawurlencode( PolylangDouble::HOME ) . '">Contact</a>';
			$this->assertSame( $html, $this->localizer()->localize( $html ) );
		}
	}

	/** The frontend's filtered home URL must not prevent resolving a native page pair. */
	public function test_native_page_lookup_recovers_a_page_when_url_lookup_returns_zero(): void {
		$this->unresolved_posts = true;
		$this->assertSame( PolylangDouble::HOME . 'de/kontakt/', $this->localizer()->url( PolylangDouble::HOME . 'contact/', 'de' ) );
		$this->assertSame( PolylangDouble::HOME . 'contact/', $this->localizer()->url( PolylangDouble::HOME . 'de/kontakt/', 'en' ) );
	}

	/** A translated query result does not mean the URL already belongs to that language. */
	public function test_native_query_returning_the_current_language_twin_still_localizes_the_source_url(): void {
		$this->translated_posts = true;
		$this->assertSame( PolylangDouble::HOME . 'de/kontakt/', $this->localizer()->url( PolylangDouble::HOME . 'contact/', 'de' ) );
		$this->assertSame( PolylangDouble::HOME . 'de/produkte/', $this->localizer()->url( PolylangDouble::HOME . 'products/', 'de' ) );
	}

	/** A fallback must not accept an alias, private page or protected page. */
	public function test_native_page_fallback_requires_a_public_canonical_page(): void {
		$this->unresolved_posts = true;
		$this->assertSame( PolylangDouble::HOME . 'fake/contact/', $this->localizer()->url( PolylangDouble::HOME . 'fake/contact/' ) );
		$this->page_status = 'private';
		$this->assertSame( PolylangDouble::HOME . 'contact/', $this->localizer()->url( PolylangDouble::HOME . 'contact/' ) );
		$this->page_status   = 'publish';
		$this->page_password = 'restricted';
		$this->assertSame( PolylangDouble::HOME . 'contact/', $this->localizer()->url( PolylangDouble::HOME . 'contact/' ) );
	}

	/** Unknown taxonomy parents stay rejected sources; ordinary redirect compatibility is separate. */
	public function test_marked_source_does_not_turn_an_unknown_taxonomy_path_into_a_real_source(): void {
		$source = PolylangDouble::HOME . 'product-category/definitely-not-a-real-parent/accessories/';
		$html   = '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $source ) . '">Contact</a>';
		$this->assertSame( $html, $this->localizer()->localize( $html ) );
		$this->assertSame( PolylangDouble::HOME . 'de/produkt-kategorie/zubehoer/', $this->localizer()->url( $source ) );
		$valid  = PolylangDouble::HOME . 'product-category/accessories/';
		$target = PolylangDouble::HOME . 'de/produkt-kategorie/zubehoer/';
		$this->assertSame( '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $target ) . '">Contact</a>', $this->localizer()->localize( '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $valid ) . '">Contact</a>' ) );
	}

	/** Private and password-protected pages, including home, must not become accepted sources. */
	public function test_marked_source_requires_a_public_unprotected_page(): void {
		foreach ( array( 'private', 'password' ) as $restriction ) {
			$this->page_status   = 'private' === $restriction ? 'private' : 'publish';
			$this->page_password = 'password' === $restriction ? 'restricted' : '';
			foreach ( array( PolylangDouble::HOME, PolylangDouble::HOME . 'contact/' ) as $source ) {
				$html = '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $source ) . '">Contact</a>';
				$this->assertSame( $html, $this->localizer()->localize( $html ) );
			}
		}
	}

	/** The shop's legacy URI matching does not make a noncanonical contact source valid. */
	public function test_shop_source_requires_the_canonical_path_of_its_own_language(): void {
		$source = PolylangDouble::HOME . 'produkte/';
		$html   = '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $source ) . '">Contact</a>';
		$this->assertSame( $html, $this->localizer()->localize( $html ) );
		$this->assertSame( PolylangDouble::HOME . 'de/produkte/', $this->localizer()->url( $source ) );
		$valid  = PolylangDouble::HOME . 'products/';
		$target = PolylangDouble::HOME . 'de/produkte/';
		$this->assertSame( '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $target ) . '">Contact</a>', $this->localizer()->localize( '<a data-linker-contact="" href="/de/kontakt/?source=' . rawurlencode( $valid ) . '">Contact</a>' ) );
	}
}

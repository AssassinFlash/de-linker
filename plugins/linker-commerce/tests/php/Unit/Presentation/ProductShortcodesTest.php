<?php
/**
 * Tests for the catalogue shortcodes' language links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Presentation\LanguageLinks;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\Support\MocksSelectionFacts;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;
use WP_Post;
use WP_Term;

/**
 * The language half is the translated permalink of the queried object plus
 * the request path past that object's permalink. The current language's half
 * is the address the visitor is on.
 *
 * @covers \Linker\Commerce\Presentation\ProductShortcodes
 */
final class ProductShortcodesTest extends TestCase {
	use \Linker\Commerce\Tests\Support\PublishedDocumentView;

	use MocksSelectionFacts;

	/**
	 * The product the product-page tests below read.
	 */
	private const PDP = 6530;

	/**
	 * The product mock the current test's reads answer with.
	 *
	 * @var WC_Product|null
	 */
	private ?WC_Product $pdp_product = null;

	/** The card model for the current fixture.
	 *
	 * @var string
	 */
	private string $pdp_model = 'GW60K-STS-G10';

	/**
	 * The legacy ACF JSON the current test's reads answer with.
	 *
	 * @var array<string, mixed>
	 */
	private array $pdp_acf = array();

	/**
	 * The product's WooCommerce gallery field as the current test's reads
	 * answer it (the comma-separated editor list).
	 *
	 * @var string
	 */
	private string $pdp_gallery = '6504,6505';

	/**
	 * The URL of an attachment in the fixture: it names the id, so a test can
	 * tell which picture a shortcode printed.
	 *
	 * @param int $id The attachment.
	 */
	private function pdp_image_url( int $id ): string {
		return 'http://linker.test/uploads/image-' . $id . '.png';
	}

	/**
	 * Translation and escaping return their input; permalink helpers are the
	 * WordPress ones the shortcode calls, reduced to path joining.
	 */
	public function setUp(): void {
		parent::setUp();
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products( array( 6530 => 6530 ) );
		$this->plain_text();
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => static fn( string $path = '/' ): string => 'http://linker.test' . ( '' === $path || '/' === $path ? '/' : $path ),
			)
		);
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static function ( string $url, int $component = -1 ) {
					$parsed = -1 === $component ? parse_url( $url ) : parse_url( $url, $component );
					return false === $parsed ? null : $parsed;
				},
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				// Both forms the tree calls: add_query_arg( array $args, ?string $url )
				// and WordPress's add_query_arg( string $key, $value, ?string $url )
				// (ProductView's sign-in URL).
				'return' => static function ( $first, $second = null, $third = null ): string {
					$args     = \is_array( $first ) ? $first : array( (string) $first => $second );
					// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.MissingUnslash, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
					$base_url = ( \is_array( $first ) ? $second : $third ) ?? (string) ( $_SERVER['REQUEST_URI'] ?? 'http://linker.test/' );
					$parts    = parse_url( $base_url );
					$query    = array();
					if ( is_array( $parts ) && isset( $parts['query'] ) ) {
						parse_str( $parts['query'], $query );
						$query = array_map( self::encode_query_value( ... ), $query );
					}
					foreach ( $args as $key => $value ) {
						$query[ $key ] = $value;
					}
					$base = strtok( $base_url, '?' );
					return array() === $query ? (string) $base : $base . '?' . implode( '&', array_map( static fn( $key, $value ): string => $key . '=' . $value, array_keys( $query ), $query ) );
				},
			)
		);
		WP_Mock::userFunction(
			'remove_query_arg',
			array(
				'return' => static function ( $keys, ?string $url = null ): string {
					// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.MissingUnslash, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
					$base_url = $url ?? (string) ( $_SERVER['REQUEST_URI'] ?? 'http://linker.test/' );
					$parts    = parse_url( $base_url );
					if ( ! is_array( $parts ) || ! isset( $parts['query'] ) ) {
						return $base_url;
					}
					parse_str( $parts['query'], $query );
					foreach ( (array) $keys as $key ) {
						unset( $query[ $key ] );
					}
					$base = strtok( $base_url, '?' );
					return array() === $query ? (string) $base : $base . '?' . http_build_query( $query );
				},
			)
		);
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		// Model the native text sanitizer's whitespace and percent-sequence handling.
		WP_Mock::userFunction(
			'sanitize_text_field',
			array(
				'return' => static function ( string $value ): string {
					$collapsed = (string) preg_replace( '/[\r\n\t ]+/', ' ', trim( $value ) );
					return trim( (string) preg_replace( '/%[a-f0-9]{2}/i', '', $collapsed ) );
				},
			)
		);
		WP_Mock::userFunction( 'user_trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn( $thing ): bool => $thing instanceof \WP_Error ) );
		WP_Mock::userFunction( 'get_query_var', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => false ) );
	}

	/**
	 * An account endpoint, its value and a nested endpoint stay on the translated account permalink.
	 *
	 * @dataProvider account_paths
	 * @param string $request  The visitor's path.
	 * @param string $expected The German half.
	 */
	public function test_account_path_is_appended_to_the_translated_account_permalink( string $request, string $expected ): void {
		$this->page(
			1037,
			'http://linker.test/my-account/',
			array(
				'de' => 6869,
			)
		);
		$this->permalink( 6869, 'http://linker.test/de/mein-konto/' );
		$_SERVER['REQUEST_URI'] = $request;
		$_GET                   = array();

		$this->filter_returns( 'pll_translation_url', $expected, array( $expected, 'de' ) );
		$this->assertSame( $expected, $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test' . $request, $this->url( 'en' ) );
	}

	/**
	 * The footer's switcher is the header's implementation: on an English
	 * account page "Deutsch" opens the German account page, not /de/, and
	 * "English" stays on the page the visitor is on (AUDIT.md H2).
	 */
	public function test_the_footer_switcher_uses_the_same_language_targets_as_the_header(): void {
		$this->page(
			1037,
			'http://linker.test/my-account/',
			array( 'de' => 6869 )
		);
		$this->permalink( 6869, 'http://linker.test/de/mein-konto/' );
		$_SERVER['REQUEST_URI'] = '/my-account/';
		$_GET                   = array();
		WP_Mock::userFunction( 'pll_the_languages', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => 'http://linker.test/' ) );
		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/mein-konto/', array( 'http://linker.test/de/mein-konto/', 'de' ) );

		$html = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->language_switch();

		$this->assertStringContainsString( 'href="http://linker.test/my-account/"', $html );
		$this->assertStringContainsString( 'href="http://linker.test/de/mein-konto/"', $html );
		$this->assertStringContainsString( 'data-lnk-flang="en"', $html );
		$this->assertStringContainsString( 'data-lnk-flang="de"', $html );
		$this->assertStringContainsString( 'lang="en" aria-current="true"', $html );
		$this->assertStringNotContainsString( 'lang="de" aria-current="true"', $html );
		$this->assertStringContainsString( 'data-linker-language-choice="en"', $html );
	}

	/** Family selection and its actual page survive the shared language consumer. */
	public function test_language_switch_keeps_family_selection_search_and_order(): void {
		$this->page( 1038, 'http://linker.test/products/', array( 'de' => 6870 ) );
		$this->permalink( 6870, 'http://linker.test/de/produkte/' );
		$_GET                   = array(
			'q'            => 'ESA',
			'sort'         => 'name',
			'brand'        => 'goodwe',
			'kw_min'       => '5.5',
			'product-page' => '2',
			'ignored'      => 'unrelated',
		);
		$_SERVER['REQUEST_URI'] = '/products/?q=ESA&sort=name&brand=goodwe&kw_min=5.5&product-page=2';
		WP_Mock::userFunction( 'pll_the_languages', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => 'http://linker.test/' ) );
		$expected = 'http://linker.test/de/produkte/?q=ESA&sort=name&brand=goodwe&kw_min=5.5&product-page=2';
		$this->filter_returns( 'pll_translation_url', $expected, array( $expected, 'de' ) );
		self::assertSame( $expected, $this->url( 'de' ) );
	}

	/** The German footer marks German, while keeping both translated targets. */
	public function test_the_german_footer_marks_its_actual_language(): void {
		$this->page( 6869, 'http://linker.test/de/mein-konto/', array( 'en' => 1037 ), 'de' );
		$this->permalink( 1037, 'http://linker.test/my-account/' );
		$_SERVER['REQUEST_URI'] = '/de/mein-konto/';
		$_GET                   = array();
		WP_Mock::userFunction( 'pll_the_languages', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => 'http://linker.test/' ) );
		$this->filter_returns( 'pll_translation_url', 'http://linker.test/my-account/', array( 'http://linker.test/my-account/', 'en' ) );
		$html = ( new LanguageLinks() )->footer();
		$this->assertStringContainsString( 'lang="de" aria-current="true"', $html );
		$this->assertStringNotContainsString( 'lang="en" aria-current="true"', $html );
		$this->assertStringContainsString( 'href="http://linker.test/my-account/"', $html );
		$this->assertStringContainsString( 'href="http://linker.test/de/mein-konto/"', $html );
	}

	/**
	 * The account paths the language half has to keep whole.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function account_paths(): array {
		return array(
			'endpoint'        => array( '/my-account/inquiries/', 'http://linker.test/de/mein-konto/inquiries/' ),
			'endpoint value'  => array( '/my-account/inquiry/1600/', 'http://linker.test/de/mein-konto/inquiry/1600/' ),
			'paging'          => array( '/my-account/inquiries/2/', 'http://linker.test/de/mein-konto/inquiries/2/' ),
			'nested endpoint' => array( '/my-account/company/billing/', 'http://linker.test/de/mein-konto/company/billing/' ),
		);
	}

	/**
	 * A confirmation stays on the translated request page, endpoint and value included.
	 */
	public function test_confirmation_stays_on_the_translated_request_page(): void {
		$this->page(
			1036,
			'http://linker.test/proforma-request/',
			array(
				'de' => 6867,
			)
		);
		$this->permalink( 6867, 'http://linker.test/de/proforma-anfrage/' );
		$_SERVER['REQUEST_URI'] = '/proforma-request/inquiry-received/7021/?key=k';
		$_GET                   = array( 'key' => 'k' );

		// Woo needs the order key on the confirmation page — without it the
		// thank-you page renders without the order's details.
		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', array( 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', 'de' ) );
		$this->assertSame( 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', $this->url( 'de' ) );
		$this->assertStringNotContainsString( 'mein-konto', $this->url( 'de' ) );
	}

	/**
	 * A category page keeps paging; the query keys the visitor set travel with the link.
	 */
	public function test_category_paging_and_the_visitor_query_are_kept(): void {
		$term = new WP_Term(
			(object) array(
				'term_id'  => 44,
				'slug'     => 'inverters',
				'taxonomy' => 'product_cat',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( $term ),
				'return' => 'http://linker.test/product-category/inverters/',
			)
		);
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				'args'   => array( 44, 'de' ),
				'return' => 88,
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( 88 ),
				'return' => 'http://linker.test/de/produkt-kategorie/wechselrichter/',
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/page/2/?step=roof';
		$_GET                   = array( 'step' => 'roof' );

		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/product-category/inverters/page/2/?step=roof',
			)
		);

		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/produkt-kategorie/wechselrichter/page/2/?step=roof', array( 'http://linker.test/de/produkt-kategorie/wechselrichter/page/2/?step=roof', 'de' ) );
		$this->assertSame( 'http://linker.test/de/produkt-kategorie/wechselrichter/page/2/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/product-category/inverters/page/2/?step=roof', $this->url( 'en' ) );
	}

	/**
	 * A search is not a queried page: the switcher's URL keeps the search query.
	 */
	public function test_search_keeps_the_switcher_url_and_the_query(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/?s=inverter' ),
				),
			)
		);
		WP_Mock::userFunction( 'pll_get_requested_url', array( 'return' => 'http://linker.test/?s=inverter' ) );
		$_SERVER['REQUEST_URI'] = '/?s=inverter';
		$_GET                   = array( 's' => 'inverter' );

		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/?s=inverter', array( 'http://linker.test/de/?s=inverter', 'de' ) );
		$this->assertSame( 'http://linker.test/de/?s=inverter', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/?s=inverter', $this->url( 'en' ) );

		$_GET['post_type'] = 'post';
		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/?s=inverter&post_type=post', array( 'http://linker.test/de/?s=inverter&post_type=post', 'de' ) );
		$this->assertSame( 'http://linker.test/de/?s=inverter&post_type=post', $this->url( 'de' ), 'Journal scope must not silently become a general search in the other language.' );
		$_GET['post_type'] = array( 'post' );
		$this->assertSame( 'http://linker.test/de/?s=inverter', $this->url( 'de' ), 'Malformed type lists do not become preserved journal scope.' );
	}

	/**
	 * Journal search keeps the visitor's text and uses the target language,
	 * including when the native switcher uses a language query parameter.
	 *
	 * @dataProvider journal_search_language_urls
	 * @param string $current Current language.
	 * @param string $target Target language.
	 * @param string $native_url Polylang switcher URL.
	 * @param string $search Visitor's search text.
	 * @param string $before URL produced by the previous adapter.
	 * @param string $expected Expected URL passed through the native filter.
	 */
	public function test_journal_search_switch_targets_the_requested_language( string $current, string $target, string $native_url, string $search, string $before, string $expected ): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => $current ) );
		WP_Mock::userFunction( 'pll_the_languages', array( 'return' => array( $target => array( 'url' => $native_url ) ) ) );
		$_SERVER['REQUEST_URI'] = '/?post_type=post&lang=' . $current . '&s=' . rawurlencode( $search );
		$_GET                   = array(
			'post_type' => 'post',
			'lang'      => $current,
			's'         => $search,
		);
		foreach ( array_unique( array( $before, $expected ) ) as $filtered_url ) {
			$this->filter_returns( 'pll_translation_url', $filtered_url, array( $filtered_url, $target ) );
		}

		$url = $this->url( $target );
		parse_str( (string) parse_url( $url, PHP_URL_QUERY ), $query );
		self::assertSame( $expected, $url );
		self::assertSame( $target, $query['lang'] ?? null );
		self::assertSame( $search, $query['s'] ?? null );
		self::assertSame( 'post', $query['post_type'] ?? null );
	}

	/**
	 * Native directory and query-mode switcher answers.
	 *
	 * @return array<string, array{string, string, string, string, string, string}>
	 */
	public function journal_search_language_urls(): array {
		return array(
			'german directory to english with stale query' => array( 'de', 'en', 'http://linker.test/?lang=de&s=Notstrom&post_type=post', 'Notstrom', 'http://linker.test/?lang=de&s=Notstrom&post_type=post', 'http://linker.test/?lang=en&s=Notstrom&post_type=post' ),
			'query mode to german'                         => array( 'en', 'de', 'http://linker.test/?lang=de&s=inverter', 'inverter', 'http://linker.test/?lang=de&s=inverter&post_type=post', 'http://linker.test/?lang=de&s=inverter&post_type=post' ),
			'explicit default language path and query'     => array( 'de', 'en', 'http://linker.test/en/?lang=en&s=Notstrom', 'Notstrom', 'http://linker.test/en/?lang=en&s=Notstrom&post_type=post', 'http://linker.test/en/?lang=en&s=Notstrom&post_type=post' ),
			'encoded visitor text'                         => array( 'de', 'en', 'http://linker.test/?lang=de', 'SMA + Speicher & Akku', 'http://linker.test/?lang=de&s=SMA%20%2B%20Speicher%20%26%20Akku&post_type=post', 'http://linker.test/?lang=en&s=SMA%20%2B%20Speicher%20%26%20Akku&post_type=post' ),
			'literal percent and repeated spaces'          => array( 'de', 'en', 'http://linker.test/?lang=en', 'PV%20  battery', 'http://linker.test/?lang=en&s=PV%20battery&post_type=post', 'http://linker.test/?lang=en&s=PV%2520%20%20battery&post_type=post' ),
			'markup is encoded in the URL'                 => array( 'de', 'en', 'http://linker.test/?lang=en', '"><script>alert(1)</script>', 'http://linker.test/?lang=en&s=%22%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E&post_type=post', 'http://linker.test/?lang=en&s=%22%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E&post_type=post' ),
		);
	}

	/** An empty journal search stays a search for posts after switching. */
	public function test_empty_journal_search_keeps_its_search_key_and_post_scope(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'pll_the_languages', array( 'return' => array( 'en' => array( 'url' => 'http://linker.test/?lang=de' ) ) ) );
		$_SERVER['REQUEST_URI'] = '/de/?post_type=post&lang=de&s=';
		$_GET                   = array(
			'post_type' => 'post',
			'lang'      => 'de',
			's'         => '',
		);
		$before                 = 'http://linker.test/?lang=de';
		$expected               = 'http://linker.test/?lang=en&s=&post_type=post';
		$this->filter_returns( 'pll_translation_url', $before, array( $before, 'en' ) );
		$this->filter_returns( 'pll_translation_url', $expected, array( $expected, 'en' ) );

		$url = $this->url( 'en' );
		parse_str( (string) parse_url( $url, PHP_URL_QUERY ), $query );
		self::assertArrayHasKey( 's', $query );
		self::assertSame( '', $query['s'] );
		self::assertSame( 'post', $query['post_type'] ?? null );
		self::assertSame( 'en', $query['lang'] ?? null );
	}

	/**
	 * Without a queried object the switcher's URL is the answer, query included.
	 * The current language's half is the request, cache-bust key included.
	 */
	public function test_a_page_without_a_queried_object_keeps_the_switcher_url(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/loesungskonfigurator/?step=roof' ),
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/solution-configurator/?step=roof&cbq=1',
			)
		);
		$_SERVER['REQUEST_URI'] = '/solution-configurator/?step=roof&cbq=1';
		$_GET                   = array(
			'step' => 'roof',
			'cbq'  => '1',
		);

		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/loesungskonfigurator/?step=roof', array( 'http://linker.test/de/loesungskonfigurator/?step=roof', 'de' ) );
		$this->assertSame( 'http://linker.test/de/loesungskonfigurator/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/solution-configurator/?step=roof', $this->url( 'en' ) );
	}


	/**
	 * A product proposal survives the native language switch. A cache-bust key does not.
	 */
	public function test_language_switch_keeps_the_product_proposal(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/loesungskonfigurator/?step=equipment&product_id=1946' ),
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/solution-configurator/?step=equipment&product_id=1946&cbq=1',
			)
		);
		$_SERVER['REQUEST_URI'] = '/solution-configurator/?step=equipment&product_id=1946&cbq=1';
		$_GET                   = array(
			'step'       => 'equipment',
			'product_id' => '1946',
			'cbq'        => '1',
		);

		$this->filter_returns( 'pll_translation_url', 'http://linker.test/de/loesungskonfigurator/?step=equipment&product_id=1946', array( 'http://linker.test/de/loesungskonfigurator/?step=equipment&product_id=1946', 'de' ) );
		$this->assertSame( 'http://linker.test/de/loesungskonfigurator/?step=equipment&product_id=1946', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/solution-configurator/?step=equipment&product_id=1946', $this->url( 'en' ) );
	}

	/**
	 * The fixture's request path, without its query.
	 */
	private function request_path(): string {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '/'; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
		return (string) strtok( $uri, '?' );
	}

	/**
	 * The catalogue query's common reads: the queried object (or none), the
	 * shop address, the category terms' reads and the helper shortcodes.
	 *
	 * @param WP_Term|null                       $term        The queried category, null on the shop.
	 * @param array<int, WP_Term>                $top         The top-level categories.
	 * @param array<int, array<int, WP_Term>>    $children    Children by parent term id.
	 * @param array<int, int>                    $product_ids The archive's products, in the order get_posts() answers them.
	 * @param array<string, array<int, WP_Term>> $by_slug   The terms the rail's display map looks up by English slug; they answer get_term() by id too, so the English anchors of a translated lookup resolve.
	 * @param callable(int, string): int|null    $twin        The twin the language layer links for a term id and the language a lookup asks for ('' for the language on display); null while the fixture runs without a language layer, where every lookup answers 0 — the definition of a stubbed pll_* function outlives the test that made it, so the rail's reads have to be answered here either way.
	 * @param string                             $home        Polylang's home URL for the request's language.
	 */
	private function mock_catalog_query( ?WP_Term $term, array $top = array(), array $children = array(), array $product_ids = array(), array $by_slug = array(), ?callable $twin = null, string $home = 'http://linker.test/' ): void {
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				// Without a twin every lookup answers 0, the way a site whose
				// terms carry no language layer answers.
				'return' => static fn ( int $id, string $language = '' ): int => null === $twin ? 0 : $twin( $id, $language ),
			)
		);
		// Polylang's home URL carries the request's language segment (/de/ on
		// German); the breadcrumb follows it (#264 H5). PageUrls::home() (#263)
		// names the language itself and trails the slash, so both halves are
		// answered here: the language the request runs in (read off the home
		// URL the fixture wants, so the stub cannot inherit a prior test's) and
		// the slash shape it prints.
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => str_contains( $home, '/de/' ) ? 'de' : 'en' ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => $home ) );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		// The rail's tool card links the configurator page; the fixture has
		// none (get_page_by_path answers nothing).
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => null ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn ( string $option ) => 'default_product_cat' === $option ? 15 : 'no',
			)
		);
		WP_Mock::userFunction( 'do_shortcode', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static function ( array $args ) use ( $top, $children, $by_slug ) {
					if ( isset( $args['slug'] ) && isset( $by_slug[ $args['slug'] ] ) ) {
						return $by_slug[ $args['slug'] ];
					}
					if ( isset( $args['parent'] ) && isset( $children[ $args['parent'] ] ) ) {
						return $children[ $args['parent'] ];
					}
					if ( isset( $args['parent'] ) && 0 === $args['parent'] ) {
						return $top;
					}
					return array();
				},
			)
		);
		$terms_by_id = array();
		if ( null !== $term ) {
			$terms_by_id[ (int) $term->term_id ] = $term;
		}
		foreach ( array_merge( $top, ...array_values( $children ), ...array_values( $by_slug ) ) as $term_row ) {
			$terms_by_id[ (int) $term_row->term_id ] = $term_row;
			WP_Mock::userFunction(
				'get_term_link',
				array(
					'args'   => array( $term_row ),
					'return' => 'http://linker.test/product-category/' . $term_row->slug . '/',
				)
			);
		}
		// The crumb and the rail's branch walk read the remembered terms by
		// id; anything else answers nothing, which ends a parent chain.
		WP_Mock::userFunction(
			'get_term',
			array(
				'return' => static fn ( int $id ): ?WP_Term => $terms_by_id[ $id ] ?? null,
			)
		);
		if ( null !== $term ) {
			WP_Mock::userFunction(
				'get_term_link',
				array(
					'args'   => array( $term ),
					'return' => 'http://linker.test/product-category/' . $term->slug . '/',
				)
			);
		}
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'exclude-from-catalog' => 99,
					'outofstock'           => 98,
				),
			)
		);
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => $product_ids ) );
		WP_Mock::userFunction( 'get_post_time', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'setup_postdata' );
		WP_Mock::userFunction( 'wp_reset_postdata' );
	}

	/**
	 * A term row.
	 *
	 * @param int    $id     Term id.
	 * @param string $name   Name.
	 * @param string $slug   Slug.
	 * @param int    $parent_id Parent term id.
	 */
	private function term( int $id, string $name, string $slug, int $parent_id = 0 ): WP_Term {
		return new WP_Term(
			(object) array(
				'term_id'  => $id,
				'name'     => $name,
				'slug'     => $slug,
				'taxonomy' => 'product_cat',
				'parent'   => $parent_id,
			)
		);
	}

	/**
	 * The nested category's crumb walks the term's parent chain: the live
	 * all-in-one page reads HOME / PRODUCTS / COMMERCIAL STORAGE /
	 * ALL-IN-ONE SYSTEMS, the parent linked, the category itself bold
	 * (measured 2026-10-12; recheck 2026-10-14 found the deployed crumb
	 * missing the parent segment).
	 */
	public function test_head_breadcrumb_walks_the_parent_chain(): void {
		$parent = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$child  = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		// No language layer: the crumb reads the terms' own names.
		WP_Mock::userFunction( 'pll_get_term', array( 'return' => 0 ) );
		$this->mock_catalog_query( $child, array( $parent ) );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		$this->assertStringContainsString( 'HOME</a> / <a href="http://linker.test/products/">PRODUCTS</a> / <a href="http://linker.test/product-category/commercial-storage/">COMMERCIAL STORAGE</a> / <b>ALL-IN-ONE SYSTEMS</b>', $head );
	}

	/**
	 * The German crumb is German-only (owner ruling 2026-10-17; ticket #264
	 * H5): the home link carries the language segment and the category names
	 * are the queried German terms, not their English twins. The old tree
	 * printed the English names on purpose to match the live site; the ruling
	 * makes that defect the change.
	 */
	public function test_german_head_breadcrumb_uses_german_names_and_the_german_home(): void {
		$parent = $this->term( 451, 'Gewerbespeicher', 'gewerbespeicher' );
		$child  = $this->term( 452, 'Komplettsysteme', 'komplettsysteme', 451 );
		$this->mock_catalog_query( $child, array( $parent ), array(), array(), array(), null, 'http://linker.test/de/' );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		$this->assertStringContainsString( 'href="http://linker.test/de/">HOME</a>', $head );
		$this->assertStringContainsString( '<a href="http://linker.test/product-category/gewerbespeicher/">GEWERBESPEICHER</a>', $head );
		$this->assertStringContainsString( '<b>KOMPLETTSYSTEME</b>', $head );
		$this->assertStringNotContainsString( 'COMMERCIAL STORAGE', $head );
		$this->assertStringNotContainsString( 'ALL-IN-ONE SYSTEMS', $head );
	}

	/**
	 * A term name stored HTML-encoded ("&amp;") is decoded before the crumb
	 * uppercases it, so the page prints "&" and not "&AMP;".
	 */
	public function test_a_category_name_with_an_entity_uppercases_cleanly(): void {
		$term = $this->term( 453, 'Energiezähler &amp; Stromwandler', 'energiezaehler-stromwandler' );
		$this->mock_catalog_query( $term, array(), array(), array(), array(), null, 'http://linker.test/de/' );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		// The unit process passes esc_html() through, so the clean name prints
		// the decoded "&"; the defect this pins is the uppercased entity.
		$this->assertStringContainsString( '<b>ENERGIEZÄHLER & STROMWANDLER</b>', $head );
		$this->assertStringNotContainsString( '&AMP;', $head );
	}

	/**
	 * The head's tool row carries the AI entry only: the batch item-number
	 * and nameplate chips stay out (owner re-confirmed 2026-10-13, spec 13
	 * section C), and no chip may borrow another surface's words.
	 */
	public function test_head_tool_row_carries_the_ai_entry_alone(): void {
		$this->mock_catalog_query( null );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		$this->assertStringContainsString( 'class="wb-acts"', $head );
		$this->assertStringNotContainsString( 'Batch item numbers', $head );
		$this->assertStringNotContainsString( 'Identify a device from a nameplate photo', $head );
		$this->assertStringNotContainsString( 'data-linker-bom-open', $head );
	}

	/**
	 * The rail's hidden summary carries the applied count ("Filters (1)" on
	 * a category with no facet selected — the category is the one filter),
	 * and the Reset link sits in the rail-head row, the one the stylesheet
	 * shows (`#linker-products .rail-summary` is display:none,
	 * storefront.css:212; the rail-head is the flex row the live filtered
	 * rail shows its "Filters … Reset" on).
	 */
	public function test_filters_summary_shows_the_count_without_a_facet_and_reset_with_one(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
				32 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 30.0,
				),
			)
		);
		$category = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$this->mock_catalog_query( $category, array( $this->term( 451, 'Commercial Storage', 'commercial-storage' ) ) );

		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$_GET       = array();
		$summary    = $shortcodes->products_filters();
		$this->assertStringContainsString( 'Filters (1)</span><span class="rail-summary-mark"', $summary );
		// Without a facet there is no Reset anywhere on the rail.
		$this->assertStringNotContainsString( 'rail-reset', $summary );

		$_GET = array( 'brand' => 'goodwe' );
		$rail = $shortcodes->products_filters();
		// The Reset sits in the visible rail-head row, after its label.
		$this->assertStringContainsString( '<div class="rail-head"><span class="rail-head-label">Filters</span><a class="rail-reset" href="http://linker.test/product-category/all-in-one-systems/">Reset</a></div>', $rail );

		$_GET = array(
			'brand'        => 'goodwe',
			'q'            => 'ESA & 5',
			'sort'         => 'name',
			'product-page' => '3',
		);
		$rail = $shortcodes->products_filters();
		$this->assertStringContainsString( 'class="rail-reset" href="http://linker.test/product-category/all-in-one-systems/?q=ESA%20%26%205&sort=name"', $rail );
		$this->assertStringContainsString( '<div class="product-filter-actions"><a href="http://linker.test/product-category/all-in-one-systems/?q=ESA%20%26%205&sort=name">Clear</a>', $rail );
	}

	/**
	 * The rail's Power section is the view's own: a shelf whose products carry
	 * no AC power figure renders no Power fold at all — the live rail of the
	 * powerless shelves (meters, EMS) reads Category → Brand → its tool card
	 * and stops (the 2026-10-14 shelf captures), and the 2026-10-14 recheck
	 * found the deployed rail listing four empty Power rows there. The empty
	 * tiers of a shelf that does carry power stay, disabled, and are asserted
	 * on the shop fixture below.
	 */
	public function test_rail_omits_power_when_no_product_carries_it(): void {
		$this->mock_selection_facts(
			array(
				71 => array(
					'brand'       => 'chint',
					'application' => 'commercial',
					'phase'       => 3,
				),
				72 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
				),
			)
		);
		$this->mock_catalog_query( null, array(), array(), array( 71, 72 ) );
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( '<summary class="filter-title">Brand</summary>', $rail );
		$this->assertStringNotContainsString( 'Power', $rail );
	}

	/**
	 * A shelf that carries power lists the fold with its empty tiers disabled
	 * — the live accessories rail prints "15 to 30 kW"/"Over 30 kW" as rows
	 * and leaves the two it has nothing in greyed (the 2026-10-14 shelf
	 * captures). The empty tiers are not links.
	 */
	public function test_rail_lists_power_with_its_empty_tiers_disabled(): void {
		$this->mock_selection_facts(
			array(
				81 => array(
					'brand'       => 'chint',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 25.0,
				),
				82 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$this->mock_catalog_query( null, array(), array(), array( 81, 82 ) );
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( '<summary class="filter-title">Power</summary>', $rail );
		// One product in "15 to 30 kW" and one in "Over 30 kW": the two empty
		// tiers still list, and they are not links.
		$this->assertStringContainsString( '<span class="filter-option is-disabled" aria-disabled="true">', $rail );
		$this->assertStringContainsString( '>15 to 30 kW</span></span><span class="filter-count">1</span></a>', $rail );
	}

	/**
	 * Name order follows the visible series titles after grouping, while
	 * Recommended retains the original family leads and product order.
	 */
	public function test_family_grid_rows_follow_the_requested_sort(): void {
		foreach ( array( 3, 7, 4, 5 ) as $id ) {
			$members = \in_array( $id, array( 3, 7 ), true ) ? array( 3, 7 ) : array( 4, 5 );
			WP_Mock::userFunction(
				'get_post_meta',
				array(
					'args'   => array( $id, '_tv_legacy_acf_json', true ),
					'return' => (string) json_encode(
						array(
							'product_series'  => 3 === $members[0] ? 'Zeta Series' : 'Alpha Series',
							'family_variants' => array_map( static fn( int $member ): array => array( 'id' => $member ), $members ),
						)
					),
				)
			);
		}
		$this->mock_selection_facts(
			array(
				4 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 60.0,
				),
				7 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 20.0,
				),
				3 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 1,
					'kw'          => 10.0,
				),
				5 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 125.0,
				),
			)
		);
		// The grid's own reads, bespoke: the shared archive fixture answers an
		// empty product list and stubs the row loop, and this test needs both
		// the products and the leads the loop hands the cards.
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		// No language layer: the family data is read off the products as they are.
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => '' ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'http://linker.test/products/' ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'no' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 7, 4, 3, 5 ) ) );
		// The archive's own "Recommended" order is newest first, and this
		// fixture's newest product is its title-last one: the two orders
		// differ, so the row leads below can only come out sorted if the
		// request's sort really reaches the grid.
		WP_Mock::userFunction(
			'get_post_time',
			array(
				'return' => static fn ( string $format, bool $gmt, int $id ): int => match ( $id ) {
					4 => 300,
					7 => 200,
					3 => 100,
					5 => 50,
					default => 0,
				},
			)
		);
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'exclude-from-catalog' => 99,
					'outofstock'           => 98,
				),
			)
		);
		$products = array();
		foreach ( array( 3, 7, 4, 5 ) as $id ) {
			$product = Mockery::mock( WC_Product::class );
			$product->shouldReceive( 'get_id' )->andReturn( $id );
			$product->shouldReceive( 'get_name' )->andReturn( 'Product ' . $id );
			$product->shouldReceive( 'is_purchasable' )->andReturn( false );
			$products[ $id ] = $product;
		}
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => static fn( int $id ) => $products[ $id ] ?? false ) );
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static fn ( int $id ): string => match ( $id ) {
					7 => 'GoodWe ESA GW20K-ETA-G20',
					4 => 'GoodWe GW60K-STS-G10',
					3 => 'GoodWe ESA GW10K-EHA-G20',
					5 => 'GoodWe ESA GW125/261-ESA-LCN-G10',
					default => '',
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn ( int $id ): WP_Post => new WP_Post( (object) array( 'ID' => $id ) ),
			)
		);
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => 0 ) );
		// Each row hands its lead to the card fragment; the order of those
		// calls is the order of the grid's cards.
		$leads = array();
		WP_Mock::userFunction(
			'setup_postdata',
			array(
				'return' => static function ( $post ) use ( &$leads ): bool {
					$leads[] = (int) $post->ID;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_reset_postdata' );
		$_GET = array(
			'brand' => 'goodwe',
			'sort'  => 'name',
		);

		( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_families();

		// Product-title order leads with 3, but the visible Alpha family (5)
		// precedes Zeta (3). Sorting rows must not replace either family lead.
		$this->assertSame( array( 5, 3 ), $leads );
		$leads        = array();
		$_GET['sort'] = 'recommended';
		( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_families();
		$this->assertSame( array( 4, 7 ), $leads );
	}

	/**
	 * The rail's Category section expands the branch the visitor is in with
	 * exactly the three rows the live all-in-one page prints under Commercial
	 * Storage, in that page's order: the Inverters row the display map adds
	 * (the term itself is flat, RAIL_GROUP_ROWS), then the two children the
	 * term tree holds, the current one marked. Other branches stay flat, and
	 * the section's own top-level Inverters row keeps serving
	 * /product-category/inverters/.
	 */
	public function test_category_section_expands_the_branch_with_the_live_rows(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
				32 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 30.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$aio       = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$battery   = $this->term( 453, 'Battery Systems', 'battery-systems', 451 );
		$ems       = $this->term( 454, 'EMS & Monitoring', 'ems-monitoring' );
		$this->mock_catalog_query(
			$aio,
			array( $inverters, $storage, $ems ),
			array(
				451 => array( $aio, $battery ),
			),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		// The group's three rows, in the live page's order, between the group's
		// own row and the next top-level category.
		$this->assertStringContainsString(
			'Commercial Storage</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/inverters/"><span>Inverters</span></a>'
			. '<a class="family-link family-link--child is-current" href="http://linker.test/product-category/all-in-one-systems/" aria-current="page"><span>All-in-One Systems</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/battery-systems/"><span>Battery Systems</span></a>'
			. '<a class="family-link" href="http://linker.test/product-category/ems-monitoring/"><span>EMS & Monitoring</span></a>',
			$rail
		);
		// Three rows, no more: the branch carries no other category.
		$this->assertSame( 3, substr_count( $rail, 'family-link--child' ) );
		// Inverters is where the live page prints it twice: the section's own
		// row, and the group's.
		$this->assertSame( 2, substr_count( $rail, '<span>Inverters</span>' ) );
	}

	/**
	 * The shop page enters no branch: every top-level category is a flat row,
	 * and the Commercial Storage display row stays out of it.
	 */
	public function test_the_shop_section_stays_flat(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$this->mock_catalog_query(
			null,
			array( $storage, $inverters ),
			array(),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringNotContainsString( 'family-link--child', $rail );
		$this->assertSame( 1, substr_count( $rail, '<span>Inverters</span>' ) );
	}

	/**
	 * The Inverters page keeps the Commercial Storage branch closed, the row
	 * itself marked current — the live Inverters rail is flat there too, the
	 * row the display map adds is not a child of the group.
	 */
	public function test_the_inverters_page_keeps_the_group_closed(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$ems       = $this->term( 454, 'EMS & Monitoring', 'ems-monitoring' );
		$this->mock_catalog_query(
			$inverters,
			array( $inverters, $storage, $ems ),
			array(),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		// The group's row sits between its neighbours, with nothing under it.
		$this->assertStringContainsString( 'Commercial Storage</span></a><a class="family-link" href="http://linker.test/product-category/ems-monitoring/"><span>EMS & Monitoring</span></a>', $rail );
		$this->assertStringNotContainsString( 'family-link--child', $rail );
	}

	/**
	 * The Accessories branch carries its own two children alone — the live
	 * accessories page's composition, no row from the Commercial Storage map.
	 */
	public function test_the_accessories_branch_carries_its_own_two_children(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$accessory = $this->term( 456, 'Accessories', 'accessories' );
		$meters    = $this->term( 457, 'Meters & Current Transformers', 'meters-current-transformers', 456 );
		$backup    = $this->term( 458, 'Backup Power', 'backup-power', 456 );
		$this->mock_catalog_query(
			$accessory,
			array( $inverters, $storage, $accessory ),
			array( 456 => array( $meters, $backup ) ),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( 'Accessories</span></a><a class="family-link family-link--child" href="http://linker.test/product-category/meters-current-transformers/"><span>Meters & Current Transformers</span></a><a class="family-link family-link--child" href="http://linker.test/product-category/backup-power/"><span>Backup Power</span></a>', $rail );
		$this->assertSame( 2, substr_count( $rail, 'family-link--child' ) );
	}

	/**
	 * The group's added row is the term's own twin in the language on
	 * display: the live Gewerbespeicher rail prints Wechselrichter above its
	 * two German children (the German capture of 2026-10-13).
	 */
	public function test_rail_group_row_is_the_german_twin_on_the_german_page(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$wechs     = $this->term( 581, 'Wechselrichter', 'wechselrichter' );
		$gewerbe   = $this->term( 587, 'Gewerbespeicher', 'gewerbespeicher' );
		$systeme   = $this->term( 599, 'All-in-One-Systeme', 'all-in-one-systeme', 587 );
		$batterien = $this->term( 601, 'Batteriesysteme', 'batteriesysteme', 587 );
		$en_group  = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$en_inv    = $this->term( 449, 'Inverters', 'inverters' );
		$this->mock_catalog_query(
			$systeme,
			array( $wechs, $gewerbe ),
			array( 587 => array( $systeme, $batterien ) ),
			array(),
			array(
				'inverters'          => array( $en_inv ),
				'commercial-storage' => array( $en_group ),
			),
			// The links the language layer carries: the German group answers
			// its English anchor, and the English Inverters term answers the
			// German page's Wechselrichter.
			static function ( int $id, string $language = '' ): int {
				if ( 587 === $id && 'en' === $language ) {
					return 451;
				}
				return 449 === $id ? 581 : 0;
			}
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString(
			'Gewerbespeicher</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/wechselrichter/"><span>Wechselrichter</span></a>'
			. '<a class="family-link family-link--child is-current" href="http://linker.test/product-category/all-in-one-systeme/" aria-current="page"><span>All-in-One-Systeme</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/batteriesysteme/"><span>Batteriesysteme</span></a>',
			$rail
		);
		$this->assertSame( 3, substr_count( $rail, 'family-link--child' ) );
	}

	/**
	 * A row the tree has since made a child keeps its single row: the map is
	 * a display addition, not a second copy of a child.
	 */
	public function test_rail_group_row_is_left_out_when_the_tree_makes_it_a_child(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters', 451 );
		$aio       = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$this->mock_catalog_query(
			$aio,
			array( $storage ),
			array(
				451 => array( $inverters, $aio ),
			),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertSame( 2, substr_count( $rail, 'family-link--child' ) );
		$this->assertSame( 1, substr_count( $rail, '<span>Inverters</span>' ) );
	}

	/**
	 * The mobile actions bar reads the applied count the live bar reads (1
	 * on a category) and carries the two tool entries beside the AI chip.
	 */
	public function test_actions_bar_carries_the_count_and_the_tool_entries(): void {
		$this->mock_catalog_query( $this->term( 456, 'Accessories', 'accessories' ) );
		$_GET = array();

		$bar = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_actions();

		$this->assertStringContainsString( 'id="product-filter-open"', $bar );
		$this->assertStringContainsString( 'data-linker-applied-filter-count>1</span>', $bar );
		$this->assertStringNotContainsString( 'Batch import', $bar );
		$this->assertStringNotContainsString( 'Nameplate photo', $bar );
	}

	/** Native Woo ordering and search forms retain selection, never the old page. */
	public function test_native_ordering_and_search_keep_selection_and_reset_paging(): void {
		$this->mock_catalog_query( null );
		WP_Mock::userFunction( 'selected', array( 'return' => static fn( string $actual, string $value ): string => $actual === $value ? ' selected="selected"' : '' ) );
		$_GET       = array(
			'q'            => 'ESA',
			'brand'        => 'goodwe',
			'sort'         => 'name',
			'product-page' => '3',
		);
		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$sort       = $shortcodes->products_sort();
		self::assertStringContainsString( 'class="wbsort woocommerce-ordering" method="get" action="http://linker.test/products/"', $sort );
		self::assertStringContainsString( 'class="select-dropdown orderby"', $sort );
		self::assertStringContainsString( 'name="q" value="ESA"', $sort );
		self::assertStringContainsString( 'name="brand" value="goodwe"', $sort );
		self::assertStringNotContainsString( 'name="product-page"', $sort );
		$search = $shortcodes->products_head();
		self::assertStringContainsString( 'name="sort" value="name"', $search );
		self::assertStringContainsString( 'name="brand" value="goodwe"', $search );
		self::assertStringNotContainsString( 'name="product-page"', $search );
	}

	/**
	 * The applied-filter chips: one pill per selected facet that removes it,
	 * one per set range bound, and the "Clear all" link; no selection, no
	 * chips.
	 */
	public function test_chips_strip_renders_a_chip_per_facet_and_clear_all(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $this->term( 449, 'Inverters', 'inverters' ) ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'return' => 'http://linker.test/product-category/inverters/',
			)
		);
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => array(
					(object) array(
						'slug' => 'goodwe',
						'name' => 'GoodWe',
					),
				),
			)
		);
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$_GET       = array();

		$this->assertSame( '', $shortcodes->products_chips() );

		$_GET                   = array(
			'brand'  => 'goodwe',
			'kw_min' => '5',
			'kw_max' => '20',
			'cbq'    => '1791',
		);
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/?brand=goodwe&kw_min=5&kw_max=20&cbq=1791';

		$chips = $shortcodes->products_chips();

		// The chips keep the live page's relative addresses (the one-argument
		// query helpers read the request) and drop the facet they remove.
		$this->assertStringContainsString( 'href="http://linker.test/product-category/inverters/?kw_min=5', $chips );
		$this->assertStringContainsString( '>GoodWe <span aria-hidden="true">&times;</span></a>', $chips );
		$this->assertStringContainsString( 'href="http://linker.test/product-category/inverters/?brand=goodwe', $chips );
		$this->assertStringContainsString( 'AC power 5&ndash;20 kW <span aria-hidden="true">&times;</span></a>', $chips );
		$this->assertStringContainsString( 'class="wbclear" href="http://linker.test/product-category/inverters/" rel="nofollow">Clear all</a>', $chips );
		$this->assertStringNotContainsString( 'product-page', $chips );

		$_GET['q']            = 'ESA & 5';
		$_GET['sort']         = 'name';
		$_GET['product-page'] = '3';
		$chips                = $shortcodes->products_chips();
		$this->assertStringContainsString( 'class="wbclear" href="http://linker.test/product-category/inverters/?q=ESA%20%26%205&sort=name" rel="nofollow">Clear all</a>', $chips );
		$this->assertStringNotContainsString( 'product-page', $chips );
	}

	/**
	 * The family card's title is the data's series label unless that label
	 * is the brand's own name: the live pages print "ESA Series" for the ESA
	 * family but the full model names for the SAJ CHS2 records whose series
	 * field holds "SAJ" (their brand).
	 *
	 * @covers \Linker\Commerce\Presentation\ProductShortcodes::series_title
	 */
	public function test_series_title_falls_back_to_the_model_when_the_series_is_the_brand(): void {
		$this->assertSame( 'ESA Series', ProductShortcodes::series_title( 'ESA Series', 'GoodWe', 'GoodWe ESA GW10K-ETA-G20' ) );
		$this->assertSame( 'GoodWe BAT-C', ProductShortcodes::series_title( 'GoodWe BAT-C', 'GoodWe', 'GoodWe GW261.2-BAT-LCD-G10' ) );
		$this->assertSame( 'SAJ CHS2-50K-T6-X', ProductShortcodes::series_title( 'SAJ', 'SAJ', 'SAJ CHS2-50K-T6-X' ) );
		$this->assertSame( 'SAJ CHS2-50K-T6-X', ProductShortcodes::series_title( '', 'SAJ', 'SAJ CHS2-50K-T6-X' ) );
	}

	/**
	 * The queried page, its German twin and that twin's permalink.
	 *
	 * @param int                $id           Queried page id.
	 * @param string             $permalink    Its permalink.
	 * @param array<string, int> $translations Language => translated id.
	 * @param string             $language     Current page language.
	 */
	private function page( int $id, string $permalink, array $translations, string $language = 'en' ): void {
		$page = new WP_Post(
			(object) array(
				'ID'        => $id,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $page ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $page ),
				'return' => $permalink,
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => $language ) );
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => function () {
					return 'http://linker.test' . $this->request_path();
				},
			)
		);
		foreach ( $translations as $language => $translated ) {
			WP_Mock::userFunction(
				'pll_get_post',
				array(
					'args'   => array( $id, $language ),
					'return' => $translated,
				)
			);
		}
	}

	/**
	 * A translated page's permalink.
	 *
	 * @param int    $id   Translated page id.
	 * @param string $link Its permalink.
	 */
	private function permalink( int $id, string $link ): void {
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $id ),
				'return' => $link,
			)
		);
	}

	/**
	 * The language half for `$lang`.
	 *
	 * @param string $lang Language code.
	 */
	private function url( string $lang ): string {
		$links  = new LanguageLinks();
		$method = new \ReflectionMethod( LanguageLinks::class, 'url' );
		return $method->invoke( $links, $lang );
	}

	/**
	 * The product page shortcodes over one product, with the WordPress and
	 * WooCommerce reads its view makes stubbed. Everything the page's data
	 * assembly asks for beyond the product's own fields is empty: the tests
	 * below read the availability dot, the feature band and the FAQ side
	 * panel, not the catalogue data around them.
	 *
	 * @param bool                 $in_stock Whether WooCommerce calls the product in stock.
	 * @param array<string, mixed> $acf      The product's legacy ACF JSON branches.
	 */
	private function pdp( bool $in_stock, array $acf = array() ): ProductShortcodes {
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' );
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( self::PDP );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW60K-STS-G10' );
		$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-GW60KSTSG10' );
		$product->allows( 'get_image_id' )->andReturn( 6503 );
		$product->allows( 'get_gallery_image_ids' )->andReturn( array( 6504, 6505 ) );
		$product->allows( 'get_short_description' )->andReturn( '<p>The intro.</p>' );
		$product->allows( 'get_description' )->andReturn( '' );
		$product->allows( 'get_price_html' )->andReturn( '<span>€ 100</span>' );
		$product->allows( 'get_permalink' )->andReturn( 'http://linker.test/product/goodwe-gw60k-sts-g10/' );
		$product->allows( 'get_attributes' )->andReturn( array() );
		$product->allows( 'get_parent_id' )->andReturn( 0 );
		$product->allows( 'is_in_stock' )->andReturn( $in_stock );

		// WP_Mock keeps the first responder of a function, and this helper may
		// run twice in one test (an in-stock product, then one that is not):
		// the reads go through the properties, so the second call re-mocks the
		// data and not the function.
		$this->pdp_product = $product;
		$this->pdp_acf     = $acf;

		WP_Mock::userFunction( 'wc_get_product', array( 'return' => fn ( int $id ) => self::PDP === $id ? $this->pdp_product : false ) );
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => self::PDP ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => fn ( int $id, string $key ) => match ( $key ) {
					'_tv_legacy_acf_json'       => (string) json_encode( $this->pdp_acf ),
					'_product_image_gallery'    => $this->pdp_gallery,
					default                     => '',
				},
			)
		);
		WP_Mock::userFunction(
			'wp_get_post_terms',
			array(
				'return' => fn ( int $id, string $taxonomy ) => 'pa_model' === $taxonomy
					? array(
						(object) array(
							'slug' => 'goodwe-gw60k-sts-g10',
							'name' => 'GW60K-STS-G10',
						),
					)
					: array(
						(object) array(
							'slug' => 'goodwe',
							'name' => 'GoodWe',
						),
					),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'GoodWe GW60K-STS-G10' ) );
		WP_Mock::userFunction( 'get_term_link', array( 'return' => 'http://linker.test/product-category/inverters/' ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => static fn ( string $page ): string => 'myaccount' === $page
					? 'http://linker.test/my-account/'
					: 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction( 'wc_get_checkout_url', array( 'return' => 'http://linker.test/proforma-request/' ) );
		WP_Mock::userFunction( 'wc_attribute_label', array( 'return' => static fn ( string $name ): string => $name ) );
		// The availability line's delivery note reads the product's own
		// shipping meta through Materials::logistics (no mode and no weight in
		// this fixture, so the note states the Proforma fallback).
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wc_string_to_bool', array( 'return' => static fn ( $value ) => in_array( $value, array( 'yes', 'true', '1' ), true ) ) );
		WP_Mock::userFunction( 'wc_price', array( 'return' => static fn ( float $amount ): string => '€' . number_format( $amount, 2 ) ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( $value ) => strip_tags( (string) $value ) ) );
		// Materials::gallery_ids's WordPress half and the image tags the two
		// shortcodes print (the URL names its attachment, so a test can tell
		// which picture the markup took).
		WP_Mock::userFunction( 'wp_get_attachment_image_url', array( 'return' => fn ( int $id ): string => $this->pdp_image_url( $id ) ) );
		WP_Mock::userFunction( 'wp_attachment_is_image', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_src', array( 'return' => fn ( int $id ): array => array( $this->pdp_image_url( $id ), 1024, 768, false ) ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_srcset', array( 'return' => '' ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_sizes', array( 'return' => '(max-width: 1024px) 100vw, 1024px' ) );

		// The selection facts' own stubs come after the pair above, so the
		// readers registered here are the ones that answer.
		$this->mock_selection_facts(
			array(
				self::PDP => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
				),
			)
		);

		return new ProductShortcodes( new ProductFilters(), $this->published_document_view() );
	}

	/** A single-product model is not prefixed with a fact, unlike a family picker. */
	public function test_single_product_card_model_uses_only_the_model(): void {
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => fn( int $id, string $taxonomy ) => match ( $taxonomy ) {
					'pa_model'       => '' === $this->pdp_model ? false : array(
						(object) array(
							'slug' => 'model',
							'name' => $this->pdp_model,
						),
					),
					'pa_brand'       => array(
						(object) array(
							'slug' => 'goodwe',
							'name' => 'GoodWe',
						),
					),
					'pa_application' => array( (object) array( 'slug' => 'commercial' ) ),
					'pa_phase'       => array( (object) array( 'slug' => 'three-phase' ) ),
					default          => false,
				},
			)
		);
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id, string $lang ): int => 'en' === $lang ? $id : 0 ) );
		$shortcodes = $this->pdp( true );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'no' ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'http://linker.test/product/goodwe-gw60k-sts-g10/' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( $value ): string => (string) json_encode( $value ) ) );
		$html = $shortcodes->products_card();
		$this->assertStringContainsString( '<small>Model</small><strong data-card-selection>GW60K-STS-G10</strong>', $html );
		$this->assertStringContainsString( '<dt>Communication</dt><dd>RS485</dd>', $html );

		$card = ( new ProductView() )->card_fields( self::PDP );
		$line = new \ReflectionMethod( ProductShortcodes::class, 'selection_line' );
		$this->assertSame( 'RS485 · GW60K-STS-G10', $line->invoke( $shortcodes, $this->pdp_product, $card ) );

		$this->pdp_model = '';

		$without_model = $shortcodes->products_card();
		$this->assertStringContainsString( 'GoodWe GW60K-STS-G10</a>', $without_model );
		$this->assertStringNotContainsString( 'data-linker-exact-product', $without_model );
	}

	/** The shared component carries semantic facts and a neutral visual fallback. */
	public function test_key_stats_emit_semantic_fact_keys_and_css_covers_the_component(): void {
		$html = $this->pdp( true )->pdp_key_stats();
		$this->assertStringContainsString( 'data-pdp-fact="interface"', $html );
		$this->assertStringContainsString( 'data-pdp-fact="weight"', $html );
		$this->assertStringNotContainsString( '<svg', $html );

		$css = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/windpress/pdp.css' );
		foreach ( array( 'ac_power', 'phase', 'mppt', 'usable_kwh', 'nominal_kwh', 'efficiency', 'batt_voltage', 'nom_voltage', 'ip', 'weight', 'dimensions', 'chemistry', 'charge_a', 'discharge_a', 'accuracy', 'ratio', 'interface', 'burden', 'devices', 'temp' ) as $key ) {
			$this->assertStringContainsString( 'data-pdp-fact="' . $key . '"', $css );
		}
		$this->assertMatchesRegularExpression( '/\.pdp-app-stat-icon\s*\{\s*--pdp-fact-icon:\s*url\(/', $css );
		preg_match( '/data-pdp-fact="weight"\][^{]*\{\s*--pdp-fact-icon:\s*([^;]+);/', $css, $weight );
		preg_match( '/data-pdp-fact="ac_power"\][^{]*\{\s*--pdp-fact-icon:\s*([^;]+);/', $css, $power );
		$this->assertNotEmpty( $weight[1] ?? '' );
		$this->assertNotEmpty( $power[1] ?? '' );
		$this->assertNotSame( $power[1], $weight[1] );
	}

	/** Distinct options keep their source text; a semicolon inside a note is not a separator. */
	public function test_key_stat_options_preserve_the_complete_source_facts(): void {
		$render = new \ReflectionMethod( ProductShortcodes::class, 'pdp_stat_value' );
		$value  = '1035 kg (57.3 kWh); 1145 kg (71.6 kWh); 1255 kg (85.9 kWh); 1365 kg (100.3 kWh)';
		$html   = $render->invoke( null, $value );
		$dom    = new \DOMDocument();
		$dom->loadHTML( '<div>' . $html . '</div>', LIBXML_NOERROR | LIBXML_NOWARNING );
		$parts = array();
		foreach ( $dom->getElementsByTagName( 'span' ) as $span ) {
			// phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- DOM's native property name.
			$parts[] = $span->textContent;
		}
		$this->assertSame(
			array( '1035 kg (57.3 kWh);', ' 1145 kg (71.6 kWh);', ' 1255 kg (85.9 kWh);', ' 1365 kg (100.3 kWh)' ),
			$parts
		);
		$this->assertSame( $value, strip_tags( $html ) );
		$this->assertSame( '15 kg', $render->invoke( null, '15 kg' ) );
		$this->assertSame( '15 kg (including base; without packaging)', $render->invoke( null, '15 kg (including base; without packaging)' ) );
		$with_note = '15 kg (including base; without packaging); 20 kg (alternate)';
		$marked    = $render->invoke( null, $with_note );
		$this->assertSame( $with_note, strip_tags( $marked ) );
		$this->assertSame( 2, substr_count( $marked, '<span class="pdp-spec-option">' ) );
		$this->assertSame( '15 kg; ', $render->invoke( null, '15 kg; ' ) );
		$this->assertSame( '15 kg (including base; 20 kg', $render->invoke( null, '15 kg (including base; 20 kg' ) );
	}

	/**
	 * The availability dot follows the product's own stock state: the base
	 * class for a product in stock, `is-wait` for one that is not (the live
	 * page's own two states; the shortcode printed `is-wait` on every product
	 * until 2026-10-16, so the dot could never leave its warn colour). The
	 * wording stays WooCommerce's own state text.
	 */
	public function test_the_availability_dot_follows_the_stock_state(): void {
		unset( $GLOBALS['product'] );
		$in_stock = $this->pdp( true )->pdp_availability();

		$this->assertStringContainsString( '<span class="pdp-dot"></span>', $in_stock );
		$this->assertStringContainsString( 'In stock', $in_stock );
		$this->assertStringNotContainsString( 'is-wait', $in_stock );

		$out_of_stock = $this->pdp( false )->pdp_availability();

		$this->assertStringContainsString( '<span class="pdp-dot is-wait"></span>', $out_of_stock );
		$this->assertStringContainsString( 'Currently unavailable', $out_of_stock );
	}

	/**
	 * The nameplate entry is gone: no button, no attribute, no document
	 * listener (owner ruling 2026-10-13: the nameplate chip is not
	 * delivered, so no event may promise it).
	 */
	public function test_the_project_choices_carry_the_three_stages_alone(): void {
		unset( $GLOBALS['product'] );
		$html = $this->pdp( true )->pdp_project_choices();

		$this->assertSame( 3, substr_count( $html, 'data-project-message=' ) );
		$this->assertStringContainsString( 'New system', $html );
		$this->assertStringNotContainsString( 'nameplate', $html );
		$this->assertStringNotContainsString( 'data-linker-assistant-open', $html );
	}

	/**
	 * The feature band's kicker names the product's series (`product_series`
	 * of the product's own ACF JSON, the field the catalogue cards read),
	 * and a product without one gets no kicker line.
	 */
	public function test_the_feature_band_takes_the_products_series_as_its_kicker(): void {
		unset( $GLOBALS['product'] );
		$html = $this->pdp(
			true,
			array(
				'product_series' => 'STS Series',
				'feature_cards'  => array(
					array(
						'feature_title' => 'Transfer in ≤ 4 ms.',
						'feature_body'  => 'On/off-grid transfer time is ≤ 4 ms.',
						'feature_image' => 4818,
					),
				),
			)
		)->pdp_features();

		$this->assertStringContainsString( '<p class="pdp-kicker">STS Series</p>', $html );
		$this->assertStringContainsString( 'Transfer in ≤ 4 ms.', $html );

		$without = $this->pdp(
			true,
			array(
				'feature_cards' => array(
					array(
						'feature_title' => 'Transfer in ≤ 4 ms.',
						'feature_body'  => 'On/off-grid transfer time is ≤ 4 ms.',
						'feature_image' => 4818,
					),
				),
			)
		)->pdp_features();

		$this->assertStringNotContainsString( 'pdp-kicker', $without );
	}

	/** The hidden secondary full image must not load ahead of a visitor's choice. */
	public function test_gallery_defers_the_hidden_secondary_image_and_keeps_the_choices(): void {
		unset( $GLOBALS['product'] );
		$pdp   = $this->pdp( true );
		$pair  = $pdp->pdp_gallery_pair();
		$thumb = $pdp->pdp_gallery_thumbs();

		$this->assertMatchesRegularExpression( '/class="pdp-gallery-main"[^>]*alt="GoodWe GW60K-STS-G10"(?![^>]*loading="lazy")/', $pair );
		$this->assertMatchesRegularExpression( '/class="pdp-gallery-secondary"[^>]*data-src="http:\/\/linker\.test\/uploads\/image-6504\.png"[^>]*>\s*<img[^>]*loading="lazy"/', $pair );
		$this->assertSame( 3, substr_count( $thumb, 'data-pdp-thumb' ) );
		$this->assertSame( 3, substr_count( $thumb, 'loading="lazy"' ) );
		$this->assertStringContainsString( 'data-src="http://linker.test/uploads/image-6504.png"', $thumb );
		$this->assertStringContainsString( 'data-src="http://linker.test/uploads/image-6505.png"', $thumb );

		$this->pdp_gallery = '';
		$this->assertStringNotContainsString( 'pdp-gallery-secondary', $pdp->pdp_gallery_pair() );
		$this->assertSame( '', $pdp->pdp_gallery_thumbs() );
	}

	/**
	 * The FAQ side panel repeats no picture from the gallery above it: it
	 * takes the gallery's last id (the featured image and the first gallery
	 * picture are the pair the page's top shows), and a product whose gallery
	 * holds nothing beyond the featured picture gets no panel.
	 */
	public function test_the_faq_side_panel_takes_the_gallerys_last_picture(): void {
		unset( $GLOBALS['product'] );

		// The fixture's own gallery: 6503 is the featured image, 6504 and 6505
		// the editor's list (the real product's data). The panel takes the
		// last id, so it repeats neither the main picture nor the second one.
		$html = $this->pdp( true )->pdp_faq_side();

		$this->assertStringContainsString( '<div class="pdp-faq-side">', $html );
		$this->assertStringContainsString( 'image-6505.png', $html );
		$this->assertStringNotContainsString( 'image-6503.png', $html );
		$this->assertStringNotContainsString( 'image-6504.png', $html );

		// A product whose gallery holds the featured picture alone: no panel,
		// and the block stays one column.
		$this->pdp_gallery = '';
		$this->assertSame( '', $this->pdp( true )->pdp_faq_side() );
	}

	/**
	 * Encode existing native query leaves without collapsing nested arrays.
	 *
	 * @param array<mixed>|string $value Parsed native query value.
	 * @return array<mixed>|string
	 */
	private static function encode_query_value( array|string $value ): array|string {
		if ( is_array( $value ) ) {
			return array_map( self::encode_query_value( ... ), $value );
		}
		return rawurlencode( $value );
	}
	/** Current document data wins over retained rows; an empty current list stays empty. */
	public function test_product_documents_consume_the_current_assembly_once(): void {
		unset( $GLOBALS['product'] );
		$this->pdp(
			true,
			array(
				'downloads' => array(
					array(
						'download_file'     => 6503,
						'download_title'    => 'Retained document title',
						'download_type'     => 'document',
						'download_language' => 'EN',
					),
				),
			)
		);
		WP_Mock::userFunction( 'wp_get_attachment_url' )->andReturn( 'http://linker.test/retained.pdf' );
		$documents = array(
			array(
				'title'    => 'Current manual',
				'url'      => 'http://linker.test/manual.pdf',
				'type'     => 'manual',
				'role'     => 'document',
				'language' => 'en',
			),
			array(
				'title'    => 'Current datasheet',
				'url'      => 'http://linker.test/datasheet.pdf',
				'type'     => 'datasheet',
				'role'     => 'document',
				'language' => 'DE',
			),
			array(
				'title'    => 'Current warranty',
				'url'      => 'http://linker.test/warranty.pdf',
				'type'     => 'warranty',
				'role'     => 'document',
				'language' => 'MULTI',
			),
		);
		$reads     = 0;
		$view      = new ProductView(
			new CommerceState(),
			static function ( int $id ) use ( &$documents, &$reads ): array {
				if ( self::PDP !== $id ) {
					return array();
				}
				++$reads;
				return $documents;
			}
		);
		$html      = ( new ProductShortcodes( new ProductFilters(), $view ) )->pdp_downloads();
		$this->assertStringContainsString( 'Current manual', $html );
		$this->assertStringContainsString( 'Manual · PDF · EN', $html );
		$this->assertStringContainsString( 'Warranty · PDF · Multilingual', $html );
		$this->assertStringNotContainsString( 'retained.pdf', $html );
		$this->assertLessThan( strpos( $html, 'Current manual' ), strpos( $html, 'Current datasheet' ) );
		$this->assertLessThan( strpos( $html, 'Current warranty' ), strpos( $html, 'Current manual' ) );
		$this->assertSame( 1, $reads, 'Reuse the current page assembly instead of reading documents twice.' );

		$documents = array();
		$empty     = ( new ProductShortcodes( new ProductFilters(), $view ) )->pdp_downloads();
		$this->assertStringContainsString( 'No documents are available for this product.', $empty );
		$this->assertStringNotContainsString( 'pdp-doc"', $empty );
		$this->assertStringNotContainsString( 'retained.pdf', $empty );
		$this->assertSame( 2, $reads );
	}

	/**
	 * The live ETR relationship has partial manual evidence, not list approval.
	 * Preserve a genuinely listed card while rejecting unestablished statuses.
	 */
	public function test_pairing_status_preserves_the_recorded_evidence_boundary(): void {
		$registry = \Linker\Commerce\Products\Materials::registry();
		$rows     = $registry['materials']['mat_goodwe_gw125k_etr_g10']['technical']['relationships'];
		$method   = new \ReflectionMethod( ProductShortcodes::class, 'pairing_status' );
		foreach ( $rows as $row ) {
			$expected = 'one_way' === $row['status'] ? 'Partially documented' : 'Documented by GoodWe';
			$this->assertSame( $expected, $method->invoke( null, $row, 'en' ) );
		}
		$eha_rows = $registry['materials']['mat_goodwe_gw10k_eha_g20']['technical']['relationships'];
		foreach ( $eha_rows as $row ) {
			$this->assertSame( 'Documented by GoodWe', $method->invoke( null, $row, 'en' ) );
		}
		$this->assertSame( 'Compatibility documented', $method->invoke( null, array( 'status' => 'listed' ), 'en' ) );
		$contract = \Linker\Commerce\Products\Materials::contract();
		foreach ( $contract['cells'] as $cell ) {
			if ( 'one_way' === $cell['status'] ) {
				$this->assertSame( 'Partially documented', $method->invoke( null, $cell, 'en' ) );
			}
		}
		foreach ( array(
			array(),
			array( 'status' => 'not_listed' ),
			array(
				'status'    => 'unknown',
				'listed_by' => 'GoodWe',
			),
		) as $row ) {
			$this->assertSame( 'Compatibility information unavailable', $method->invoke( null, $row, 'en' ) );
		}
	}


	/**
	 * The tool row stays three cells. The configurator action lives in the project check.
	 */
	public function test_product_tools_stay_three_and_the_project_check_carries_the_product(): void {
		unset( $GLOBALS['product'] );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction( 'has_filter' )->andReturn( true );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'return' => new \WP_Post( (object) array( 'ID' => 3302 ) ),
			)
		);
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'http://linker.test/solution-configurator/' ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id, string $lang ): int => 'en' === $lang ? $id : 0 ) );
		$shortcodes = $this->pdp( true );
		$tools      = $shortcodes->pdp_tools();
		$dom        = new \DOMDocument();
		$dom->loadHTML( '<?xml encoding="utf-8"><div id="tools">' . $tools . '</div>', LIBXML_NOERROR | LIBXML_NOWARNING );
		$xpath      = new \DOMXPath( $dom );
		$tool_nodes = $xpath->query( '//*[@id="tools"]//*[contains(concat(" ", normalize-space(@class), " "), " pdp-tool ")]' );
		$planner    = $xpath->query( '//*[@id="tools"]//a[contains(@href, "solution-configurator")]' );
		$this->assertSame( 3, $tool_nodes instanceof \DOMNodeList ? $tool_nodes->length : -1 );
		$this->assertSame( 0, $planner instanceof \DOMNodeList ? $planner->length : -1 );
		$this->assertStringContainsString( 'Compare', $tools );
		$this->assertStringContainsString( 'Ask Genie', $tools );
		$this->assertStringContainsString( 'Documents', $tools );

		$action = $shortcodes->pdp_configurator();
		$dom->loadHTML( '<?xml encoding="utf-8"><div id="action">' . $action . '</div>', LIBXML_NOERROR | LIBXML_NOWARNING );
		$xpath = new \DOMXPath( $dom );
		$links = $xpath->query( '//*[@id="action"]//a' );
		$this->assertSame( 1, $links instanceof \DOMNodeList ? $links->length : -1 );
		$link = $links instanceof \DOMNodeList ? $links->item( 0 ) : null;
		$this->assertInstanceOf( \DOMElement::class, $link );
		$this->assertSame( 'pdp-project-choice', $link->getAttribute( 'class' ) );
		$this->assertSame( 'http://linker.test/solution-configurator/?step=equipment&product_id=6530', $link->getAttribute( 'href' ) );
		// phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- DOM's native property name.
		$this->assertSame( 'Open the Solution Configurator', $link->textContent );
		$this->assertStringNotContainsString( 'pdp-tool', $action );

		foreach ( array(
			dirname( __DIR__, 4 ) . '/content/livecanvas/single_product.html',
			dirname( __DIR__, 4 ) . '/content/livecanvas/de/single_product.html',
		) as $template ) {
			$html     = (string) file_get_contents( $template );
			$region   = strpos( $html, 'class="pdp-project-check"' );
			$choices  = strpos( $html, 'class="pdp-project-choices"' );
			$entry    = strpos( $html, '[linker_pdp_configurator]' );
			$tools_at = strpos( $html, 'class="pdp-product-tools"' );
			$this->assertNotFalse( $region );
			$this->assertNotFalse( $choices );
			$this->assertNotFalse( $entry );
			$this->assertGreaterThan( $region, $choices );
			$this->assertGreaterThan( $choices, $entry );
			$this->assertLessThan( $entry, $tools_at );
			$this->assertStringNotContainsString( '[linker_pdp_configurator]', substr( $html, (int) $tools_at, (int) $choices - (int) $tools_at ) );
			$this->assertSame( 0, substr_count( $html, 'class="pdp-tool"' ) );
		}
	}
}

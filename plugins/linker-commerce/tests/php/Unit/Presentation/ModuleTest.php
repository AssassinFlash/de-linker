<?php
/**
 * Tests for the presentation module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Presentation\BlogShortcodes;
use Linker\Commerce\Presentation\ComparePage;
use Linker\Commerce\Presentation\FamilyNavigation;
use Linker\Commerce\Presentation\LibraryPage;
use Linker\Commerce\Presentation\JournalTitles;
use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Presentation\Module;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Presentation\WindPress;
use Linker\Commerce\Presentation\WindPressPageStyles;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Storefront\SocialCards;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Mock\Matcher\AnyInstance;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Presentation\Module
 */
final class ModuleTest extends TestCase {

	/** Home draws the hero title and button in additional font weights on its first paint. */
	public function test_home_preloads_the_first_paint_font_weights(): void {
		WP_Mock::userFunction( 'plugins_url' )->andReturn( '/fonts/' );
		WP_Mock::userFunction( 'is_front_page' )->andReturn( true );
		WP_Mock::userFunction( 'is_product' )->andReturn( false );
		WP_Mock::userFunction( 'wp_get_upload_dir' )->andReturn( array( 'basedir' => __DIR__ ) );
		$resources = ( new Module( new Shortcodes(), new LoginGate(), new WindPress() ) )->preload_resources( array() );
		$fonts     = array_map( 'basename', array_column( $resources, 'href' ) );
		$this->assertSame( array( 'plus-jakarta-sans-400.woff2', 'plus-jakarta-sans-500.woff2', 'plus-jakarta-sans-600.woff2', 'plus-jakarta-sans-700.woff2' ), $fonts );
	}

	/** Local Site Kit entry points carry their bundled fingerprint in the cache key. */
	public function test_site_kit_script_versions(): void {
		$directory = 'https://linker.test/wp-content/plugins/google-site-kit/dist/assets/js/';
		WP_Mock::userFunction( 'plugins_url' )->with( 'google-site-kit/dist/assets/js/' )->andReturn( $directory );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'add_query_arg' )->andReturnUsing( static fn ( string $key, string $value, string $url ): string => $url . '?' . $key . '=' . $value );
		$module = new Module( new Shortcodes(), new LoginGate(), new WindPress() );
		foreach ( array(
			'googlesitekit-consent-mode'                   => '755f1678e260138d789e',
			'googlesitekit-events-provider-content-events' => '6b04077d00f0d606ba42',
			'googlesitekit-events-provider-woocommerce'    => '86c5a3ff303665006998',
		) as $handle => $hash ) {
			$src = $directory . $handle . '-' . $hash . '.js';
			$this->assertSame( $src . '?ver=' . $hash, $module->version_fingerprinted_scripts( $src, $handle ) );
			$versioned = $src . '?ver=existing';
			$this->assertSame( $versioned, $module->version_fingerprinted_scripts( $versioned, $handle ) );
			$third_party = str_replace( 'linker.test', 'example.org', $src );
			$this->assertSame( $third_party, $module->version_fingerprinted_scripts( $third_party, $handle ) );
		}
	}

	/**
	 * Only the rendered main picture participates in responsive image preloading.
	 *
	 * @dataProvider gallery_preloads
	 * @param bool                 $is_pdp  Whether Woo is rendering a product.
	 * @param string               $gallery Actual LiveCanvas gallery markup.
	 * @param array<string,string> $hint    The selected image resource, or no hint.
	 */
	public function test_preloads_only_the_rendered_main_image( bool $is_pdp, string $gallery, array $hint ): void {
		WP_Mock::userFunction( 'plugins_url' )->andReturn( 'https://linker.test/fonts/' );
		WP_Mock::userFunction( 'is_front_page' )->andReturn( false );
		WP_Mock::userFunction( 'is_product' )->andReturn( $is_pdp );
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- LiveCanvas's rendered dynamic template.
		$GLOBALS['lc_main_html'] = '<img class="pdp-brand-logo" src="/logo.png">' . $gallery;
		try {
			$resources = ( new Module( new Shortcodes(), new LoginGate(), new WindPress() ) )->preload_resources( array() );
			$images    = array_values( array_filter( $resources, static fn ( array $entry ): bool => 'image' === $entry['as'] ) );
			$this->assertSame( $hint ? array( $hint ) : array(), $images );
		} finally {
			unset( $GLOBALS['lc_main_html'] );
		}
	}

	/** WordPress attachment candidates, gallery fallback and empty galleries.
	 *
	 * @return array<string,array{bool,string,array<string,string>}>
	 */
	public static function gallery_preloads(): array {
		return array(
			'responsive featured image' => array(
				true,
				'<img class="pdp-gallery-main" src="/original.jpg" srcset="/small.jpg 300w, /original.jpg 800w" sizes="(max-width: 768px) 100vw, 667px">',
				array(
					'as'            => 'image',
					'href'          => '/original.jpg',
					'fetchpriority' => 'high',
					'imagesrcset'   => '/small.jpg 300w, /original.jpg 800w',
					'imagesizes'    => '(max-width: 768px) 100vw, 667px',
				),
			),
			'first gallery attachment'  => array(
				true,
				'<img class="pdp-gallery-main" src="/gallery-only.jpg" sizes="100vw">',
				array(
					'as'            => 'image',
					'href'          => '/gallery-only.jpg',
					'fetchpriority' => 'high',
				),
			),
			'empty product gallery'     => array( true, '<div class="pdp-gallery-empty">Photography in preparation</div>', array() ),
			'other page'                => array( false, '<img class="pdp-gallery-main" src="/embedded.jpg">', array() ),
		);
	}

	/** The standalone native draft also receives the saved-quantity guard. */
	public function test_cart_loads_account_interactions(): void {
		WP_Mock::userFunction( 'is_account_page' )->andReturn( false );
		WP_Mock::userFunction( 'is_checkout' )->andReturn( false );
		WP_Mock::userFunction( 'is_cart' )->andReturn( true );
		WP_Mock::userFunction( 'is_wc_endpoint_url' )->andReturn( false );
		WP_Mock::userFunction( 'plugins_url' )->andReturn( 'https://example.test/assets/' );
		WP_Mock::userFunction( 'wp_enqueue_script' )->once()->with(
			'linker-account-ui',
			'https://example.test/assets/account-ui.js',
			array(),
			(string) filemtime( dirname( __DIR__, 4 ) . '/assets/account-ui.js' ),
			true
		);
		( new Module( new Shortcodes(), new LoginGate(), new WindPress() ) )->enqueue_account_scripts();
		$this->assertConditionsMet();
	}

	/**
	 * The module's hooks, and no other: the shortcodes of the three page
	 * families (the product and checkout shortcodes, the comparison page's
	 * table and chip, the library page's two registers), the login gate's
	 * filter, the WindPress provider, and the comparison page's address
	 * normalizer, selection script and chip. WP_Mock's strict mode fails the
	 * run on any further hook — there is deliberately no body_class filter
	 * left, because the sf-account-page body class had no consumer after the
	 * storefront CSS was retired.
	 */
	public function test_register_adds_exactly_the_module_hooks(): void {
		$shortcodes = new Shortcodes();
		$gate       = new LoginGate();
		$windpress  = new WindPress();
		$compare    = new ComparePage();
		$library    = new LibraryPage();
		$account    = new AccountTemplates();
		$blog       = new BlogShortcodes();
		$products   = new ProductShortcodes(
			new ProductFilters(),
			new ProductView(),
		);
		$module     = new Module( $shortcodes, $gate, $windpress, $products, $compare, $library, $account, $blog );

		// Data shortcodes across the product, checkout, comparison,
		// library, account and blog families, including the product's configurator
		// entry and the FAQ section's scoped rows.
		WP_Mock::userFunction( 'add_shortcode', array( 'times' => 87 ) );
		WP_Mock::expectFilterAdded( 'woocommerce_loop_add_to_cart_args', array( $products, 'loop_cart_attributes' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $account, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'pre_get_document_title', array( $blog, 'empty_search_title' ), 60 );
		WP_Mock::expectActionAdded( 'template_redirect', array( $blog, 'redirect_chester_archive' ), -1 );
		WP_Mock::expectFilterAdded( 'seopress_disable_archives_redirect_url', array( $blog, 'archive_destination' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $account, 'orders_query' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/integration/livecanvas/compile:get_contents.render', array( $windpress, 'render_raw' ), 10, 2 );
		WP_Mock::expectFilterAdded(
			'wp_get_attachment_image_attributes',
			array( $products, 'related_image_attributes' ),
			10,
			3,
		);
		WP_Mock::expectActionAdded( 'template_redirect', array( $compare, 'canonical_address' ), 5 );
		WP_Mock::expectActionAdded( 'wp_head', array( $library, 'print_schema' ) );
		$families     = new AnyInstance( FamilyNavigation::class );
		$family_hooks = array(
			array( 'action', 'template_redirect', 'redirect', 0 ),
			array( 'filter', 'seopress_titles_canonical', 'canonical', 10 ),
			array( 'filter', 'pll_translation_url', 'translated_page', 55 ),
			array( 'filter', 'seopress_titles_title', 'paged_title', 50 ),
			array( 'filter', 'pre_get_document_title', 'paged_title', 50 ),
			array( 'filter', 'pll_rel_hreflang_attributes', 'hreflangs', 20 ),
		);
		$registered   = array_fill_keys( array_column( $family_hooks, 1 ), 0 );
		foreach ( $family_hooks as list( $type, $hook, $method, $priority ) ) {
			$responder = WP_Mock::onHookAdded( $hook, $type )->with( array( $families, $method ), $priority, 'pll_translation_url' === $hook ? 2 : 1 );
			self::assertInstanceOf( \WP_Mock\HookedCallbackResponder::class, $responder );
			$responder->perform(
				static function () use ( &$registered, $hook ): void {
					++$registered[ $hook ];
				}
			);
		}
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $compare, 'assets' ) );
		WP_Mock::expectActionAdded( 'wp_footer', array( $compare, 'standing_chip' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_product_scripts' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_account_scripts' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( \Linker\Commerce\Presentation\LegalNavigation::class, 'enqueue' ) );

		WP_Mock::expectActionAdded( 'init', array( JournalTitles::class, 'register' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $blog, 'enqueue_author_dialog' ) );
		WP_Mock::expectFilterAdded( 'lc_modify_header_content', array( $module, 'home_header_menu' ) );
		WP_Mock::expectFilterAdded( 'wp_preload_resources', array( $module, 'preload_resources' ) );
		WP_Mock::expectFilterAdded( 'script_loader_src', array( $module, 'version_fingerprinted_scripts' ), 20, 2 );
		WP_Mock::expectActionAdded( 'after_setup_theme', array( $module, 'disable_woo_product_gallery' ), 99 );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'trim_woo_assets' ), 31 );
		$this->expect_action_on_any( 'a!windpress/core/runtime:enqueue_css_cache.before', WindPressPageStyles::class, 'before_cache' );
		$this->expect_action_on_any( 'a!windpress/core/runtime:enqueue_css_cache.after', WindPressPageStyles::class, 'after_cache' );
		$this->expect_action_on_any( 'a!windpress/core/runtime:enqueue_play_cdn.before', WindPressPageStyles::class, 'before_cache' );
		$this->expect_action_on_any( 'a!windpress/core/runtime:enqueue_play_cdn.after', WindPressPageStyles::class, 'after_cache' );
		$cards = new AnyInstance( SocialCards::class );
		WP_Mock::expectFilterAdded( 'seopress_social_twitter_card_site', '__return_empty_string' );
		foreach ( array(
			'seopress_social_og_type'              => 'open_graph_type',
			'site_icon_meta_tags'                  => 'site_icons',
			'seopress_social_twitter_card_summary' => 'summary',
			'seopress_social_og_thumb'             => 'open_graph',
			'seopress_social_twitter_card_thumb'   => 'twitter_image',
			'seopress_social_twitter_card_creator' => 'creator',
		) as $hook => $method ) {
			// @phpstan-ignore argument.type (WP_Mock matches array callbacks with AnyInstance.)
			WP_Mock::expectFilterAdded( $hook, array( $cards, $method ), 10, in_array( $method, array( 'summary', 'creator' ), true ) ? 0 : 1 );
		}
		$module->register();
		self::assertSame( array_fill_keys( array_column( $family_hooks, 1 ), 1 ), $registered );

		$this->assertConditionsMet();
	}
}

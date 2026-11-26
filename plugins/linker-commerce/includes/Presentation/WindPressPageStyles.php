<?php
/**
 * WindPress volume styles used by individual storefront and editorial surfaces.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use WP_Post;

/** Print the current surfaces' styles in the published volume's cascade order. */
final class WindPressPageStyles {

	/** Volume imports that precede the shared account, Genie and control overrides. */
	private const BEFORE = array(
		'account.css'            => 'account',
		'auth.css'               => 'forms',
		'faq.css'                => 'library',
		'pdp.css'                => 'product',
		'model-links.css'        => 'model_links',
		'products-mounts.css'    => 'catalogue',
		'products.css'           => 'catalogue',
		'storefront.css'         => 'storefront',
		'blog.css'               => 'article',
		'contact-card.css'       => 'contact',
		'contact-invitation.css' => 'article',
		'blog-category.css'      => 'category',
		'blog-index.css'         => 'blog',
		'blog-search.css'        => 'search',
	);

	/** Volume imports following the shared control styles. */
	private const AFTER = array(
		'journal.css'              => 'journal',
		'service-intro.css'        => 'services',
		'marketing-rhythm.css'     => 'marketing',
		'homepage-focus.css'       => 'home',
		'homepage-readability.css' => 'home',
		'planner.css'              => 'planner',
		'contact-journal.css'      => 'contact',
		'planner-equipment.css'    => 'planner',
		'planner-report.css'       => 'planner',
		'planner-site-energy.css'  => 'planner',
		'home-configurator.css'    => 'showcase',
		'not-found.css'            => 'not_found',
		'roof-studio.css'          => 'planner',
	);

	/**
	 * Active surfaces on this request.
	 *
	 * @var array<string,bool>|null
	 */
	private ?array $surfaces = null;

	/** All page styles published by the volume, in import order.
	 *
	 * @return list<string>
	 */
	public static function filenames(): array {
		return array_merge( array_keys( self::BEFORE + self::AFTER ), array( 'planner-maplibre.css' ) );
	}

	/**
	 * Versioned map styles published alongside the volume, requested when the map opens.
	 */
	public static function map_style_url(): string {
		$uploads  = wp_get_upload_dir();
		$relative = '/windpress/cache/linker/planner-maplibre.css';
		$file     = $uploads['basedir'] . $relative;
		return $uploads['baseurl'] . $relative . ( is_file( $file ) ? '?ver=' . filemtime( $file ) : '' );
	}

	/** Both the cached frontend and LiveCanvas's live compiler use the same page styles. */
	public function register(): void {
		add_action( 'a!windpress/core/runtime:enqueue_css_cache.before', array( $this, 'before_cache' ) );
		add_action( 'a!windpress/core/runtime:enqueue_css_cache.after', array( $this, 'after_cache' ) );
		add_action( 'a!windpress/core/runtime:enqueue_play_cdn.before', array( $this, 'before_cache' ) );
		add_action( 'a!windpress/core/runtime:enqueue_play_cdn.after', array( $this, 'after_cache' ) );
	}

	/** Before shared control overrides. */
	public function before_cache(): void {
		$this->print_styles( self::BEFORE );
	}

	/** After shared control overrides. */
	public function after_cache(): void {
		$this->print_styles( self::AFTER );
	}

	/**
	 * Enqueue and print the active volume styles in this phase.
	 *
	 * @param array<string,string> $files Volume filenames and their surfaces.
	 */
	private function print_styles( array $files ): void {
		$this->surfaces ??= self::surfaces();
		$uploads          = wp_get_upload_dir();
		$handles          = array();
		foreach ( $files as $file => $surface ) {
			if ( ! $this->surfaces[ $surface ] ) {
				continue;
			}
			$relative = '/windpress/cache/linker/' . $file;
			$handle   = 'linker-volume-' . basename( $file, '.css' );
			wp_enqueue_style( $handle, $uploads['baseurl'] . $relative, array(), (string) filemtime( $uploads['basedir'] . $relative ) );
			$handles[] = $handle;
		}
		if ( array() !== $handles ) {
			wp_print_styles( $handles );
		}
	}

	/**
	 * LiveCanvas resolves its assigned template, including language twins, before wp_head.
	 * The page's own content also covers directly embedded shortcodes on ordinary pages/posts.
	 *
	 * @return array<string,bool>
	 */
	private static function surfaces(): array {
		$post     = get_queried_object();
		$content  = $post instanceof WP_Post ? $post->post_content : '';
		$content .= "\n" . ( $GLOBALS['lc_main_html'] ?? '' );
		preg_match_all( '/\bid\s*=\s*(["\'])([\w-]+)\1/i', $content, $matches );
		$ids = array_fill_keys( $matches[2], true );

		$catalogue = ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) || isset( $ids['linker-products'] ) || str_contains( $content, '[linker_products_' );
		$product   = is_singular( 'product' ) || isset( $ids['tv-storefront-pdp'] ) || str_contains( $content, '[linker_pdp_' );
		$cart      = ( function_exists( 'is_cart' ) && is_cart() ) || isset( $ids['tv-storefront-cart'] ) || str_contains( $content, '[woocommerce_cart' );
		$inquiry   = ( function_exists( 'is_checkout' ) && is_checkout() ) || isset( $ids['tv-woo-b2b-checkout'] ) || str_contains( $content, '[woocommerce_checkout' ) || str_contains( $content, '[linker_inquiry_' );
		$account   = ( function_exists( 'is_account_page' ) && is_account_page() ) || isset( $ids['container-content-account'] ) || str_contains( $content, '[woocommerce_my_account' ) || str_contains( $content, '[linker_account_' );
		$compare   = isset( $ids['linker-compare'] ) || isset( $ids['container-content-compare'] ) || str_contains( $content, '[linker_compare_' );
		$contact   = isset( $ids['tv-contact-v1'] ) || str_contains( $content, '[linker_contact_form' );
		$home      = is_front_page() || isset( $ids['home-a'] );
		$blog      = is_home() || isset( $ids['tv-blog-index-v1'] );
		$category  = is_category() || isset( $ids['tv-blog-category-v1'] );
		$search    = is_search() || isset( $ids['tv-blog-search-v1'] );
		$services  = isset( $ids['service-redesign'] );

		return array(
			'account'     => $account,
			'forms'       => $account || $cart || $inquiry || $contact || str_contains( $content, 'linker-gate' ) || str_contains( $content, '[linker_form_assistant' ),
			'library'     => isset( $ids['linker-faq-page'] ) || str_contains( $content, '[linker_library_' ),
			'product'     => $product,
			'model_links' => $product || str_contains( $content, '[linker_solution_products' ),
			'catalogue'   => $catalogue,
			'storefront'  => $catalogue || $product || $cart || $inquiry || $account || $compare,
			'article'     => is_singular( 'post' ) || isset( $ids['tv-blog-single-v1'] ) || str_contains( $content, '[linker_blog_' ),
			'contact'     => $contact,
			'category'    => $category,
			'blog'        => $blog,
			'search'      => $search,
			'journal'     => $blog || $category || $search,
			'services'    => $services || isset( $ids['installer-journal'] ) || isset( $ids['tv-utility-page-v1'] ),
			'marketing'   => $home || $services || array() !== array_intersect( array_keys( $ids ), array( 'installer-journal', 'about-journal', 'tv-rs-page-v1', 'tv-cs-page-v1', 'tv-cp-page-v1', 'tv-solution-v1', 'tv-solutions-developers-v1', 'tv-utility-page-v1' ) ),
			'home'        => $home,
			'showcase'    => $home || isset( $ids['configurator-showcase'] ),
			'planner'     => 1 === preg_match( '/<(?:section|div)\b[^>]*\sdata-linker-planner(?=[\s=\/>])|(?<!\[)\[(?:linker_planner|linker_configurator)(?=[\s\/\]])/i', $content ),
			'not_found'   => is_404() || isset( $ids['tv-404-v1'] ),
		);
	}
}

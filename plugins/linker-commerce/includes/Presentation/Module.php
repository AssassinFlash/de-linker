<?php
/**
 * Hooks of the presentation module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Account\AuthTemplates;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Storefront\SocialCards;

/**
 * Shortcodes, the catalogue shortcodes, the empty Proforma-request gate, the
 * comparison page, the document library page and WindPress.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Shortcodes             $shortcodes B2B shortcodes.
	 * @param LoginGate              $gate       Empty Proforma-request page.
	 * @param WindPress              $windpress  Compile provider.
	 * @param ProductShortcodes|null $products   The replica product shortcodes; built
	 *                                           from the kept data layers when omitted.
	 * @param ComparePage            $compare    The comparison page and its chip (#66).
	 * @param LibraryPage            $library    The document library page (#66).
	 * @param AccountTemplates       $account    Account content data for LC.
	 * @param BlogShortcodes         $blog       The blog single template's data.
	 */
	public function __construct(
		private readonly Shortcodes $shortcodes,
		private readonly LoginGate $gate,
		private readonly WindPress $windpress,
		private readonly ?ProductShortcodes $products = null,
		private readonly ComparePage $compare = new ComparePage(),
		private readonly LibraryPage $library = new LibraryPage(),
		private readonly AccountTemplates $account = new AccountTemplates(),
		private readonly BlogShortcodes $blog = new BlogShortcodes()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		$this->shortcodes->register();
		( new AccountLinks() )->register();
		LegalNavigation::register();
		( new SupplyBrands() )->register();
		( new SocialCards() )->register();
			( $this->products ?? new ProductShortcodes( new ProductFilters(), new ProductView() ) )->register();
		$this->gate->register();
		$this->windpress->register();
		( new WindPressPageStyles() )->register();
		$this->compare->register();
		$this->library->register();
		( new CompatibilityMatrixPage() )->register();
		$this->account->register();
		$this->blog->register();
		add_filter( 'lc_modify_header_content', array( $this, 'home_header_menu' ) );
		add_filter( 'wp_preload_resources', array( $this, 'preload_resources' ) );
		add_filter( 'script_loader_src', array( $this, 'version_fingerprinted_scripts' ), 20, 2 );
		add_action( 'after_setup_theme', array( $this, 'disable_woo_product_gallery' ), 99 );
		add_action( 'wp_enqueue_scripts', array( $this, 'trim_woo_assets' ), 31 );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_product_scripts' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_account_scripts' ) );
	}

	/**
	 * Size the Home navigation as its markup arrives, before the hero is painted.
	 *
	 * @param string $header Rendered LiveCanvas header.
	 */
	public function home_header_menu( string $header ): string {
		if ( ! is_front_page() || ! did_action( 'wp_head' ) ) {
			return $header;
		}
		ob_start();
		wp_scripts()->do_items( array( 'linker-header-menu' ), 1 );
		return $header . (string) ob_get_clean();
	}

	/**
	 * Expose Site Kit's existing file version to the static cache.
	 *
	 * @param string $src    Registered script URL.
	 * @param string $handle WordPress script handle.
	 */
	public function version_fingerprinted_scripts( string $src, string $handle ): string {
		if ( ! in_array( $handle, array( 'googlesitekit-consent-mode', 'googlesitekit-events-provider-content-events', 'googlesitekit-events-provider-woocommerce' ), true ) || str_contains( $src, 'ver=' ) ) {
			return $src;
		}
		$directory = 'google-site-kit/dist/assets/js/';
		if ( ! str_starts_with( $src, plugins_url( $directory ) ) ) {
			return $src;
		}
		$filename = basename( (string) wp_parse_url( $src, PHP_URL_PATH ) );
		if ( preg_match( '/-([a-f0-9]{12,32})\.js$/i', $filename, $match ) ) {
			return add_query_arg( 'ver', $match[1], $src );
		}
		$file = WP_PLUGIN_DIR . '/' . $directory . $filename;
		return is_file( $file ) && is_readable( $file ) ? add_query_arg( 'ver', (string) filemtime( $file ), $src ) : $src;
	}

	/**
	 * WordPress emits these hints in wp_head before the stylesheets.
	 *
	 * @param array<int,array<string,string>> $resources Existing preload hints.
	 * @return array<int,array<string,string>>
	 */
	public function preload_resources( array $resources ): array {
		$base    = plugins_url( 'assets/fonts/', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		$weights = is_front_page() ? array( 400, 500, 600, 700 ) : array( 400, 600 );
		foreach ( $weights as $weight ) {
			$resources[] = array(
				'href'        => $base . 'plus-jakarta-sans-' . $weight . '.woff2',
				'as'          => 'font',
				'type'        => 'font/woff2',
				'crossorigin' => 'anonymous',
			);
		}
		if ( is_front_page() ) {
			$uploads = wp_get_upload_dir();
			$hero    = '/2026/09/linker-linking-value-serving-you.webp';
			if ( is_file( $uploads['basedir'] . $hero ) ) {
				$image = array(
					'href'          => $uploads['baseurl'] . $hero,
					'as'            => 'image',
					'fetchpriority' => 'high',
				);
				$small = '/2026/09/linker-linking-value-serving-you-768x576.webp';
				if ( is_file( $uploads['basedir'] . $small ) ) {
					$image['imagesrcset'] = $uploads['baseurl'] . $small . ' 768w, ' . $image['href'] . ' 1024w';
					$image['imagesizes']  = '(max-width: 600px) 768px, 100vw';
				}
				$resources[] = $image;
			}
		}
		if ( function_exists( 'is_product' ) && is_product() ) {
			// LiveCanvas has already resolved gallery fallbacks and WordPress image candidates.
			$gallery = new \WP_HTML_Tag_Processor( (string) ( $GLOBALS['lc_main_html'] ?? '' ) );
			if ( $gallery->next_tag(
				array(
					'tag_name'   => 'IMG',
					'class_name' => 'pdp-gallery-main',
				)
			) ) {
				$src = $gallery->get_attribute( 'src' );
				if ( is_string( $src ) && '' !== $src ) {
					$image  = array(
						'as'            => 'image',
						'href'          => $src,
						'fetchpriority' => 'high',
					);
					$srcset = $gallery->get_attribute( 'srcset' );
					if ( is_string( $srcset ) && '' !== $srcset ) {
						$image['imagesrcset'] = $srcset;
						$sizes                = $gallery->get_attribute( 'sizes' );
						if ( is_string( $sizes ) && '' !== $sizes ) {
							$image['imagesizes'] = $sizes;
						}
					}
					$resources[] = $image;
				}
			}
		}
		return $resources;
	}

	/** The product template supplies its own gallery, zoom and image viewer. */
	public function disable_woo_product_gallery(): void {
		remove_theme_support( 'wc-product-gallery-zoom' );
		remove_theme_support( 'wc-product-gallery-lightbox' );
		remove_theme_support( 'wc-product-gallery-slider' );
	}

	/** Marketing and editorial pages have no Woo cart UI. Registered dependencies remain available to widgets. */
	public function trim_woo_assets(): void {
		if ( did_action( 'woocommerce_add_to_cart' ) ) {
			return;
		}
		if ( function_exists( 'is_product' ) && is_product() ) {
			foreach ( array( 'woocommerce-general', 'woocommerce-layout', 'woocommerce-smallscreen', 'brands-styles', 'photoswipe', 'photoswipe-default-skin' ) as $handle ) {
				wp_dequeue_style( $handle );
			}
			foreach ( array( 'wc-photoswipe', 'photoswipe', 'wc-photoswipe-ui-default', 'photoswipe-ui-default', 'wc-flexslider', 'flexslider', 'wc-zoom', 'zoom', 'wc-single-product' ) as $handle ) {
				wp_dequeue_script( $handle );
			}
			remove_action( 'wp_footer', 'woocommerce_photoswipe' );
			return;
		}
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() || ComparePage::is_comparison_page() ) ) {
			// WindPress supplies the catalog and comparison styles.
			wp_dequeue_style( 'woocommerce-general' );
			return;
		}
		if ( ! function_exists( 'is_woocommerce' ) || is_woocommerce() || is_cart() || is_checkout() || is_account_page() || ComparePage::is_comparison_page() ) {
			return;
		}
		$post = get_queried_object();
		if ( $post instanceof \WP_Post ) {
			if ( str_contains( $post->post_content, '<!-- wp:woocommerce/' ) ) {
				return;
			}
			global $shortcode_tags;
			foreach ( get_shortcode_tags_in_content( $post->post_content ) as $tag ) {
				$callback = $shortcode_tags[ $tag ];
				if ( is_string( $callback ) && str_starts_with( $callback, 'WC_Shortcodes::' ) ) {
					return;
				}
			}
		}
		foreach ( array( 'woocommerce-layout', 'woocommerce-smallscreen', 'woocommerce-general' ) as $handle ) {
			wp_dequeue_style( $handle );
		}
		// Site Kit enqueues its cart/purchase event adapter at priority 30, with Woo as a dependency.
		wp_dequeue_script( 'googlesitekit-events-provider-woocommerce' );
		wp_dequeue_script( 'wc-add-to-cart' );
		wp_dequeue_script( 'woocommerce' );
	}

	/**
	 * The account chain's interaction layer (ticket #184): the submit state,
	 * the two-field password check of the guest cards, the gates and the
	 * workspace forms, and the register card's two steps (ticket #225, which
	 * initializes WooCommerce's selectWoo on the country field). The strength
	 * meter is WooCommerce's own (wc-password-strength-meter), which Woo
	 * enqueues on the pages that carry a password field. The account chain and
	 * standalone draft load this file. selectWoo and country-select are WooCommerce's
	 * scripts: the latter also localizes the select's translations, and both
	 * must precede this file (the register script is appended after them).
	 */
	public function enqueue_account_scripts(): void {
		$is_chain = ( function_exists( 'is_account_page' ) && is_account_page() )
			|| ( function_exists( 'is_checkout' ) && is_checkout() )
			|| ( function_exists( 'is_cart' ) && is_cart() );
		if ( ! $is_chain ) {
			return;
		}
		if ( function_exists( 'is_checkout' ) && is_checkout() ) {
			// Native Woo draft updates replace only its form. The separate inquiry
			// form keeps the customer's message/details while quantities, remove
			// and undo follow Woo's nonce, validation, notices and readback.
			wp_enqueue_script( 'wc-cart' );
		}
		$base = plugins_url( 'assets/', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		// The register card initializes WooCommerce's selectWoo on its country
		// field; the country-select script also carries that field's
		// translations. Every other account/checkout page keeps this file's
		// original dependency list (none), exactly as it was.
		$deps = AuthTemplates::is_register_request()
			? array( 'jquery', 'selectWoo', 'wc-country-select' )
			: array();
		wp_enqueue_script( 'linker-account-ui', $base . 'account-ui.js', $deps, (string) filemtime( dirname( __DIR__, 2 ) . '/assets/account-ui.js' ), true );
	}

	/**
	 * The product page's interaction layer: the gallery viewer, the
	 * specification tabs. The template renders the markup these scripts read;
	 * the styles stay in the WindPress layer. The comparison selection (its
	 * controls and its floating chip) is the comparison page's own module
	 * (ComparePage), which loads on the surfaces that carry either.
	 */
	public function enqueue_product_scripts(): void {
		$base = plugins_url( 'assets/', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		wp_enqueue_script( 'linker-header-menu', $base . 'header-menu.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/header-menu.js' ), true );
		// Every page can be switched from its own header or footer, and the
		// section a visitor is reading lives in the fragment no request
		// carries. This runs unconditionally: the guard is inside the script,
		// which only carries a hash the target page actually has.
		wp_enqueue_script( 'linker-language-hash', $base . 'language-hash.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/language-hash.js' ), true );
		if ( is_front_page() ) {
			wp_enqueue_script( 'linker-home-configurator', $base . 'home-configurator.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/home-configurator.js' ), true );
		}
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) {
			// The catalogue's family cards: the model picker switches the
			// article a card shows (spec: the live shop's family grid).
			wp_enqueue_script( 'linker-product-family', $base . 'product-family.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/product-family.js' ), true );
			// Bind before the first filter button is painted, without a blocking network request.
			$drawer_script = dirname( __DIR__, 2 ) . '/assets/catalog-ui.js';
			wp_register_script( 'linker-catalog-ui', false, array(), (string) filemtime( $drawer_script ), false );
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Bundled local script.
			wp_add_inline_script( 'linker-catalog-ui', (string) file_get_contents( $drawer_script ) );
			wp_enqueue_script( 'linker-catalog-ui' );
		}
		if ( ! function_exists( 'is_product' ) || ! is_product() ) {
			return;
		}
		// The one registration point for the page's script; the version follows
		// the asset file, as the sibling handles' do.
		wp_enqueue_script( 'linker-pdp-ui', $base . 'pdp-ui.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/pdp-ui.js' ), true );
	}
}

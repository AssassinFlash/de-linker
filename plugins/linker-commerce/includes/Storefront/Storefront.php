<?php
/**
 * The storefront templates of the products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/**
 * Serves the product pages of the site: the single product and the product
 * archive (the shop page, product categories and tags) render through this
 * plugin's templates, not through LiveCanvas (docs/specs/12-site-chrome.md
 * item 6: what a maintainer edits in the standard editor shows on the front
 * end the moment it is saved).
 *
 * The template filter runs after LiveCanvas's own (priority 99998 in its
 * templating module), so a dynamic template assigned to a product context
 * can no longer take the page away from these templates.
 */
final class Storefront {

	/**
	 * Adds the plugin's hooks.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Wires the templates in.
	 */
	public function register(): void {
		add_filter( 'template_include', array( $this, 'template' ), 99999 );
		add_action( 'wp_enqueue_scripts', array( $this, 'assets' ) );
		add_filter( 'woocommerce_show_page_title', '__return_false' );
	}

	/**
	 * The plugin's template for a WooCommerce product context, the theme's
	 * one for everything else.
	 *
	 * @param string $template The template WordPress located.
	 * @return string The template to include.
	 */
	public function template( string $template ): string {
		$directory = plugin_dir_path( $this->plugin_file ) . 'templates/';
		if ( is_singular( 'product' ) ) {
			return $directory . 'storefront-single-product.php';
		}
		if ( is_post_type_archive( 'product' ) || is_tax( get_object_taxonomies( 'product', 'names' ) ) ) {
			return $directory . 'storefront-archive-product.php';
		}
		return $template;
	}

	/**
	 * The storefront's stylesheet, and the product page's viewer script, on
	 * the pages they draw.
	 */
	public function assets(): void {
		if ( ! $this->is_product_context() ) {
			return;
		}
		$base = plugin_dir_path( $this->plugin_file );
		wp_enqueue_style(
			'linker-commerce-storefront',
			plugins_url( 'assets/storefront.css', $this->plugin_file ),
			array(),
			(string) filemtime( $base . 'assets/storefront.css' )
		);
		if ( is_singular( 'product' ) ) {
			wp_enqueue_script(
				'linker-commerce-storefront',
				plugins_url( 'assets/storefront.js', $this->plugin_file ),
				array(),
				(string) filemtime( $base . 'assets/storefront.js' ),
				true
			);
		}
	}

	/**
	 * Whether the request shows the storefront's templates: the single
	 * product or a product archive (the shop page, categories, tags,
	 * attributes).
	 */
	private function is_product_context(): bool {
		return is_singular( 'product' )
			|| is_post_type_archive( 'product' )
			|| is_tax( get_object_taxonomies( 'product', 'names' ) );
	}
}

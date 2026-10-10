<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Admin\StatusColumn;
use Linker\I18n\Cli\Command;
use Linker\I18n\Rest\RestLang;
use Linker\I18n\SameSlug\Lookup;
use Linker\I18n\SameSlug\PostSlugs;
use Linker\I18n\SameSlug\TermSlugs;
use Linker\I18n\Translation\Aligner;
use Linker\I18n\Translation\DeepSeekClient;
use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Planner;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;
use Linker\I18n\Translation\Validator;
use Linker\I18n\Woo\AttributeLabels;
use Linker\I18n\Woo\Orders;
use Linker\I18n\Woo\Projection;
use Linker\I18n\Woo\Storefront;

/**
 * Hooks Linker i18n into WordPress, Polylang and WooCommerce. Every hook the
 * plugin uses is listed here.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param string $file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $file ) {}

	/**
	 * Adds the hooks that do not need Polylang, and the rest once Polylang
	 * has loaded its API (`pll_init`; on the front end only when languages
	 * exist, so the plugin does nothing before `wp linker-i18n setup`).
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'load_textdomain' ) );
		add_action( 'pll_init', array( $this, 'hook' ) );
	}

	/**
	 * Loads the translations shipped in the plugin's languages/ directory.
	 */
	public function load_textdomain(): void {
		load_plugin_textdomain( 'linker-i18n', false, dirname( plugin_basename( $this->file ) ) . '/languages' );
	}

	/**
	 * Adds the plugin's hooks.
	 */
	public function hook(): void {
		$languages  = new Languages();
		$tokenizer  = new HtmlTokenizer();
		$state      = new State();
		$links      = new LinkLocalizer( $languages, $tokenizer );
		$projection = new Projection( $languages );
		$twins      = new Twins( $languages, $links, $projection );
		$rules      = Rules::load( dirname( $this->file ) . '/data' );
		$translator = new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), $state, DeepSeekClient::from_environment( $rules ), new Validator( $rules ), $twins );
		$jobs       = new Jobs( $languages, $translator, $twins, $state );

		// What Polylang translates.
		$types = new TranslatedTypes();
		add_filter( 'pll_get_post_types', array( $types, 'post_types' ), 10, 2 );
		add_filter( 'pll_get_taxonomies', array( $types, 'taxonomies' ), 10, 2 );

		// One slug for an English object and its German version.
		$post_slugs = new PostSlugs( $languages );
		$term_slugs = new TermSlugs( $languages );
		$lookup     = new Lookup( $languages );
		add_filter( 'wp_unique_post_slug', array( $post_slugs, 'unique' ), 10, 6 );
		add_filter( 'wp_update_term_parent', array( $term_slugs, 'note' ), 10, 3 );
		add_filter( 'get_terms_args', array( $term_slugs, 'narrow' ), 20 );
		add_filter( 'request', array( $lookup, 'request' ), 20 );
		add_filter( 'rest_dispatch_request', array( $lookup, 'store_product' ), 10, 3 );

		// German URL segments.
		$segments = new UrlSegments( $languages );
		add_filter( 'rewrite_rules_array', array( $segments, 'rules' ) );
		add_filter( 'pll_modify_rewrite_rule', array( $segments, 'polylang_rule' ), 10, 4 );
		add_action( 'wp_loaded', array( $segments, 'refresh' ), 20 );
		add_filter( 'post_type_link', array( $segments, 'link' ), 30 );
		add_filter( 'term_link', array( $segments, 'link' ), 30 );
		add_filter( 'post_type_archive_link', array( $segments, 'link' ), 30 );
		add_filter( 'pll_translation_url', array( $segments, 'link' ) );

		// hreflang and 404.
		$seo = new Seo();
		add_filter( 'pll_rel_hreflang_attributes', array( $seo, 'hreflangs' ) );
		add_filter( 'do_redirect_guess_404_permalink', array( $seo, 'guess_404' ) );

		// REST lists in one language.
		$rest = new RestLang( $languages );
		add_filter( 'rest_request_before_callbacks', array( $rest, 'enter' ), 10, 3 );
		add_filter( 'rest_request_after_callbacks', array( $rest, 'leave' ) );
		add_action( 'pre_get_posts', array( $rest, 'posts' ) );
		add_filter( 'get_terms_args', array( $rest, 'terms' ), 10, 2 );

		// Translation on save.
		add_action( 'wp_after_insert_post', array( $jobs, 'post_saved' ), 10, 2 );
		add_action( 'created_term', array( $jobs, 'term_saved' ), 10, 3 );
		add_action( 'edited_term', array( $jobs, 'term_saved' ), 10, 3 );
		add_action( Jobs::HOOK, array( $jobs, 'run' ), 10, 4 );

		// WooCommerce: commerce fields, the storefront, orders and their emails.
		foreach ( array( 'woocommerce_new_product', 'woocommerce_update_product', 'woocommerce_product_set_stock_status', 'woocommerce_updated_product_stock' ) as $action ) {
			add_action( $action, array( $projection, 'changed' ), 20 );
		}
		$storefront = new Storefront( $languages );
		add_filter( 'woocommerce_add_to_cart_product_id', array( $storefront, 'cart_product' ) );
		add_filter( 'linker_commerce_facts_product_id', array( $storefront, 'facts_product_id' ) );
		add_filter( 'woocommerce_store_api_add_to_cart_data', array( $storefront, 'store_cart_product' ) );
		add_filter( 'woocommerce_product_get_name', array( $storefront, 'name' ), 10, 2 );
		add_filter( 'woocommerce_add_to_cart_item_name_in_quotes', array( $storefront, 'quoted_item_name' ), 10, 2 );
		add_filter( 'woocommerce_cart_item_permalink', array( $storefront, 'cart_item_permalink' ), 10, 2 );
		add_filter( 'woocommerce_product_get_sku', array( $storefront, 'sku' ), 10, 2 );
		foreach ( array( 'shop', 'cart', 'checkout', 'myaccount', 'terms' ) as $page ) {
			add_filter( "woocommerce_get_{$page}_page_id", array( $storefront, 'page_id' ) );
		}
		$orders = new Orders( $languages );
		add_action( 'woocommerce_checkout_create_order', array( $orders, 'record' ) );
		add_action( 'woocommerce_store_api_checkout_update_order_meta', array( $orders, 'record' ) );
		add_filter( 'woocommerce_email_actions', array( $orders, 'notifications' ), PHP_INT_MAX );
		add_filter( 'woocommerce_allow_switching_email_locale', array( $orders, 'email' ), 10, 2 );
		add_filter( 'woocommerce_email_setup_locale', array( $orders, 'setup_customer_email' ) );
		add_filter( 'woocommerce_email_restore_locale', array( $orders, 'restore_customer_email' ) );
		add_filter( 'woocommerce_attribute_label', array( new AttributeLabels(), 'label' ) );

		// The German column of the admin lists.
		$column = new StatusColumn( $languages, $state, $jobs );
		foreach ( StatusColumn::POST_TYPES as $post_type ) {
			add_filter( "manage_{$post_type}_posts_columns", array( $column, 'columns' ) );
			add_action( "manage_{$post_type}_posts_custom_column", array( $column, 'cell' ), 10, 2 );
		}
		add_filter( 'page_row_actions', array( $column, 'row_actions' ), 10, 2 );
		add_filter( 'post_row_actions', array( $column, 'row_actions' ), 10, 2 );
		add_action( 'admin_post_' . StatusColumn::ACTION, array( $column, 'retranslate' ) );
		add_action( 'admin_notices', array( $column, 'notice' ) );

		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			\WP_CLI::add_command( 'linker-i18n', new Command( $languages, new Setup(), $translator, $jobs, $state, $links ) );
		}
	}
}

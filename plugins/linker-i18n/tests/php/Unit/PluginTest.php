<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Plugin;
use Linker\I18n\Admin\StatusColumn;
use Linker\I18n\Jobs;
use Linker\I18n\Rest\RestLang;
use Linker\I18n\SameSlug\Lookup;
use Linker\I18n\SameSlug\PostSlugs;
use Linker\I18n\SameSlug\TermSlugs;
use Linker\I18n\Seo;
use Linker\I18n\TranslatedTypes;
use Linker\I18n\UrlSegments;
use Linker\I18n\Woo\AttributeLabels;
use Linker\I18n\Woo\Orders;
use Linker\I18n\Woo\Projection;
use Linker\I18n\Woo\Storefront;
use WP_Mock;
use WP_Mock\Matcher\AnyInstance;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\I18n\Plugin
 */
final class PluginTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-i18n/linker-i18n.php';

	/**
	 * Every hook of the plugin: type, hook, class and method of the callback,
	 * priority, number of arguments.
	 */
	private const HOOKS = array(
		array( 'filter', 'pll_get_post_types', TranslatedTypes::class, 'post_types', 10, 2 ),
		array( 'filter', 'pll_get_taxonomies', TranslatedTypes::class, 'taxonomies', 10, 2 ),
		array( 'filter', 'wp_unique_post_slug', PostSlugs::class, 'unique', 10, 6 ),
		array( 'filter', 'wp_update_term_parent', TermSlugs::class, 'note', 10, 3 ),
		array( 'filter', 'get_terms_args', TermSlugs::class, 'narrow', 20, 1 ),
		array( 'filter', 'request', Lookup::class, 'request', 20, 1 ),
		array( 'filter', 'rest_dispatch_request', Lookup::class, 'store_product', 10, 3 ),
		array( 'filter', 'rewrite_rules_array', UrlSegments::class, 'rules', 10, 1 ),
		array( 'filter', 'pll_modify_rewrite_rule', UrlSegments::class, 'polylang_rule', 10, 4 ),
		array( 'action', 'wp_loaded', UrlSegments::class, 'refresh', 20, 1 ),
		array( 'filter', 'post_type_link', UrlSegments::class, 'link', 30, 1 ),
		array( 'filter', 'term_link', UrlSegments::class, 'link', 30, 1 ),
		array( 'filter', 'post_type_archive_link', UrlSegments::class, 'link', 30, 1 ),
		array( 'filter', 'pll_translation_url', UrlSegments::class, 'link', 10, 1 ),
		array( 'filter', 'pll_rel_hreflang_attributes', Seo::class, 'hreflangs', 10, 1 ),
		array( 'filter', 'do_redirect_guess_404_permalink', Seo::class, 'guess_404', 10, 1 ),
		array( 'filter', 'rest_request_before_callbacks', RestLang::class, 'enter', 10, 3 ),
		array( 'filter', 'rest_request_after_callbacks', RestLang::class, 'leave', 10, 1 ),
		array( 'action', 'pre_get_posts', RestLang::class, 'posts', 10, 1 ),
		array( 'filter', 'get_terms_args', RestLang::class, 'terms', 10, 2 ),
		array( 'action', 'wp_after_insert_post', Jobs::class, 'post_saved', 10, 2 ),
		array( 'action', 'created_term', Jobs::class, 'term_saved', 10, 3 ),
		array( 'action', 'edited_term', Jobs::class, 'term_saved', 10, 3 ),
		array( 'action', 'linker_i18n_translate', Jobs::class, 'run', 10, 4 ),
		array( 'action', 'woocommerce_new_product', Projection::class, 'changed', 20, 1 ),
		array( 'action', 'woocommerce_update_product', Projection::class, 'changed', 20, 1 ),
		array( 'action', 'woocommerce_product_set_stock_status', Projection::class, 'changed', 20, 1 ),
		array( 'action', 'woocommerce_updated_product_stock', Projection::class, 'changed', 20, 1 ),
		array( 'filter', 'woocommerce_add_to_cart_product_id', Storefront::class, 'cart_product', 10, 1 ),
		array( 'filter', 'woocommerce_store_api_add_to_cart_data', Storefront::class, 'store_cart_product', 10, 1 ),
		array( 'filter', 'woocommerce_product_get_name', Storefront::class, 'name', 10, 2 ),
		array( 'filter', 'woocommerce_add_to_cart_item_name_in_quotes', Storefront::class, 'quoted_item_name', 10, 2 ),
		array( 'filter', 'woocommerce_cart_item_permalink', Storefront::class, 'cart_item_permalink', 10, 2 ),
		array( 'filter', 'woocommerce_product_get_sku', Storefront::class, 'sku', 10, 2 ),
		array( 'filter', 'woocommerce_get_shop_page_id', Storefront::class, 'page_id', 10, 1 ),
		array( 'filter', 'woocommerce_get_cart_page_id', Storefront::class, 'page_id', 10, 1 ),
		array( 'filter', 'woocommerce_get_checkout_page_id', Storefront::class, 'page_id', 10, 1 ),
		array( 'filter', 'woocommerce_get_myaccount_page_id', Storefront::class, 'page_id', 10, 1 ),
		array( 'filter', 'woocommerce_get_terms_page_id', Storefront::class, 'page_id', 10, 1 ),
		array( 'action', 'woocommerce_checkout_create_order', Orders::class, 'record', 10, 1 ),
		array( 'action', 'woocommerce_store_api_checkout_update_order_meta', Orders::class, 'record', 10, 1 ),
		array( 'filter', 'woocommerce_email_actions', Orders::class, 'notifications', PHP_INT_MAX, 1 ),
		array( 'filter', 'woocommerce_allow_switching_email_locale', Orders::class, 'email', 10, 2 ),
		array( 'filter', 'woocommerce_email_setup_locale', Orders::class, 'setup_customer_email', 10, 1 ),
		array( 'filter', 'woocommerce_email_restore_locale', Orders::class, 'restore_customer_email', 10, 1 ),
		array( 'filter', 'woocommerce_attribute_label', AttributeLabels::class, 'label', 10, 1 ),
		array( 'filter', 'manage_page_posts_columns', StatusColumn::class, 'columns', 10, 1 ),
		array( 'action', 'manage_page_posts_custom_column', StatusColumn::class, 'cell', 10, 2 ),
		array( 'filter', 'manage_post_posts_columns', StatusColumn::class, 'columns', 10, 1 ),
		array( 'action', 'manage_post_posts_custom_column', StatusColumn::class, 'cell', 10, 2 ),
		array( 'filter', 'manage_product_posts_columns', StatusColumn::class, 'columns', 10, 1 ),
		array( 'action', 'manage_product_posts_custom_column', StatusColumn::class, 'cell', 10, 2 ),
		array( 'filter', 'page_row_actions', StatusColumn::class, 'row_actions', 10, 2 ),
		array( 'filter', 'post_row_actions', StatusColumn::class, 'row_actions', 10, 2 ),
		array( 'action', 'admin_post_linker_i18n_retranslate', StatusColumn::class, 'retranslate', 10, 1 ),
		array( 'action', 'admin_notices', StatusColumn::class, 'notice', 10, 1 ),
	);

	/**
	 * Registering loads the text domain on init and waits for Polylang's API.
	 */
	public function test_register_waits_for_polylang(): void {
		$plugin = new Plugin( self::FILE );

		WP_Mock::expectActionAdded( 'init', array( $plugin, 'load_textdomain' ) );
		WP_Mock::expectActionAdded( 'pll_init', array( $plugin, 'hook' ) );

		$plugin->register();

		$this->assertConditionsMet();
	}

	/**
	 * Once Polylang is loaded every hook is added, and only these (strict
	 * mode fails on any other).
	 */
	public function test_hook_adds_every_hook(): void {
		foreach ( self::HOOKS as list( $type, $hook, $class, $method, $priority, $arguments ) ) {
			WP_Mock::expectHookAdded( $type, $hook, array( new AnyInstance( $class ), $method ), $priority, $arguments );
		}

		( new Plugin( dirname( __DIR__, 3 ) . '/linker-i18n.php' ) )->hook();

		$this->assertConditionsMet();
	}

	/**
	 * Translations load from the plugin's own languages/ directory.
	 */
	public function test_load_textdomain_uses_the_languages_directory(): void {
		WP_Mock::userFunction(
			'plugin_basename',
			array(
				'args'   => array( self::FILE ),
				'return' => 'linker-i18n/linker-i18n.php',
			)
		);
		WP_Mock::userFunction(
			'load_plugin_textdomain',
			array(
				'times' => 1,
				'args'  => array( 'linker-i18n', false, 'linker-i18n/languages' ),
			)
		);

		( new Plugin( self::FILE ) )->load_textdomain();

		$this->assertConditionsMet();
	}
}

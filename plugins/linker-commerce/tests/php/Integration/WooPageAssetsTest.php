<?php
/**
 * WordPress resolves the Site Kit Woo adapter's dependencies after the enqueue action.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use WP_Post;

/** The shared tag and the Site Kit Woo event adapter have different consumers. */
final class WooPageAssetsTest extends IntegrationTestCase {

	/**
	 * Marketing pages with and without a storefront control.
	 *
	 * @return array<string,array{bool,string,bool}>
	 */
	public static function pages(): array {
		return array(
			'no adapter'     => array( false, 'Installer services', false ),
			'adapter'        => array( true, 'Installer services', false ),
			'shopping embed' => array( true, '[add_to_cart id="123"]', true ),
			'shopping block' => array( true, '<!-- wp:woocommerce/product-button /-->', true ),
		);
	}

	/**
	 * The head and footer share one dependency queue.
	 *
	 * @dataProvider pages
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 *
	 * @param bool   $adapter   Whether Site Kit has an active Analytics snippet.
	 * @param string $content   Current page body.
	 * @param bool   $uses_cart Whether Woo and its adapter are needed.
	 */
	public function test_resolved_frontend_queue( bool $adapter, string $content, bool $uses_cart ): void {
		global $wp_query;
		$page                     = new WP_Post(
			(object) array(
				'post_type'    => 'page',
				'post_content' => $content,
			)
		);
		$wp_query->queried_object = $page;
		$wp_query->is_page        = true;
		$wp_query->is_singular    = true;

		$provider = 'googlesitekit-events-provider-woocommerce';
		// Site Kit registers the adapter at priority 30 when its Analytics snippet is active.
		add_action(
			'wp_enqueue_scripts',
			static function () use ( $adapter, $provider ): void {
				wp_enqueue_script( 'google_gtagjs', '/gtag.js', array(), '1', true );
				if ( $adapter ) {
					wp_enqueue_script( $provider, '/woo-events.js', array( 'woocommerce' ), '1', true );
				}
			},
			30
		);
		do_action( 'wp_enqueue_scripts' ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Exercise the native WordPress enqueue lifecycle.
		$scripts = wp_scripts();
		$scripts->all_deps( $scripts->queue );
		$this->assertContains( 'google_gtagjs', $scripts->to_do );
		foreach ( array( $provider, 'woocommerce', 'wc-jquery-blockui', 'wc-js-cookie' ) as $handle ) {
			$this->assertSame( $uses_cart, in_array( $handle, $scripts->to_do, true ), $handle );
		}
	}

	/**
	 * The custom product gallery and first-touch attribution survive Woo queue resolution.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_product_gallery_and_attribution_assets(): void {
		global $wp_query;
		$wp_query->queried_object = new WP_Post( (object) array( 'post_type' => 'product' ) );
		$wp_query->is_single      = true;
		$wp_query->is_singular    = true;
		do_action( 'wp_enqueue_scripts' ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Exercise the native WordPress enqueue lifecycle.
		$scripts = wp_scripts();
		$scripts->all_deps( $scripts->queue );
		$this->assertContains( 'linker-pdp-ui', $scripts->to_do );
		foreach ( array( 'wc-zoom', 'wc-flexslider', 'wc-photoswipe', 'wc-photoswipe-ui-default', 'wc-single-product' ) as $handle ) {
			$this->assertNotContains( $handle, $scripts->to_do );
		}
		$styles = wp_styles();
		$styles->all_deps( $styles->queue );
		foreach ( array( 'woocommerce-general', 'woocommerce-layout', 'woocommerce-smallscreen', 'brands-styles', 'photoswipe', 'photoswipe-default-skin' ) as $handle ) {
			$this->assertNotContains( $handle, $styles->to_do );
		}
		$this->assertFalse( has_action( 'wp_footer', 'woocommerce_photoswipe' ) );

		ob_start();
		$scripts->do_items( array( 'wc-order-attribution' ), 1 );
		$tags = new \WP_HTML_Tag_Processor( (string) ob_get_clean() );
		foreach ( array( 'sourcebuster-js-js', 'wc-order-attribution-js' ) as $id ) {
			while ( $tags->next_tag( array( 'tag_name' => 'SCRIPT' ) ) && $tags->get_attribute( 'id' ) !== $id ) {
				continue;
			}
			$this->assertSame( $id, $tags->get_attribute( 'id' ) );
			$this->assertNotNull( $tags->get_attribute( 'defer' ) );
		}
	}
}

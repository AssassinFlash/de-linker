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
}

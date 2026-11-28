<?php
/**
 * Frontend styles emitted around the WindPress cache.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\WindPressPageStyles;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Public component stylesheet selection.
 *
 * @covers \Linker\Commerce\Presentation\WindPressPageStyles
 */
final class WindPressPageStylesTest extends TestCase {

	/**
	 * The visible consumer chooses the published stylesheet, including pages
	 * that mount a shortcode outside its usual permalink.
	 *
	 * @dataProvider pages
	 * @param string        $native  WordPress or Woo query.
	 * @param string        $body    Page content.
	 * @param string        $render  Active LiveCanvas template result.
	 * @param array<string> $before Files before the common cache.
	 * @param array<string> $after  Files after it.
	 */
	public function test_page_loads_its_volume_styles( string $native, string $body, string $render, array $before, array $after ): void {
		$dir  = sys_get_temp_dir() . '/linker-volume-' . uniqid();
		$path = $dir . '/windpress/cache/linker';
		mkdir( $path, 0777, true );
		foreach ( array_merge( $before, $after ) as $file ) {
			file_put_contents( $path . '/' . $file, $file );
		}

		$post = new WP_Post( (object) array( 'post_content' => $body ) );
		WP_Mock::userFunction( 'get_queried_object' )->andReturn( $post );
		WP_Mock::userFunction( 'wp_get_upload_dir' )->andReturn(
			array(
				'baseurl' => 'https://linker.test/uploads',
				'basedir' => $dir,
			)
		);
		foreach ( array( 'is_shop', 'is_product_taxonomy', 'is_cart', 'is_checkout', 'is_account_page', 'is_front_page', 'is_home', 'is_category', 'is_search', 'is_404' ) as $query ) {
			WP_Mock::userFunction( $query )->andReturn( $query === $native );
		}
		WP_Mock::userFunction( 'is_singular' )->andReturnUsing( static fn ( string $type ): bool => $type === $native );
		$emitted = array();
		WP_Mock::userFunction( 'wp_enqueue_style' )->andReturnUsing(
			function ( string $handle, string $url, array $dependencies, string $version ) use ( &$emitted ): void {
				$file      = basename( $url );
				$emitted[] = $file;
				$this->assertSame( 'https://linker.test/uploads/windpress/cache/linker/' . $file, $url );
				$this->assertSame( substr( md5( $file ), 0, 12 ), $version );
			}
		);
		WP_Mock::userFunction( 'wp_print_styles' )->andReturn( null );

		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- This is the active LiveCanvas template's global.
		$GLOBALS['lc_main_html'] = $render;
		try {
			$styles = new WindPressPageStyles();
			$styles->before_cache();
			$this->assertSame( $before, $emitted );
			$emitted = array();
			$styles->after_cache();
			$this->assertSame( $after, $emitted );
		} finally {
			unset( $GLOBALS['lc_main_html'] );
			foreach ( array_merge( $before, $after ) as $file ) {
				unlink( $path . '/' . $file );
			}
			rmdir( $path );
			rmdir( dirname( $path ) );
			rmdir( dirname( $path, 2 ) );
			rmdir( $dir );
		}
	}

	/** Published native pages, template assignments and custom mounts.
	 *
	 * @return array<string,array{string,string,string,list<string>,list<string>}>
	 */
	public static function pages(): array {
		return array(
			'home showcase'            => array( 'is_front_page', '', '<section id="configurator-showcase"><a href="/solution-configurator/" data-linker-planner-entry>Plan</a></section>', array(), array( 'marketing-rhythm.css', 'home-bundle.css', 'capability-cards.css', 'app-details.css', 'reference-photo-scenes.css' ) ),
			'custom showcase'          => array( '', '<section id="configurator-showcase">', '', array(), array( 'home-configurator.css' ) ),

			'product category'         => array( 'is_product_taxonomy', '', '', array( 'model-links.css', 'products-mounts.css', 'products.css', 'storefront.css' ), array() ),
			'matrix body'              => array( '', '[linker_compatibility_matrix]', '', array( 'compatibility-matrix.css' ), array() ),
			'matrix link only'         => array( '', '[linker_compatibility_matrix_link]', '', array(), array() ),
			'translated FAQ'           => array( '', '', '<div id="linker-faq-page">', array( 'faq.css' ), array() ),
			'product detail'           => array( 'product', '', '', array( 'pdp.css', 'model-links.css', 'storefront.css' ), array() ),
			'solution product links'   => array( '', '[linker_solution_products scope="utility"]', '', array( 'model-links.css' ), array() ),
			'native search'            => array( 'is_search', '', '', array( 'blog-search.css' ), array( 'journal.css' ) ),
			'account endpoint'         => array( 'is_account_page', '', '', array( 'account.css', 'auth.css', 'storefront.css' ), array() ),
			'planner inside post'      => array( 'post', '[linker_planner]', '', array( 'model-links.css', 'blog.css', 'contact-invitation.css' ), array( 'planner.css', 'planner-equipment.css', 'planner-report.css', 'planner-site-energy.css', 'roof-studio.css' ) ),
			'translated services'      => array( '', '<main id="service-redesign">', '', array(), array( 'service-intro.css', 'marketing-rhythm.css', 'capability-cards.css', 'app-details.css' ) ),
			'installer stage controls' => array( '', '<main id="installer-journal">', '', array(), array( 'service-intro.css', 'marketing-rhythm.css', 'capability-cards.css', 'app-details.css' ) ),
			'utility application dots' => array( '', '<main id="tv-utility-page-v1">', '', array(), array( 'service-intro.css', 'marketing-rhythm.css', 'utility-journal.css', 'utility-middle.css' ) ),
			'about inline'             => array( '', '<main id="about-journal"><style data-site-css="about-journal.css">', '', array(), array( 'marketing-rhythm.css', 'app-details.css', 'reference-photo-scenes.css' ) ),
			'about published'          => array( '', '<main id="about-journal">', '', array(), array( 'marketing-rhythm.css', 'app-details.css', 'reference-photo-scenes.css', 'about-journal.css', 'mobile-photo-topics.css' ) ),
			'solutions published'      => array( '', '<main id="tv-solution-v1">', '', array(), array( 'marketing-rhythm.css', 'solution-journal.css', 'capability-cards.css', 'app-details.css' ) ),
			'no component'             => array( '', '<p>Legal notice</p>', '', array(), array() ),
		);
	}
}

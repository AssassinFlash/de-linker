<?php
/**
 * Read-only navigation regression in the existing native Polylang frontend.
 *
 * Run with PHP 8.3, not `wp eval-file` (WP-CLI omits frontend language hooks):
 * php -c /path/to/php.ini tests/fixtures/supply-brands-frontend.php \
 *   --wordpress-root=/path/to/wordpress --site-url=http://127.0.0.1:8888
 *
 * It loads the author source under an isolated class name, leaving the site's
 * plugin symlink, routes, data and templates unchanged. No model is called.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use PLL_Frontend;
use PLL_Language;
use RuntimeException;

/** Typed boundary for the isolated author source instance. */
interface SupplyBrandsFrontendReader {
	/**
	 * Render one LC data fragment.
	 *
	 * @param array<string,string>|string $atts Fragment attributes.
	 */
	public function render( $atts = array() ): string;
}

if ( 'cli' !== PHP_SAPI ) {
	exit( 2 );
}

$linker_commerce_supply_options = getopt( '', array( 'wordpress-root:', 'site-url:' ) );
if ( ! isset( $linker_commerce_supply_options['wordpress-root'], $linker_commerce_supply_options['site-url'] ) || ! is_string( $linker_commerce_supply_options['wordpress-root'] ) || ! is_string( $linker_commerce_supply_options['site-url'] ) ) {
	fwrite( STDERR, "Required: --wordpress-root=/existing/wordpress --site-url=http://existing-site\n" );
	exit( 2 );
}
$linker_commerce_supply_host = parse_url( $linker_commerce_supply_options['site-url'], PHP_URL_HOST );
$linker_commerce_supply_port = parse_url( $linker_commerce_supply_options['site-url'], PHP_URL_PORT );
$_SERVER['HTTP_HOST']        = $linker_commerce_supply_host . ( $linker_commerce_supply_port ? ':' . $linker_commerce_supply_port : '' );
$_SERVER['SERVER_NAME']      = $linker_commerce_supply_host;
$_SERVER['SERVER_PORT']      = (string) ( $linker_commerce_supply_port ? $linker_commerce_supply_port : 80 );
$_SERVER['REQUEST_URI']      = '/';
$_SERVER['SCRIPT_NAME']      = '/index.php';
$_SERVER['PHP_SELF']         = '/index.php';
$_SERVER['REQUEST_METHOD']   = 'GET';
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- native WordPress frontend flag.
ob_start();
require rtrim( $linker_commerce_supply_options['wordpress-root'], '/' ) . '/wp-blog-header.php';
ob_end_clean();
if ( ! function_exists( 'PLL' ) || ! PLL() instanceof PLL_Frontend || ( defined( 'WP_CLI' ) && WP_CLI ) ) {
	fwrite( STDERR, "A native Polylang frontend context is required.\n" );
	exit( 2 );
}
// Run the author source while the shared site's plugin remains on its own head.
$linker_commerce_supply_source = file_get_contents( dirname( __DIR__, 2 ) . '/includes/Presentation/SupplyBrands.php' );
$linker_commerce_supply_source = str_replace( 'final class SupplyBrands {', 'final class SupplyBrandsFrontendProbe implements \\Linker\\Commerce\\Tests\\Fixtures\\SupplyBrandsFrontendReader {', (string) $linker_commerce_supply_source );
$linker_commerce_supply_reader = eval( preg_replace( '/^<\?php/', '', $linker_commerce_supply_source ) . 'return new SupplyBrandsFrontendProbe();' ); // phpcs:ignore Squiz.PHP.Eval.Discouraged -- isolated read-only source probe; never accepts HTTP or user content.
if ( ! $linker_commerce_supply_reader instanceof SupplyBrandsFrontendReader ) {
	throw new RuntimeException( 'The author source probe does not implement its render contract.' );
}
$linker_commerce_supply_original  = PLL()->curlang;
$linker_commerce_supply_results   = array(
	'en' => array(
		'home'       => '',
		'commercial' => '',
		'storage'    => '',
	),
	'de' => array(
		'home'       => '',
		'commercial' => '',
		'storage'    => '',
	),
);
$linker_commerce_supply_fragments = array(
	'en' => array(),
	'de' => array(),
);
try {
	foreach ( array( 'en', 'de' ) as $linker_commerce_supply_language ) {
		$linker_commerce_supply_native_language = PLL()->model->get_language( $linker_commerce_supply_language );
		if ( ! $linker_commerce_supply_native_language instanceof PLL_Language ) {
			throw new RuntimeException( 'The required language is not installed.' );
		}
		PLL()->curlang = $linker_commerce_supply_native_language;
		if ( pll_current_language() !== $linker_commerce_supply_language ) {
			throw new RuntimeException( 'Native frontend language did not change.' );
		}
		foreach ( array(
			'home'       => 'home-storage',
			'commercial' => 'commercial-storage',
			'storage'    => 'home-storage,commercial-storage',
		) as $linker_commerce_supply_scope => $linker_commerce_supply_categories ) {
			$linker_commerce_supply_results[ $linker_commerce_supply_language ][ $linker_commerce_supply_scope ] = $linker_commerce_supply_reader->render( array( 'categories' => $linker_commerce_supply_categories ) );
		}
		$linker_commerce_supply_header = dirname( __DIR__, 2 ) . '/content/livecanvas/partials/' . ( 'de' === $linker_commerce_supply_language ? 'de/' : '' ) . 'header.html';
		preg_match_all( '/\[linker_supply_brands ([^\]]+)\]/', (string) file_get_contents( $linker_commerce_supply_header ), $linker_commerce_supply_matches );
		foreach ( $linker_commerce_supply_matches[1] as $linker_commerce_supply_attributes ) {
			$linker_commerce_supply_fragments[ $linker_commerce_supply_language ][] = $linker_commerce_supply_reader->render( shortcode_parse_atts( $linker_commerce_supply_attributes ) );
		}
	}
} finally {
	PLL()->curlang = $linker_commerce_supply_original;
}
$linker_commerce_supply_first_german = $linker_commerce_supply_fragments['de'][0] ?? '';
$linker_commerce_supply_checks       = array(
	'native_frontend'             => true,
	'english_scopes_populated'    => ! in_array( '', $linker_commerce_supply_results['en'], true ),
	'german_scopes_populated'     => ! in_array( '', $linker_commerce_supply_results['de'], true ),
	'same_current_supply_en_de'   => $linker_commerce_supply_results['en'] === $linker_commerce_supply_results['de'],
	'ten_real_header_fragments'   => 5 === count( $linker_commerce_supply_fragments['en'] ) && 5 === count( $linker_commerce_supply_fragments['de'] ) && ! in_array( '', array_merge( ...array_values( $linker_commerce_supply_fragments ) ), true ),
	'german_sentence_terms'       => str_starts_with( $linker_commerce_supply_first_german, 'Energiespeicher von ' ) && str_contains( $linker_commerce_supply_first_german, ' und ' ),
	'withdrawn_brand_not_present' => ! str_contains( strtolower( json_encode( $linker_commerce_supply_results, JSON_THROW_ON_ERROR ) ), 'ecoflow' ),
);
echo json_encode(
	array(
		'checks'    => $linker_commerce_supply_checks,
		'scopes'    => $linker_commerce_supply_results,
		'fragments' => $linker_commerce_supply_fragments,
	),
	JSON_PRETTY_PRINT
), "\n";
exit( in_array( false, $linker_commerce_supply_checks, true ) ? 1 : 0 );

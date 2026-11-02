<?php
/** The public REST PHP process loads the native temporary-file API itself.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use PHPUnit\Framework\TestCase;

/** The WP-CLI bootstrap has a different set of preloaded admin functions. */
final class PlannerSeriesFrontendTest extends TestCase {
	/** Exercise the actual frontend PHP process, without an Engine or guest write. */
	public function test_frontend_series_download_loads_wordpress_file_api(): void {
		$root = getenv( 'LINKER_WP_ROOT' );
		$this->assertIsString( $root );
		$token  = bin2hex( random_bytes( 16 ) );
		$probe  = $root . '/wp-content/mu-plugins/linker-series-' . $token . '.php';
		$bytes  = "timestamp,power\n2023-01-01,1\n";
		$code   = <<<'PROBE'
<?php
if (($_GET['linker_series_fixture'] ?? '') !== 'TOKEN') { return; }
add_action('template_redirect', static function () {
    if (function_exists('wp_tempnam')) { status_header(409); echo 'frontend fixture preloaded file API'; exit; }
    add_filter('pre_option_linker_planner_url', static fn () => 'http://127.0.0.1:9');
    $transport = new \Linker\Tools\Planner\Transport(static function ($url, $args) {
        if (str_ends_with($url, '/assets/read')) {
            $data = array('id' => 'fixture-asset', 'project_id' => 'fixture-project', 'purpose' => 'planning_pv_series_csv_v1', 'media_type' => 'text/csv', 'content_sha256' => 'SHA');
            return array('response' => array('code' => 200), 'headers' => array('content-type' => 'application/json'), 'body' => wp_json_encode($data));
        }
        if (str_ends_with($url, '/assets/content') && true === ($args['stream'] ?? false)) {
            file_put_contents($args['filename'], base64_decode('BYTES', true));
            return array('response' => array('code' => 200), 'headers' => array('content-type' => 'application/octet-stream'), 'body' => '');
        }
        return new WP_Error('fixture_unexpected_request');
    });
    $command = array('schema_version' => 1, 'project_id' => 'fixture-project', 'asset_id' => 'fixture-asset', 'series_csv' => true);
    $result = \Linker\Tools\Planner\SeriesDownload::fetch(new \Linker\Tools\Planner\Principal('guest', 'fixture'), $command, $transport);
    if (is_wp_error($result)) { status_header(502); echo 'series failed'; exit; }
    header('Content-Type: text/csv');
    $result->output();
    exit;
});
PROBE;
		$code   = str_replace( array( 'TOKEN', 'SHA', 'BYTES' ), array( $token, hash( 'sha256', $bytes ), base64_encode( $bytes ) ), $code ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Fixture bytes only.
		$handle = fopen( $probe, 'x' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Exclusive test-owned plugin.
		$this->assertNotFalse( $handle );
		try {
			$this->assertSame( strlen( $code ), fwrite( $handle, $code ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- Write only the fixture-owned file.
			fclose( $handle ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Close the fixture-owned file.
			chmod( $probe, 0600 ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod -- Fixture-private file.
			$response = wp_remote_get(
				add_query_arg( 'linker_series_fixture', $token, home_url( '/' ) ),
				array(
					'timeout'     => 20,
					'redirection' => 0,
				)
			);
			$this->assertNotInstanceOf( \WP_Error::class, $response );
			$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
			$this->assertSame( $bytes, wp_remote_retrieve_body( $response ) );
		} finally {
			unlink( $probe ); // phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- Remove only the fixture-owned plugin.
		}
	}
}

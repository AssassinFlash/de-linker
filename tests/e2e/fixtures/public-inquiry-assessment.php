<?php
/**
 * Local classifier answer for the public-inquiry browser fixture.
 *
 * Loaded by a temporary mu-plugin so the web request and its assessment
 * loopback see the same answer. It never writes a mail job and never calls a model.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\E2E;

defined( 'ABSPATH' ) || exit;

/**
 * Deterministic normal verdict for this fixture's classifier call.
 */
final class PublicInquiryAssessment {

	/**
	 * Option the browser fixture sets while its inquiries may be classified.
	 */
	public const OPTION = 'linker_246_assessment_fixture';

	/**
	 * Answers only this fixture's assessment call. Isolation keeps a non-false result,
	 * so the request never leaves the machine.
	 *
	 * @param mixed                $pre  Earlier HTTP result.
	 * @param array<string, mixed> $args Request arguments.
	 * @param string               $url  Destination.
	 * @return mixed
	 */
	public static function filter( mixed $pre, array $args, string $url ): mixed {
		if ( ! self::applies( $url ) ) {
			return $pre;
		}
		$raw     = (string) ( $args['body'] ?? '' );
		$body    = json_decode( $raw, true );
		$email   = is_array( $body ) ? ( $body['state']['submission']['billing']['email'] ?? '' ) : '';
		$binding = is_array( $body ) ? ( $body['binding'] ?? null ) : null;
		$owned   = is_string( $email ) && 1 === preg_match( '/\Atester246-[A-Za-z0-9-]+@example\.test\z/', $email );
		if ( ! $owned && ( ! str_contains( $raw, 'tester246-' ) || ! str_contains( $raw, '@example.test' ) ) ) {
			return $pre;
		}
		if ( ! is_array( $binding ) ) {
			return new \WP_Error( 'linker_e2e_assessment_fixture', 'The fixture assessment request had no binding.' );
		}
		$verdict = dirname( __DIR__, 3 ) . '/plugins/linker-commerce/tests/fixtures/NormalMailAuthorizationFixture.php';
		if ( ! is_readable( $verdict ) ) {
			return new \WP_Error( 'linker_e2e_assessment_fixture', 'The local verdict fixture is not readable.' );
		}
		require_once $verdict;
		return array(
			'response' => array(
				'code'    => 200,
				'message' => 'OK',
			),
			'body'     => wp_json_encode( \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::verdict( $binding ) ),
		);
	}

	/**
	 * Whether this request is the fixture's classifier call.
	 *
	 * @param string $url Destination.
	 */
	private static function applies( string $url ): bool {
		if ( 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
			return false;
		}
		if ( '1' !== (string) get_option( self::OPTION, '' ) ) {
			return false;
		}
		return str_ends_with( $url, '/inquiries/assess' );
	}

	/**
	 * Publish the answer to subsequent web and loopback requests.
	 *
	 * @throws \RuntimeException When this is not an isolated local site or the loader cannot be written.
	 */
	public static function install(): void {
		if ( 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
			throw new \RuntimeException( 'The public-inquiry assessment fixture requires the local instance.' );
		}
		$source = __DIR__ . '/public-inquiry-assessment.php';
		if ( ! is_readable( $source ) ) {
			throw new \RuntimeException( 'The public-inquiry assessment fixture is missing.' );
		}
		self::remove();
		// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- PHP literal for an ephemeral local loader, not debug output.
		$loader = "<?php\ndeclare( strict_types = 1 );\ndefined( 'ABSPATH' ) || exit;\nrequire " . var_export( $source, true ) . ";\n";
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- Local mu-plugin outside WP_Filesystem's scope.
		if ( false === file_put_contents( self::loader(), $loader ) ) {
			throw new \RuntimeException( 'The public-inquiry assessment fixture could not be installed.' );
		}
		update_option( self::OPTION, '1', false );
	}

	/**
	 * Remove the loader and the switch. A missing loader is already clean.
	 */
	public static function remove(): void {
		$loader = self::loader();
		if ( is_file( $loader ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- Local mu-plugin outside WP_Filesystem's scope.
			unlink( $loader );
		}
		delete_option( self::OPTION );
	}

	/**
	 * Stable loader path so cleanup cannot miss a random filename.
	 */
	private static function loader(): string {
		return WPMU_PLUGIN_DIR . '/999-linker-public-inquiry-assessment.php';
	}

}

add_filter( 'pre_http_request', array( PublicInquiryAssessment::class, 'filter' ), PHP_INT_MAX - 1, 3 );

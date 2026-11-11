<?php
/**
 * A local engine answer for the inquiry report download chain.
 *
 * The production chain is the one under test: the native REST route, the
 * stored order context, the Tools reader and its hash comparisons. Only the
 * engine on the other side of the private transport is this fixture, so a
 * browser or an integration test can read a real report without a service.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

/**
 * Answers handoffs/read and assets/content for one stored report.
 *
 * Installed by a temporary mu-plugin, so the PHP process that serves the
 * download sees the same answer as the test that prepared it.
 */
final class PlanningReportEngineFixture {

	/**
	 * The option holding this fixture's frozen handoff and PDF.
	 */
	public const OPTION = 'linker_planning_report_fixture';

	/**
	 * The service address the transport posts to while the fixture is installed.
	 */
	public const PLANNER = 'http://127.0.0.1:9/planning';

	/**
	 * Install the answer for one report and return the restore.
	 *
	 * @param array<string,mixed> $handoff The engine-owned handoff, as stored.
	 * @param string              $pdf     The frozen PDF bytes.
	 * @return callable(): void Restore.
	 * @throws \RuntimeException Not an isolated local instance, or the loader could not be written.
	 */
	public static function install( array $handoff, string $pdf ): callable {
		self::assert_local();
		self::remove();
		$previous = get_option( 'linker_planner_url' );
		$planner  = is_string( $previous ) && '' !== $previous ? $previous : self::PLANNER;
		update_option(
			self::OPTION,
			array(
				'handoff'              => $handoff,
				'pdf'                  => base64_encode( $pdf ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Synthetic fixture bytes through a text option.
				'planner'              => $planner,
				'refuse_handoff'       => false,
				'refuse_content'       => false,
				'replace_content'      => false,
				'previous_planner_url' => false === $previous ? '' : (string) $previous,
			),
			false
		);
		// The instance's own service address stays as it is; only an instance
		// that has none is given one to answer on.
		if ( $planner !== $previous ) {
			update_option( 'linker_planner_url', $planner, false );
		}
		// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- PHP literal for an ephemeral local loader, not debug output.
		$loader = "<?php\ndeclare( strict_types = 1 );\ndefined( 'ABSPATH' ) || exit;\nrequire " . var_export( self::source(), true ) . ";\n";
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- Local mu-plugin outside WP_Filesystem's scope.
		if ( false === file_put_contents( self::loader(), $loader ) ) {
			throw new \RuntimeException( 'The planning report fixture could not be installed.' );
		}
		return static function (): void {
			self::remove();
		};
	}

	/**
	 * Change what the engine answers without reinstalling the loader.
	 *
	 * @param array{refuse_handoff?: bool, refuse_content?: bool, replace_content?: bool} $changes Answers to switch.
	 * @throws \RuntimeException The fixture is not installed.
	 */
	public static function answer( array $changes ): void {
		$state = get_option( self::OPTION );
		if ( ! is_array( $state ) ) {
			throw new \RuntimeException( 'The planning report fixture is not installed.' );
		}
		if ( array_key_exists( 'refuse_handoff', $changes ) ) {
			$state['refuse_handoff'] = (bool) $changes['refuse_handoff'];
		}
		if ( array_key_exists( 'refuse_content', $changes ) ) {
			$state['refuse_content'] = (bool) $changes['refuse_content'];
		}
		if ( array_key_exists( 'replace_content', $changes ) ) {
			$state['replace_content'] = (bool) $changes['replace_content'];
		}
		update_option( self::OPTION, $state, false );
	}

	/**
	 * Remove the loader and restore the instance's own service address.
	 */
	public static function remove(): void {
		$state = get_option( self::OPTION );
		if ( is_array( $state ) && array_key_exists( 'previous_planner_url', $state ) && ( $state['planner'] ?? null ) !== $state['previous_planner_url'] ) {
			$previous = (string) $state['previous_planner_url'];
			if ( '' === $previous ) {
				delete_option( 'linker_planner_url' );
			} else {
				update_option( 'linker_planner_url', $previous, false );
			}
		}
		if ( is_file( self::loader() ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink -- Local mu-plugin outside WP_Filesystem's scope.
			unlink( self::loader() );
		}
		delete_option( self::OPTION );
	}

	/**
	 * This fixture's own source, required by the loader.
	 */
	private static function source(): string {
		return __FILE__;
	}

	/**
	 * Stable loader path, so a removal cannot miss a random filename.
	 */
	private static function loader(): string {
		return WPMU_PLUGIN_DIR . '/999-linker-planning-report-fixture.php';
	}

	/**
	 * Refuse to run anywhere but an isolated local instance.
	 *
	 * @throws \RuntimeException Not the local instance.
	 */
	private static function assert_local(): void {
		if ( 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
			throw new \RuntimeException( 'The planning report fixture requires the local instance.' );
		}
	}

	/**
	 * Answer this fixture's two service calls and pass every other request on.
	 *
	 * @param mixed                $pre  Earlier short-circuit.
	 * @param array<string, mixed> $args Request arguments.
	 * @param string               $url  Destination.
	 * @return mixed
	 */
	public static function filter( mixed $pre, array $args, string $url ): mixed {
		if ( false !== $pre ) {
			return $pre;
		}
		$state = get_option( self::OPTION );
		if ( ! is_array( $state ) || ! is_array( $state['handoff'] ?? null ) || ! is_string( $state['pdf'] ?? null ) || ! is_string( $state['planner'] ?? null ) ) {
			return $pre;
		}
		$base = rtrim( (string) $state['planner'], '/' ) . '/';
		if ( ! str_starts_with( $url, $base ) ) {
			return $pre;
		}
		$path = substr( $url, strlen( $base ) );
		if ( 'handoffs/read' === $path ) {
			if ( ! empty( $state['refuse_handoff'] ) ) {
				return self::reply( 404, 'application/json', (string) wp_json_encode( array( 'error' => array( 'code' => 'not_found' ) ) ) );
			}
			return self::reply( 200, 'application/json', (string) wp_json_encode( $state['handoff'] ) );
		}
		if ( 'assets/content' === $path ) {
			if ( ! empty( $state['refuse_content'] ) ) {
				return self::reply( 404, 'application/json', (string) wp_json_encode( array( 'error' => array( 'code' => 'not_found' ) ) ) );
			}
			$body = (string) base64_decode( (string) $state['pdf'], true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Synthetic fixture bytes.
			if ( ! empty( $state['replace_content'] ) ) {
				$body = str_replace( 'Catalog', 'Pages', $body );
			}
			return self::reply( 200, 'application/octet-stream', $body );
		}
		return $pre;
	}

	/**
	 * A WordPress HTTP reply.
	 *
	 * @param int    $status HTTP status.
	 * @param string $type   Content type.
	 * @param string $body   Body bytes.
	 * @return array<string,mixed>
	 */
	private static function reply( int $status, string $type, string $body ): array {
		return array(
			'response' => array(
				'code'    => $status,
				'message' => 200 === $status ? 'OK' : 'Refused',
			),
			'headers'  => array( 'content-type' => $type ),
			'body'     => $body,
		);
	}
}

add_filter( 'pre_http_request', array( PlanningReportEngineFixture::class, 'filter' ), PHP_INT_MAX - 5, 3 );

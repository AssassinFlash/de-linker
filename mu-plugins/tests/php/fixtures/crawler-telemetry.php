<?php
/**
 * Isolated WordPress REST and cron doubles for the origin probe.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals, Universal.Files.SeparateFunctionsFromOO, Squiz.Commenting.FunctionComment, Squiz.Commenting.ClassComment -- Minimal native API doubles loaded only by the telemetry unit fixture.
// phpcs:disable Generic.Files.OneObjectStructurePerFile, WooCommerce.Commenting.CommentHooks -- Isolated REST and action doubles share a test process.
// phpcs:disable WordPress.WP.AlternativeFunctions -- Real local files and JSON with no WordPress process.

function add_action( string $hook, callable $callback ): void {}
function add_filter( string $hook, callable $callback ): void {}
function do_action( string $hook, string $value ): void {}
function is_admin(): bool {
	return false; }
function wp_doing_cron(): bool {
	return false; }
function wp_doing_ajax(): bool {
	return false; }
function wp_next_scheduled( string $hook ): int {
	unset( $hook );
	return 1; }
function wp_parse_url( string $url, int $component ): mixed {
	return parse_url( $url, $component ); }
function wp_json_encode( mixed $data, int $flags = 0 ): string|false {
	return json_encode( $data, $flags ); }
function wp_remote_get( string $url ): string {
	++$GLOBALS['linker_crawler_fixture_reads'];
	return $GLOBALS['linker_crawler_fixture_feeds'][ $url ] ?? '';
}
function wp_remote_retrieve_response_code( string $result ): int {
	return '' === $result ? 503 : 200; }
function wp_remote_retrieve_body( string $result ): string {
	return $result; }

if ( ! class_exists( 'WP_REST_Request' ) ) {
	class WP_REST_Request {
		/** Native request/response headers.
		 *
		 * @var array<string,string>
		 */
		private array $headers = array();
		/** Native route.
		 *
		 * @var string
		 */
		private string $route;
		public function __construct( string $method = 'GET', string $route = '' ) {
			$this->route = $route;
		}
		public function get_route(): string {
			return $this->route; }
		public function set_header( string $key, string $value ): void {
			$this->headers[ $key ] = $value; }
		public function get_header( string $key ): ?string {
			return $this->headers[ $key ] ?? null; }
	}
	class WP_HTTP_Response {
		/** Native request/response headers.
		 *
		 * @var array<string,string>
		 */
		private array $headers = array();
		public function header( string $key, string $value ): void {
			$this->headers[ $key ] = $value; }
		/** Read the response headers.
		 *
		 * @return array<string,string>
		 */
		public function get_headers(): array {
			return $this->headers; }
	}
	class WP_REST_Response extends WP_HTTP_Response {}
	class WP_REST_Server {} // phpcs:ignore Generic.Classes.DuplicateClassName.Found -- A separate PHPUnit process owns this REST double.
	class WP_Error {
		/** Initialize a native error response.
		 *
		 * @param array<string,int> $data Status metadata.
		 */
		public function __construct( string $code, string $message, private array $data ) {}
		/** Read error metadata.
		 *
		 * @return array<string,int>
		 */
		public function get_error_data(): array {
			return $this->data; }
	}
}

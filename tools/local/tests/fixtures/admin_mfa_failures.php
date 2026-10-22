<?php
/** Offline API substitutes: executes the actual fixture without loading WordPress. */

declare( strict_types=1 );

if ( defined( 'WPINC' ) ) {
	throw new RuntimeException( 'Offline failure harness must not run inside WordPress.' );
}
define( 'ABSPATH', $argv[2] . '/' );
define( 'LINKER_LOCAL_MAIL_DIR', $argv[2] . '/mail' );
require dirname( __DIR__, 4 ) . '/plugins/linker-commerce/includes/Mail/TestMode.php';
require dirname( __DIR__, 4 ) . '/plugins/linker-commerce/includes/Registration/Approval.php';

class WP_Error {}
class WP_REST_Request {
	public array $params = array();
	public function __construct( string $method ) {}
	public function set_param( string $key, mixed $value ): void { $this->params[ $key ] = $value; }
}
class Two_Factor_Core {
	public const PROVIDER_USER_META_KEY = 'provider';
	public static function enable_provider_for_user( int $id, string $provider ): void {}
}
class Two_Factor_Totp {
	public static function get_instance(): self { return new self(); }
	public static function generate_key(): string { return 'offline-not-a-real-seed'; }
	public static function calc_totp( string $seed ): string { return '123456'; }
	public function is_available_for_user( mixed $user ): bool { return false; }
	public function rest_setup_totp( WP_REST_Request $request ): WP_Error|true {
		if ( 'invalid' === $request->params['code'] || 'totp' === $GLOBALS['fault'] ) { return new WP_Error(); }
		$GLOBALS['factors'][ $request->params['user_id'] ] = true;
		return true;
	}
}
class Two_Factor_Backup_Codes {
	public static function get_instance(): self { return new self(); }
	public function generate_codes( mixed $user ): array { return array( 'offline-code' ); }
}
class WP_Application_Passwords {
	public static function create_new_application_password( int $id, array $args ): WP_Error|array {
		if ( 'application-password' === $GLOBALS['fault'] ) { return new WP_Error(); }
		$GLOBALS['apps'][ $id ] = true;
		return array( 'offline-password' );
	}
}
function home_url(): string { return 'http://127.0.0.1:9999'; }
function wp_parse_url( string $url, int $part ): mixed { return parse_url( $url, $part ); }
function get_option( string $key, mixed $default = false ): mixed { return $GLOBALS['options'][ $key ] ?? $default; }
function wp_cache_delete( mixed ...$args ): void {}
function sanitize_email( string $email ): string { return $email; }
function is_email( string $email ): bool { return false !== filter_var( $email, FILTER_VALIDATE_EMAIL ); }
function is_wp_error( mixed $value ): bool { return $value instanceof WP_Error; }
function wp_generate_password( mixed ...$args ): string { return 'offline-synthetic'; }
function wp_json_encode( mixed $value ): string { return json_encode( $value, JSON_THROW_ON_ERROR ); }
function delete_option( string $key ): void { unset( $GLOBALS['options'][ $key ] ); }
function update_option( string $key, mixed $value, mixed ...$args ): bool {
	if ( 'linker_admin_mfa_fixture' === $key ) {
		$fail = ( 'initial-state-write' === $GLOBALS['fault'] )
			|| ( in_array( $GLOBALS['fault'], array( 'user-state-write', 'failed-user-compensation' ), true ) && count( $value['users'] ) > 0 )
			|| ( 'page-state-write' === $GLOBALS['fault'] && count( $value['created_pages'] ) > 0 )
			|| ( 'late-state-write' === $GLOBALS['fault'] && isset( $value['users']['admin']['application_password'] ) );
		if ( $fail ) { return false; }
	}
	$changed = get_option( $key ) !== $value;
	$GLOBALS['options'][ $key ] = $value;
	return $changed;
}
function wp_insert_user( array $data ): int {
	$id = 100 + count( $GLOBALS['created_users'] );
	$GLOBALS['users'][ $id ] = (object) array( 'ID' => $id );
	$GLOBALS['created_users'][] = $id;
	return $id;
}
function update_user_meta( int $id, mixed ...$args ): void {
	$state = get_option( 'linker_admin_mfa_fixture' );
	if ( ! in_array( $id, array_column( $state['users'], 'id' ), true ) ) { throw new LogicException( 'User ownership was not durable before metadata/provider work.' ); }
}
function wp_delete_user( int $id ): bool {
	$GLOBALS['deleted_users'][] = $id;
	if ( 'failed-user-compensation' === $GLOBALS['fault'] ) { return false; }
	unset( $GLOBALS['users'][ $id ], $GLOBALS['factors'][ $id ], $GLOBALS['apps'][ $id ] );
	return true;
}
function clean_user_cache( int $id ): void {}
function get_user_by( string $field, mixed $value ): mixed { return 'id' === $field ? ( $GLOBALS['users'][ $value ] ?? false ) : false; }
function wp_insert_post( array $data, bool $wp_error = false ): int {
	$id = 1000 + count( $GLOBALS['created_pages'] );
	$GLOBALS['posts'][ $id ] = (object) array( 'ID' => $id );
	$GLOBALS['created_pages'][] = $id;
	return $id;
}
function get_post( int $id ): mixed { return $GLOBALS['posts'][ $id ] ?? null; }
function wp_delete_post( int $id, bool $force = false ): void { $GLOBALS['deleted_pages'][] = $id; unset( $GLOBALS['posts'][ $id ] ); }
function pll_get_post( int $id, string $lang ): int { return in_array( $GLOBALS['fault'], array( 'page-language', 'page-state-write', 'german-language' ), true ) ? 0 : 11; }
function pll_languages_list(): array { return 'page-language' === $GLOBALS['fault'] ? array( 'en' ) : array( 'en', 'de' ); }
function pll_get_post_translations( int $id ): array { return array( 'en' => $id ); }
function pll_save_post_translations( array $translations ): void {}
function pll_set_post_language( int $id, string $lang ): void {
	$state = get_option( 'linker_admin_mfa_fixture' );
	if ( $id >= 1000 && ! in_array( $id, $state['created_pages'], true ) ) { throw new LogicException( 'Page ownership was not durable before language work.' ); }
	if ( 'german-language' === $GLOBALS['fault'] && 'de' === $lang ) { throw new RuntimeException( 'Injected language write failed.' ); }
}
function get_permalink( int $id ): string { return 'http://127.0.0.1:9999/page-' . $id . '/'; }
function wc_get_orders( array $query ): array { return array(); }

$wpdb = new class {
	public string $posts = 'offline_posts';
	public function get_var( string $sql ): int { return 0; }
	public function prepare( string $sql, mixed ...$args ): string { return $sql; }
	public function get_col( string $sql ): array { return array(); }
};
$results = array();
foreach ( array( 'initial-state-write', 'totp', 'application-password', 'page-language', 'german-language', 'user-state-write', 'page-state-write', 'late-state-write', 'failed-user-compensation' ) as $fault ) {
	$GLOBALS['fault'] = $fault;
	$options = array( 'woocommerce_myaccount_page_id' => in_array( $fault, array( 'page-language', 'page-state-write' ), true ) ? 0 : 10, 'linker_commerce_test_mail_to' => 'original@example.test' );
	$users = array( 1 => (object) array( 'ID' => 1 ) );
	$posts = array( 10 => (object) array( 'ID' => 10 ), 11 => (object) array( 'ID' => 11 ) );
	$created_users = $created_pages = $deleted_users = $deleted_pages = $factors = $apps = array();
	$before_options = $options;
	$failure = '';
	try {
		$args = array( 'setup' );
		require $argv[1];
	} catch ( RuntimeException $error ) {
		$failure = $error->getMessage();
	} finally {
		$args = array( 'cleanup' );
		require $argv[1];
	}
	$loud_compensation_failure = 'failed-user-compensation' === $fault && str_contains( $failure, 'new user ID 100; manual local cleanup required' );
	$expected_users = $loud_compensation_failure ? array( 1, 100 ) : array( 1 );
	$passed = '' !== $failure && array_keys( $users ) === $expected_users && array_keys( $posts ) === array( 10, 11 ) && $options === $before_options
		&& ! in_array( 1, $deleted_users, true ) && array() === array_intersect( array( 10, 11 ), $deleted_pages ) && array() === $factors && array() === $apps;
	if ( 'failed-user-compensation' === $fault ) { $passed = $passed && $loud_compensation_failure; }
	$results[] = array( 'case' => $fault, 'passed' => $passed, 'created_users' => count( $created_users ), 'created_pages' => count( $created_pages ), 'preexisting_preserved' => isset( $users[1], $posts[10], $posts[11] ), 'baseline_restored' => ! $loud_compensation_failure, 'manual_cleanup_required_reported' => $loud_compensation_failure );
	if ( ! $passed ) { throw new RuntimeException( 'Offline fixture cleanup failed: ' . $fault . ' / ' . $failure ); }
}
echo json_encode( $results, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR ) . "\n";

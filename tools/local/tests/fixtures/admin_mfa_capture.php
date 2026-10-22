<?php
/** Offline mailbox seam for the real local MFA reset-link fixture. */

declare( strict_types = 1 );

if ( defined( 'WPINC' ) ) {
	throw new RuntimeException( 'The offline capture seam must not load WordPress.' );
}
define( 'LINKER_LOCAL_MAIL_DIR', $argv[2] );
class WP_Error {}
class Two_Factor_Core {}
class SyntheticMfaCaptureDatabase {
	public string $posts = 'synthetic_posts';
	public function prepare( string $sql, mixed ...$args ): string { return $sql; }
	public function get_col( string $sql ): array { return array(); }
}
$wpdb = new SyntheticMfaCaptureDatabase();
function home_url(): string { return 'http://127.0.0.1:9999'; }
function wp_parse_url( string $url, int $component ): mixed { return parse_url( $url, $component ); }
function get_option( string $name ): array {
	return array( 'started' => 0, 'job_marker' => 0, 'users' => array( 'customer' => array( 'id' => 42, 'login' => 'mfa565_offline' ) ) );
}
function check_password_reset_key( string $key, string $login ): object {
	global $argv;
	return $key === $argv[3] && 'mfa565_offline' === $login ? (object) array( 'ID' => (int) $argv[4] ) : new WP_Error();
}
function is_wp_error( mixed $value ): bool { return $value instanceof WP_Error; }
$args = array( 'reset-link', 'customer' );
try {
	require $argv[1];
} catch ( RuntimeException $error ) {
	fwrite( STDERR, $error->getMessage() );
	exit( 1 );
}

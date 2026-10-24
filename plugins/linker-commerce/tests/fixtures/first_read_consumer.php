<?php
/** Independent local AS consumer while another native consumer is inside synthetic IO.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
global $argv;
if ( ! isset( $argv[1], $argv[2], $argv[3], $argv[4] ) ) {
	exit( 2 );
}
require $argv[1] . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() || 'tester246@example.test' !== get_option( Linker\Commerce\Mail\TestMode::OPTION ) ) {
	exit( 3 );
}
global $wpdb;
$linker_commerce_job        = (int) $argv[2];
$linker_commerce_action     = (int) $argv[3];
$linker_commerce_hits       = 0;
$linker_commerce_transports = 0;
$linker_commerce_peer       = new wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false', 999 );
add_filter(
	'query',
	static function ( string $sql ) use ( $linker_commerce_job, $linker_commerce_peer, &$linker_commerce_hits ): string {
		global $wpdb;
		if ( 0 === $linker_commerce_hits && str_starts_with( $sql, 'SELECT' ) && str_contains( $sql, $wpdb->postmeta ) && preg_match( '/\b' . $linker_commerce_job . '\b/', $sql ) ) {
			++$linker_commerce_hits;
			$linker_commerce_peer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
		}
		return $sql;
	},
	999
);
add_filter(
	'pre_wp_mail',
	static function () use ( &$linker_commerce_transports ): bool {
		++$linker_commerce_transports;
		return true;
	},
	-1000
);
ActionScheduler_QueueRunner::instance()->process_action( $linker_commerce_action, 'independent native first-read fixture' );
$wpdb->db_connect( false );
file_put_contents(
	$argv[4],
	(string) wp_json_encode(
		array(
			'hits'       => $linker_commerce_hits,
			'transports' => $linker_commerce_transports,
			'status'     => ActionScheduler::store()->get_status( $linker_commerce_action ),
			'pending'    => as_has_scheduled_action( Linker\Commerce\Mail\Outbox::HOOK, array( $linker_commerce_job ), Linker\Commerce\Mail\Outbox::GROUP ),
		)
	)
);
$linker_commerce_peer->close();

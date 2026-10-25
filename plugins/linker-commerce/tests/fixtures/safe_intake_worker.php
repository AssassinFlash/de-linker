<?php
/**
 * Independent native connections race for the last persistent review slot.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

$linker_commerce_root = getenv( 'LINKER_WP_ROOT' );
if ( false === $linker_commerce_root ) {
	exit( 2 );
}
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Native local bootstrap.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require $linker_commerce_root . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
$linker_commerce_barrier = (string) ( $argv[1] ?? '' );
$linker_commerce_email   = (string) ( $argv[2] ?? '' );
if ( 'negative-cache' === ( $argv[3] ?? '' ) ) {
	// Native per-process options caching is supported with or without Redis.
	// The group change ends with this worker and changes no instance setting.
	wp_cache_add_non_persistent_groups( array( 'options' ) );
	if ( false !== get_option( \Linker\Commerce\Protection\IntakeStore::OPTION ) ) {
		exit( 5 );
	}
	file_put_contents( $linker_commerce_barrier, 'ready' );
}
$_COOKIE[ \Linker\Commerce\Protection\Identity::COOKIE ] = substr( hash( 'sha256', $linker_commerce_email ), 0, 32 );
$_SERVER['REMOTE_ADDR']                                  = '127.0.0.245';
wc_load_cart();
WC()->cart->empty_cart();
$linker_commerce_started = (string) time();
$linker_commerce_post    = array(
	'name'                 => 'Concurrent fixture',
	'email'                => $linker_commerce_email,
	'message'              => 'Please advise on a battery.',
	'consent'              => '1',
	'linker_started'       => $linker_commerce_started,
	'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $linker_commerce_started ),
	'linker_inquiry_nonce' => wp_create_nonce( \Linker\Commerce\Inquiry\Handler::ACTION ),
	'linker_request_id'    => wp_generate_uuid4(),
	'linker_proof'         => '',
	'linker_draft_hash'    => WC()->cart->get_cart_hash(),
);
$linker_commerce_until   = microtime( true ) + 5;
while ( 'go' !== file_get_contents( $linker_commerce_barrier ) && microtime( true ) < $linker_commerce_until ) {
	usleep( 10000 );
}
if ( 'negative-cache' === ( $argv[3] ?? '' ) ) {
	// Exercise the actual intake/native writer boundary with a prewarmed cache.
	// Business's earlier Ledger lookup happens to invalidate notoptions today;
	// the intake store itself cannot depend on that unrelated cache side effect.
	$linker_commerce_details = \Linker\Commerce\Contact\Submission::from_post( $linker_commerce_post, false );
	$linker_commerce_subject = \Linker\Commerce\Protection\Identity::current();
	if ( is_wp_error( $linker_commerce_details ) || is_wp_error( $linker_commerce_subject ) ) {
		exit( 6 );
	}
	$linker_commerce_payload = array(
		'details' => get_object_vars( $linker_commerce_details ),
		'draft'   => $linker_commerce_post['linker_draft_hash'],
	);
	$linker_commerce_hash    = \Linker\Commerce\Protection\Fingerprint::make( $linker_commerce_subject, 'inquiry', $linker_commerce_payload );
	if ( is_wp_error( $linker_commerce_hash ) ) {
		exit( 7 );
	}
	$linker_commerce_result = \Linker\Commerce\Protection\Intake::run(
		'verification',
		'inquiry',
		$linker_commerce_post['linker_request_id'],
		$linker_commerce_hash,
		$linker_commerce_subject,
		$linker_commerce_payload,
		array( new \Linker\Commerce\Protection\Allowance( 'fixture_initialization', $linker_commerce_subject->browser, 2, HOUR_IN_SECONDS ) ),
		array(),
		array(),
		static fn () => ( new \Linker\Commerce\Inquiry\Sender() )->request( $linker_commerce_details, $linker_commerce_post )
	);
} else {
	$linker_commerce_result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $linker_commerce_post );
}
echo wp_json_encode( is_wp_error( $linker_commerce_result ) ? array( 'error' => $linker_commerce_result->get_error_code() ) : array( 'order' => $linker_commerce_result->get_id() ) );

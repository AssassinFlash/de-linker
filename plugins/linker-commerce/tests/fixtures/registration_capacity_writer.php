<?php
/**
 * Native second-process public registration with a controlled pre-create pause.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.NonceVerification, WordPress.Security.ValidatedSanitizedInput, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks, WordPress.PHP.DiscouragedPHPFunctions -- Test-only native request/process harness; real validation hooks remain under test.

require dirname( __DIR__ ) . '/php/integration-bootstrap.php';

$linker_commerce_fixture = json_decode( (string) stream_get_contents( STDIN ), true );
if ( ! is_array( $linker_commerce_fixture ) ) {
	exit( 2 );
}
foreach ( array(
	'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
	'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
	'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
	'LINKER_TURNSTILE_HOSTNAME'     => 'localhost',
) as $linker_commerce_key => $linker_commerce_value ) {
	putenv( $linker_commerce_key . '=' . $linker_commerce_value );
}
$_COOKIE[ \Linker\Commerce\Protection\Identity::COOKIE ] = $linker_commerce_fixture['cookie'];
$_SERVER['REMOTE_ADDR']                                  = $linker_commerce_fixture['address'];
$_POST                      = $linker_commerce_fixture['post'];
$linker_commerce_vies_calls = 0;
add_filter(
	'pre_http_request',
	static function ( $pre, $args, $url ) use ( &$linker_commerce_vies_calls ) {
		if ( \Linker\Commerce\Registration\ViesClient::ENDPOINT === $url ) {
			++$linker_commerce_vies_calls;
			return array(
				'response' => array( 'code' => 200 ),
				'headers'  => array(),
				'body'     => '{"valid":true}',
			);
		}
		return $pre;
	},
	1,
	3
);
if ( isset( $linker_commerce_fixture['edit_user'] ) ) {
	wp_set_current_user( (int) $linker_commerce_fixture['edit_user'] );
	add_action(
		'woocommerce_before_customer_object_save',
		static function () use ( $linker_commerce_fixture ): void {
			file_put_contents( $linker_commerce_fixture['ready'], 'ready' );
			$until = microtime( true ) + 15;
			while ( ! file_exists( $linker_commerce_fixture['release'] ) && microtime( true ) < $until ) {
				usleep( 20000 ); }
			if ( ! file_exists( $linker_commerce_fixture['release'] ) ) {
				exit( 3 ); }
		},
		PHP_INT_MAX
	);
	$linker_commerce_customer = new WC_Customer( (int) $linker_commerce_fixture['edit_user'] );
	$linker_commerce_customer->set_billing_company( $linker_commerce_fixture['company'] );
	$linker_commerce_customer->save();
	echo wp_json_encode( array( 'saved' => get_user_meta( $linker_commerce_customer->get_id(), 'billing_company', true ) ) );
	exit;
}
$linker_commerce_started = microtime( true );
$linker_commerce_errors  = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $_POST['password'], $_POST['email'] );
if ( $linker_commerce_errors->has_errors() ) {
	echo wp_json_encode(
		array(
			'created'    => 0,
			'errors'     => $linker_commerce_errors->get_error_codes(),
			'vies_calls' => $linker_commerce_vies_calls,
			'elapsed'    => microtime( true ) - $linker_commerce_started,
		)
	);
	exit;
}
if ( isset( $linker_commerce_fixture['ready'], $linker_commerce_fixture['release'] ) ) {
	file_put_contents( $linker_commerce_fixture['ready'], 'ready' );
	$linker_commerce_until = microtime( true ) + 15;
	while ( ! file_exists( $linker_commerce_fixture['release'] ) && microtime( true ) < $linker_commerce_until ) {
		usleep( 20000 );
	}
	if ( ! file_exists( $linker_commerce_fixture['release'] ) ) {
		exit( 3 );
	}
}
$linker_commerce_user = wc_create_new_customer( $_POST['email'], '', $_POST['password'] );
echo wp_json_encode(
	array(
		'notices'    => is_int( $linker_commerce_user ) ? \Linker\Commerce\Registration\RegistrationNotices::read( $linker_commerce_user ) : null,
		'created'    => is_int( $linker_commerce_user ) ? $linker_commerce_user : 0,
		'errors'     => is_wp_error( $linker_commerce_user ) ? $linker_commerce_user->get_error_codes() : array(),
		'vies_calls' => $linker_commerce_vies_calls,
		'elapsed'    => microtime( true ) - $linker_commerce_started,
	)
);

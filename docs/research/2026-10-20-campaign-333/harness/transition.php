<?php
/**
 * Pending, approve-without-relogin, reject, re-approve for one local customer.
 *
 * The login is c333-transition. Users 43, 44 and 45 are not touched. Mail is
 * short-circuited. The shutdown hook deletes the user if this process dies.
 * The password is never printed.
 *
 * CommerceState::visitor_reason has no rejected branch. A signed-in rejected
 * account reads the restricted sentence. The customer-visible check is
 * wp_authenticate, which returns linker_approval_rejected.
 *
 * Usage: just wp c333 eval-file <absolute path>
 */

require __DIR__ . '/catalog.php';
require_once ABSPATH . 'wp-admin/includes/user.php';

add_filter(
	'pre_wp_mail',
	static function () {
		return true;
	}
);

$login = 'c333-transition';
register_shutdown_function(
	static function () use ( $login ): void {
		require_once ABSPATH . 'wp-admin/includes/user.php';
		$user = get_user_by( 'login', $login );
		if ( $user instanceof WP_User ) {
			wp_delete_user( $user->ID );
		}
	}
);

/**
 * @return array{price_line: string, price_visible: bool, price: string}
 */
function c333_priced_view(): array {
	$priced   = c333_product_ids()['priced'];
	$response = c333_rest(
		'GET',
		'/wp-abilities/v1/abilities/linker/get-product/run',
		array(
			'input' => array(
				'product_id' => $priced,
				'lang'       => 'en',
			),
		),
		array(),
		false
	);
	$commerce = c333_commerce( $response );
	return array(
		'price_line'    => (string) ( $commerce['price_line'] ?? '' ),
		'price_visible' => (bool) ( $commerce['price_visible'] ?? false ),
		'price'         => isset( $commerce['price'] ) ? (string) $commerce['price'] : '',
	);
}

/**
 * The next request: the cookie WordPress would have sent, then the ability.
 *
 * @return array{valid: bool, commerce: array{price_line: string, price_visible: bool, price: string}}
 */
function c333_view_as_cookie( string $cookie ): array {
	wp_set_current_user( 0 );
	$valid   = wp_validate_auth_cookie( $cookie, 'logged_in' );
	$user_id = is_int( $valid ) ? $valid : 0;
	if ( $user_id > 0 ) {
		wp_set_current_user( $user_id );
	}
	return array(
		'valid'    => $user_id > 0,
		'commerce' => c333_priced_view(),
	);
}

try {
	$existing = get_user_by( 'login', $login );
	if ( $existing instanceof WP_User ) {
		wp_delete_user( $existing->ID );
	}

	$password = wp_generate_password( 24, true, true );
	$user_id  = wp_insert_user(
		array(
			'user_login' => $login,
			'user_pass'  => $password,
			'user_email' => 'c333-transition@example.com',
			'role'       => 'customer',
		)
	);
	if ( is_wp_error( $user_id ) ) {
		throw new RuntimeException( 'wp_insert_user failed' );
	}
	$user_id = (int) $user_id;
	$created = get_userdata( $user_id );
	$roles   = $created instanceof WP_User ? array_values( $created->roles ) : array();

	$approval = new \Linker\Commerce\Registration\Approval();
	$approval->set( $user_id, \Linker\Commerce\Registration\Approval::PENDING );

	$expiration = time() + DAY_IN_SECONDS;
	$session    = WP_Session_Tokens::get_instance( $user_id )->create( $expiration );
	$cookie     = wp_generate_auth_cookie( $user_id, $expiration, 'logged_in', $session );
	$pending    = c333_view_as_cookie( $cookie );

	// The same cookie. No new login. Approval does not destroy sessions.
	$approval->set( $user_id, \Linker\Commerce\Registration\Approval::APPROVED );
	$approved = c333_view_as_cookie( $cookie );

	$approval->set( $user_id, \Linker\Commerce\Registration\Approval::REJECTED, 'c333 harness rejection' );
	$rejected_cookie = c333_view_as_cookie( $cookie );
	$auth            = wp_authenticate( $login, $password );
	$auth_code       = is_wp_error( $auth ) ? $auth->get_error_code() : '';

	wp_set_current_user( $user_id );
	$forced = c333_priced_view();

	$approval->set( $user_id, \Linker\Commerce\Registration\Approval::APPROVED );
	$again    = wp_authenticate( $login, $password );
	$again_ok = $again instanceof WP_User && (int) $again->ID === $user_id;
	wp_set_current_user( $user_id );
	$reopened = c333_priced_view();

	wp_set_current_user( 0 );
	wp_delete_user( $user_id );
	$gone = false === get_user_by( 'login', $login );

	echo wp_json_encode(
		array(
			'roles'                  => $roles,
			'pending_cookie_valid'   => $pending['valid'],
			'pending_commerce'       => $pending['commerce'],
			'approved_cookie_valid'  => $approved['valid'],
			'approved_commerce'      => $approved['commerce'],
			'rejected_cookie_valid'  => $rejected_cookie['valid'],
			'rejected_auth_code'     => $auth_code,
			'rejected_commerce'      => $forced,
			'reapproved_auth_ok'     => $again_ok,
			'reapproved_commerce'    => $reopened,
			'user_gone'              => $gone,
		)
	);
	echo "\n";
} catch ( Throwable $failure ) {
	fwrite( STDERR, 'c333-throw ' . $failure::class . ' ' . $failure->getMessage() . ' @ ' . $failure->getFile() . ':' . $failure->getLine() . "\n" );
	echo '{"error":' . wp_json_encode( $failure->getMessage() ) . "}\n";
	exit( 1 );
}

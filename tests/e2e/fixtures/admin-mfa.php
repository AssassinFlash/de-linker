<?php
/**
 * Synthetic local identities for native Two-Factor HTTP/browser acceptance.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Mail\TestMode;

( static function ( array $args ): void {
	if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
		throw new RuntimeException( 'An isolated local instance is required.' );
	}
	if ( ! class_exists( 'Two_Factor_Core' ) ) {
		throw new RuntimeException( 'Install the official Two-Factor 0.17.0 dependency first.' );
	}
	$key      = 'linker_admin_mfa_fixture';
	$mode     = $args[0] ?? '';
	$state    = get_option( $key );
	$save     = static function ( array $next ) use ( $key ): void {
		update_option( $key, $next, false );
		wp_cache_delete( $key, 'options' );
		if ( get_option( $key ) !== $next ) {
			throw new RuntimeException( 'MFA fixture ownership could not be persisted.' );
		}
	};
	$remember = static function ( array $next, string $kind, int $id ) use ( $save ): void {
		try {
			$save( $next );
		} catch ( Throwable $error ) {
			// Only this just-created object is compensating cleanup. Previously
			// persisted ownership is left for the caller's normal finally cleanup.
			if ( 'user' === $kind ) {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
				clean_user_cache( $id );
				$exists = (bool) get_user_by( 'id', $id );
			} else {
				wp_delete_post( $id, true );
				$exists = (bool) get_post( $id );
			}
			if ( $exists ) {
				throw new RuntimeException( sprintf( 'MFA fixture compensation failed for new %s ID %d; manual local cleanup required.', $kind, $id ), 0, $error );
			}
			throw $error;
		}
	};
	if ( 'exists' === $mode ) {
		echo wp_json_encode( false !== $state );
		return;
	}
	if ( 'setup' === $mode ) {
		if ( false !== $state ) {
			throw new RuntimeException( 'Clean up the existing MFA fixture first.' );
		}
		global $wpdb;
		$state = array(
			'users'          => array(),
			'started'        => time(),
			'job_marker'     => (int) $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts} WHERE post_type='linker_mail_job'" ),
			'test_mode'      => get_option( TestMode::OPTION ),
			'created_pages'  => array(),
			'account_option' => get_option( 'woocommerce_myaccount_page_id' ),
		);
		$save( $state );
		if ( ! ( new TestMode() )->enable( 'tester565@example.test' ) ) {
			throw new RuntimeException( 'Local tester mail routing could not be enabled.' );
		}
		$account = (int) get_option( 'woocommerce_myaccount_page_id' );
		if ( ! get_post( $account ) ) {
			$account = wp_insert_post(
				array(
					'post_type'    => 'page',
					'post_status'  => 'publish',
					'post_title'   => 'My account',
					'post_name'    => 'my-account',
					'post_content' => '[woocommerce_my_account]',
				),
				true
			);
			if ( is_wp_error( $account ) || $account <= 0 ) {
				throw new RuntimeException( 'Synthetic account page creation failed.' );
			}
			$state['created_pages'][] = $account;
			$remember( $state, 'page', $account );
			update_option( 'woocommerce_myaccount_page_id', $account );
			if ( function_exists( 'pll_set_post_language' ) ) {
				pll_set_post_language( $account, 'en' ); }
		}
		$german = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $account, 'de' ) : 0;
		if ( ! $german ) {
			if ( ! function_exists( 'pll_save_post_translations' ) || ! in_array( 'de', pll_languages_list(), true ) ) {
				throw new RuntimeException( 'Configure the native EN/DE languages before the MFA test.' ); }
			$state['account_translations'] = pll_get_post_translations( $account );
			$german                        = wp_insert_post(
				array(
					'post_type'    => 'page',
					'post_status'  => 'publish',
					'post_title'   => 'Mein Konto',
					'post_name'    => 'mein-konto',
					'post_content' => '[woocommerce_my_account]',
				),
				true
			);
			if ( is_wp_error( $german ) || $german <= 0 ) {
				throw new RuntimeException( 'Synthetic German account page creation failed.' );
			}
			$state['created_pages'][] = $german;
			$remember( $state, 'page', $german );
			pll_set_post_language( $german, 'de' );
			pll_save_post_translations(
				array(
					'en' => $account,
					'de' => $german,
				)
			);
		}
		$state['paths'] = array(
			'en' => wp_parse_url( get_permalink( $account ), PHP_URL_PATH ),
			'de' => wp_parse_url( get_permalink( $german ), PHP_URL_PATH ),
		);
		$save( $state );
		foreach ( array(
			'admin'     => 'administrator',
			'woo_admin' => 'administrator',
			'customer'  => 'customer',
			'pending'   => 'customer',
		) as $label => $role ) {
			$login    = 'mfa565_' . $label . '_' . wp_generate_password( 6, false, false );
			$password = wp_generate_password( 32, true, false );
			$id       = wp_insert_user(
				array(
					'user_login'   => $login,
					'user_pass'    => $password,
					'user_email'   => $login . '@example.test',
					'role'         => $role,
					'display_name' => 'MFA local ' . $label,
				)
			);
			if ( is_wp_error( $id ) || $id <= 0 ) {
				throw new RuntimeException( 'Synthetic user creation failed.' );
			}
			$state['users'][ $label ] = array(
				'id'       => $id,
				'login'    => $login,
				'password' => $password,
			);
			$remember( $state, 'user', $id );
			update_user_meta( $id, Approval::STATUS_META, 'pending' === $label ? 'pending' : 'approved' );
			if ( 'administrator' === $role ) {
				$totp    = Two_Factor_Totp::get_instance();
				$seed    = Two_Factor_Totp::generate_key();
				$request = new WP_REST_Request( 'POST' );
				$request->set_param( 'user_id', $id );
				$request->set_param( 'key', $seed );
				$request->set_param( 'code', 'invalid' );
				$invalid = $totp->rest_setup_totp( $request );
				$state['users'][ $label ]['invalid_setup_refused'] = is_wp_error( $invalid ) && ! $totp->is_available_for_user( get_user_by( 'id', $id ) );
				$request->set_param( 'code', Two_Factor_Totp::calc_totp( $seed ) );
				$request->set_param( 'enable_provider', true );
				$result = $totp->rest_setup_totp( $request );
				if ( is_wp_error( $result ) ) {
					throw new RuntimeException( 'Native TOTP setup failed.' );
				}
				Two_Factor_Core::enable_provider_for_user( $id, 'Two_Factor_Backup_Codes' );
				update_user_meta( $id, Two_Factor_Core::PROVIDER_USER_META_KEY, 'Two_Factor_Totp' );
				$state['users'][ $label ]['seed']   = $seed;
				$state['users'][ $label ]['backup'] = Two_Factor_Backup_Codes::get_instance()->generate_codes( get_user_by( 'id', $id ) );
				$app                                = WP_Application_Passwords::create_new_application_password( $id, array( 'name' => 'MFA synthetic local reader' ) );
				if ( is_wp_error( $app ) ) {
					throw new RuntimeException( 'Synthetic application password setup failed.' ); }
				$state['users'][ $label ]['application_password'] = $app[0];
			}
			$save( $state );
		}
		echo wp_json_encode( $state );
		return;
	}
	if ( 'cleanup' === $mode && false === $state ) {
		return; // Initial ownership write may fail before any object exists.
	}
	if ( ! is_array( $state ) ) {
		throw new RuntimeException( 'MFA fixture is not set up.' );
	}
	if ( 'track-email' === $mode || 'records' === $mode ) {
		$email = $args[1] ?? '';
		if ( ! str_starts_with( $email, 'mfa565_' ) || ! str_ends_with( $email, '@example.test' ) || ! is_email( $email ) ) {
			throw new RuntimeException( 'Only this fixture synthetic email namespace is permitted.' ); }
		$state['external_emails'] = array_unique( array_merge( $state['external_emails'] ?? array(), array( $email ) ) );
		global $wpdb;
		$state['job_marker'] = $state['job_marker'] ?? (int) $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts} WHERE post_type='linker_mail_job'" );
		$save( $state );
		$user   = get_user_by( 'email', $email );
		$orders = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		echo wp_json_encode(
			array(
				'user_exists'     => (bool) $user,
				'user_status'     => $user ? ( new Approval() )->status( $user->ID ) : null,
				'user_has_factor' => $user ? Two_Factor_Core::is_user_using_two_factor( $user ) : false,
				'orders'          => array_map(
					static fn( $order ) => array(
						'customer_id'     => $order->get_customer_id(),
						'held_for_review' => (bool) $order->get_meta( \Linker\Commerce\Protection\Intake::META ),
						'ledger'          => ( function () use ( $order ) {
							$journal = json_decode( (string) get_option( \Linker\Commerce\Protection\Ledger::OPTION, '{}' ), true );
							$id = $order->get_meta( \Linker\Commerce\Protection\BusinessRecord::REQUEST );
							$receipt = $journal['receipts'][ $id ] ?? array();
							return array_merge( array_intersect_key( $receipt, array_flip( array( 'status', 'purpose', 'created_at', 'outcome' ) ) ), array( 'verified_parent_count' => count( array_filter( $journal['receipts'] ?? array(), static fn( $verification ) => ( $verification['consumed_by'] ?? '' ) === $id && 1 === $verification['outcome'] && str_starts_with( $verification['purpose'], 'verification_' ) ) ) ) );
						} )(),
						'id'              => $order->get_id(),
						'source'          => $order->get_meta( '_linker_inquiry_source' ),
						'status'          => $order->get_status(),
					),
					$orders
				),
			)
		);
		return;
	}
	if ( 'reset-link' === $mode ) {
		$label = $args[1] ?? 'customer';
		$user  = $state['users'][ $label ];
		global $wpdb;
		$ids    = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE post_type='linker_mail_job' AND ID>%d ORDER BY ID DESC", $state['job_marker'] ) );
		$bodies = array();
		foreach ( $ids as $id ) {
			$job = ( new \Linker\Commerce\Mail\JobStore() )->load( (int) $id );
			if ( $job && in_array( $user['login'] . '@example.test', $job['message']->to, true ) ) {
				$bodies[] = $job['message']->body;
			}
		}
		foreach ( glob( LINKER_LOCAL_MAIL_DIR . '/*.eml' ) as $file ) {
			if ( filemtime( $file ) >= $state['started'] ) {
				$bodies[] = quoted_printable_decode( file_get_contents( $file ) );
			}
		}
		foreach ( $bodies as $body ) {
			if ( preg_match( '~https?://[^"\s<>]+[?&](?:amp;)?key=[^"\s<>]+~', $body, $match ) ) {
				$url   = html_entity_decode( $match[0], ENT_QUOTES );
				$query = array();
				parse_str( (string) wp_parse_url( $url, PHP_URL_QUERY ), $query );
				$valid = isset( $query['key'] ) ? check_password_reset_key( $query['key'], $user['login'] ) : new WP_Error( 'missing_key' );
				if ( str_starts_with( $url, home_url() . '/' ) && ! is_wp_error( $valid ) && $valid->ID === $user['id'] ) {
					echo $url; // Synthetic reset token: capture privately, never report.
					return;
				}
			}
		}
		throw new RuntimeException( 'Synthetic reset message link was not captured or queued.' );
	}
	if ( 'read' === $mode ) {
		echo wp_json_encode( $state );
		return;
	}
	if ( 'code' === $mode ) {
		$label = $args[1] ?? 'admin';
		$seed  = $state['users'][ $label ]['seed'];
		if ( 'wrong' === ( $args[2] ?? '' ) ) {
			foreach ( array( '000000', '111111', '222222' ) as $code ) {
				if ( ! Two_Factor_Totp::is_valid_authcode( $seed, $code ) ) {
					echo $code;
					return;
				}
			}
		}
		echo Two_Factor_Totp::calc_totp( $seed );
		return;
	}
	if ( 'status' === $mode ) {
		$out = array();
		foreach ( $state['users'] as $label => $user ) {
			$out[ $label ] = array(
				'two_factor_required' => Two_Factor_Core::is_user_using_two_factor( $user['id'] ),
				'sessions'            => count( WP_Session_Tokens::get_instance( $user['id'] )->get_all() ),
				'backup_remaining'    => Two_Factor_Backup_Codes::codes_remaining_for_user( get_user_by( 'id', $user['id'] ) ),
				'retry_after'         => max( 0, (int) get_user_meta( $user['id'], Two_Factor_Core::USER_RATE_LIMIT_KEY, true ) + Two_Factor_Core::get_user_time_delay( get_user_by( 'id', $user['id'] ) ) - time() ),
				'mfa_sessions'        => count( array_filter( WP_Session_Tokens::get_instance( $user['id'] )->get_all(), static fn( $session ) => isset( $session['two-factor-login'] ) ) ),
			);
		}
		echo wp_json_encode( $out );
		return;
	}
	if ( 'cleanup' === $mode ) {
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( $state['users'] as $user ) {
			wp_delete_user( $user['id'] );
		}
		$emails = array_merge( $state['external_emails'] ?? array(), array_map( static fn( $user ) => $user['login'] . '@example.test', $state['users'] ) );
		foreach ( $emails as $email ) {
			foreach ( wc_get_orders(
				array(
					'billing_email' => $email,
					'limit'         => -1,
				)
			) as $order ) {
				$order->delete( true ); }
			$user = get_user_by( 'email', $email );
			if ( $user ) {
				wp_delete_user( $user->ID ); }
		}
		if ( isset( $state['job_marker'] ) ) {
			global $wpdb;
			$jobs = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE post_type='linker_mail_job' AND ID>%d", $state['job_marker'] ) );
			foreach ( $jobs as $id ) {
				$message = (string) get_post_meta( (int) $id, '_linker_mail_message', true );
				foreach ( $emails as $email ) {
					if ( str_contains( $message, $email ) ) {
						as_unschedule_all_actions( \Linker\Commerce\Mail\Outbox::HOOK, array( (int) $id ), \Linker\Commerce\Mail\Outbox::GROUP );
						wp_delete_post( (int) $id, true );
						break;
					}
				}
			}
		}

		foreach ( $state['created_pages'] ?? array() as $id ) {
			wp_delete_post( $id, true ); }
		if ( isset( $state['account_translations'] ) ) {
			pll_save_post_translations( $state['account_translations'] ); }
		if ( isset( $state['account_option'] ) ) {
			update_option( 'woocommerce_myaccount_page_id', $state['account_option'] ); }
		if ( false === ( $state['test_mode'] ?? false ) ) {
			delete_option( TestMode::OPTION );
		} else {
			update_option( TestMode::OPTION, $state['test_mode'], false ); }
		delete_option( $key );
		return;
	}
	throw new RuntimeException( 'Unknown local MFA fixture operation.' );
} )( $args );

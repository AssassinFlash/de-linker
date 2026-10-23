<?php
/**
 * Disposable native identities and records for the API boundary test.
 *
 * @package Linker\Mu
 */

if ( ! isset( $args ) || ! is_array( $args ) ) {
	throw new RuntimeException( 'Run this local fixture through native WP-CLI eval-file.' );
}

( static function ( array $args ): void {
	if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
		throw new RuntimeException( 'An isolated local native instance is required.' );
	}
	$key   = 'linker_inventory_fixture';
	$state = get_option( $key );
	$save  = static function ( array $next ) use ( $key ): void {
		update_option( $key, $next, false );
		wp_cache_delete( $key, 'options' );
		if ( get_option( $key ) !== $next ) {
			throw new RuntimeException( 'Native fixture ownership could not be persisted.' );
		}
	};
	$mode  = $args[0] ?? '';
	if ( 'exists' === $mode ) {
		echo wp_json_encode( false !== $state );
		return;
	}
	if ( 'ordering' === $mode ) {
		rest_get_server();
		global $wp_filter;
		$order = array(
			'acf_initializer_10'  => false,
			'null_initializer_10' => 10 === has_filter( 'rest_pre_dispatch', 'linker_inventory_null_initializer' ),
			'users_guard_20'      => 20 === has_filter( 'rest_pre_dispatch', 'linker_site_guards_rest_users' ),
			'inventory_priority'  => null,
		);
		foreach ( $wp_filter['rest_pre_dispatch']->callbacks as $priority => $callbacks ) {
			foreach ( $callbacks as $callback ) {
				$function = $callback['function'];
				if ( ! is_array( $function ) || ! is_object( $function[0] ) ) {
					continue;
				}
				if ( is_a( $function[0], 'ACF_Rest_Api' ) && 'initialize' === $function[1] && 10 === $priority ) {
					$order['acf_initializer_10'] = true;
				}
				if ( $function[0] instanceof \Linker\Mu\InventoryAccess && 'dispatch' === $function[1] ) {
					$order['inventory_priority'] = $priority;
				}
			}
		}
		echo wp_json_encode( $order );
		return;
	}
	if ( 'setup' === $mode ) {
		if ( false !== $state ) {
			throw new RuntimeException( 'Explicitly clean the owned inventory fixture first.' );
		}
		if ( ! function_exists( 'pll_languages_list' ) || ! function_exists( 'pll_set_post_language' ) || ! in_array( 'en', pll_languages_list(), true ) ) {
			throw new RuntimeException( 'Configure native EN/DE with linker-i18n setup before the inventory fixture.' );
		}
		$state = array(
			'users'       => array(),
			'posts'       => array(),
			'collections' => array(
				'media'    => array(),
				'products' => array(),
			),
		);
		$save( $state );
		foreach ( array(
			'admin'       => 'administrator',
			'customer'    => 'customer',
			'other_admin' => 'administrator',
		) as $label => $role ) {
			$login    = 'inventory574_' . $label . '_' . wp_generate_password( 8, false, false );
			$password = wp_generate_password( 32, true, false );
			$id       = wp_insert_user(
				array(
					'user_login' => $login,
					'user_pass'  => $password,
					'user_email' => $login . '@example.test',
					'role'       => $role,
				)
			);
			if ( is_wp_error( $id ) ) {
				throw new RuntimeException( 'Synthetic identity creation failed.' );
			}
			$state['users'][ $label ] = array(
				'id'       => $id,
				'login'    => $login,
				'password' => $password,
			);
			try {
				$save( $state );
			} catch ( Throwable $error ) {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
				clean_user_cache( $id );
				if ( get_user_by( 'id', $id ) ) {
					// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Local integer cleanup ID and causal Throwable; no customer HTML or secrets.
					throw new RuntimeException( sprintf( 'New local identity needs manual cleanup: %d', $id ), 0, $error );
				}
				throw $error;
			}
		}
		foreach ( array( 'selected', 'other' ) as $name ) {
			$app = WP_Application_Passwords::create_new_application_password( $state['users']['admin']['id'], array( 'name' => 'Inventory synthetic ' . $name ) );
			if ( is_wp_error( $app ) ) {
				throw new RuntimeException( 'Synthetic application credential creation failed.' );
			}
			$state['applications'][ $name ] = array(
				'password' => $app[0],
				'uuid'     => $app[1]['uuid'],
			);
			$save( $state ); // The already-owned user owns all of its native credential metadata.
		}
		// UUIDs are native per-user identifiers. A synthetic duplicate isolates
		// the user half of the tuple; the secret still comes from native creation.
		$other_user = $state['users']['other_admin']['id'];
		$app        = WP_Application_Passwords::create_new_application_password( $other_user, array( 'name' => 'Inventory synthetic other user' ) );
		if ( is_wp_error( $app ) ) {
			throw new RuntimeException( 'Synthetic other-user credential creation failed.' );
		}
		$items            = WP_Application_Passwords::get_user_application_passwords( $other_user );
		$items[0]['uuid'] = $state['applications']['selected']['uuid'];
		update_user_meta( $other_user, WP_Application_Passwords::USERMETA_KEY_APPLICATION_PASSWORDS, $items );
		if ( null === WP_Application_Passwords::get_user_application_password( $other_user, $items[0]['uuid'] ) ) {
			throw new RuntimeException( 'Synthetic duplicate-UUID tuple was not persisted.' );
		}
		$state['applications']['other_user'] = array(
			'password' => $app[0],
			'uuid'     => $items[0]['uuid'],
		);
		$save( $state );
		$count = (int) ( $args[1] ?? 1 );
		if ( $count < 1 || $count > 201 ) {
			throw new RuntimeException( 'Use the bounded synthetic inventory count.' );
		}
		$uploads   = wp_upload_dir();
		$directory = $uploads['basedir'] . '/inventory574-' . wp_generate_uuid4();
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_mkdir -- Exclusive local fixture namespace; never reuse an existing directory.
		if ( $uploads['error'] || ! mkdir( $directory, 0700 ) ) {
			throw new RuntimeException( 'Exclusive local upload directory creation failed.' );
		}
		$state['directory'] = $directory;
		$state['file']      = $directory . '/fixture.pdf';
		try {
			$save( $state ); // Own the exclusive namespace before creating its only file.
		} catch ( Throwable $error ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_rmdir -- Only the empty directory just created by this run.
			rmdir( $directory );
			if ( is_dir( $directory ) ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Causal Throwable in local CLI only; no customer HTML.
				throw new RuntimeException( 'New local upload directory needs manual cleanup.', 0, $error );
			}
			throw $error;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Exclusive file inside the durably owned local namespace.
		$handle = fopen( $state['file'], 'x' );
		if ( false === $handle ) {
			throw new RuntimeException( 'Exclusive local upload file creation failed.' );
		}
		try {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod -- Private synthetic local fixture.
			chmod( $state['file'], 0600 );
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- Synthetic bytes, not a downloaded or customer document.
			if ( 1234 !== fwrite( $handle, str_pad( "%PDF-1.4\n", 1234 ) ) ) {
				throw new RuntimeException( 'Synthetic local upload could not be written.' );
			}
		} finally {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Close only this fixture's handle.
			fclose( $handle );
		}
		$relative = basename( $directory ) . '/fixture.pdf';
		// One additional row per collection lacks document metadata, like data
		// left by another native smoke test. It stays in the full-response hash.
		foreach ( range( 1, $count + 1 ) as $number ) {
			$attachment = 0;
			foreach ( array( 'attachment', 'product', 'post' ) as $type ) {
				if ( 'post' === $type && 1 !== $number ) {
					continue;
				}
				$id = wp_insert_post(
					array(
						'post_type'      => $type,
						'post_title'     => 'Inventory synthetic ' . $type . ' ' . $number,
						'post_author'    => $state['users']['admin']['id'],
						'post_status'    => 'attachment' === $type ? 'inherit' : ( 'product' === $type ? array( 'publish', 'draft', 'private' )[ $number % 3 ] : 'publish' ),
						'post_mime_type' => 'attachment' === $type ? 'application/pdf' : '',
						'guid'           => 'attachment' === $type ? $uploads['baseurl'] . '/' . $relative : '',
					),
					true
				);
				if ( is_wp_error( $id ) ) {
					throw new RuntimeException( 'Synthetic record creation failed.' );
				}
				$state['posts'][] = $id;
				if ( $number <= $count && ( 'attachment' === $type || 'product' === $type ) ) {
					$state['collections'][ 'attachment' === $type ? 'media' : 'products' ][] = $id;
				}
				try {
					$save( $state );
				} catch ( Throwable $error ) {
					wp_delete_post( $id, true );
					if ( get_post( $id ) ) {
						// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Local integer cleanup ID and causal Throwable; no customer HTML or secrets.
						throw new RuntimeException( sprintf( 'New local record needs manual cleanup: %d', $id ), 0, $error );
					}
					throw $error;
				}
				if ( $number > $count ) {
					if ( 'product' === $type ) {
						pll_set_post_language( $id, 'en' );
					}
					continue;
				}
				if ( 'post' === $type ) {
					$state['sentinel'] = $id;
				} elseif ( 'attachment' === $type ) {
					$attachment = $id;
					update_post_meta( $id, '_wp_attached_file', $relative );
					wp_update_attachment_metadata( $id, array( 'filesize' => 1234 ) );
				} else {
					pll_set_post_language( $id, 'en' );
					$downloads = array(
						'downloads' => array(
							array(
								'download_file'     => $attachment,
								'download_title'    => 'Synthetic manual',
								'download_type'     => 'Manual',
								'download_language' => 'EN',
							),
						),
					);
					update_post_meta( $id, '_tv_legacy_acf_json', wp_json_encode( $downloads ) );
					update_post_meta(
						$id,
						'_linker_de_acf_json',
						wp_json_encode(
							array(
								'downloads' => array(
									array(
										'download_file'  => $attachment,
										'download_title' => 'Synthetisches Handbuch',
									),
								),
							)
						)
					);
					update_post_meta( $id, '_delinker_brand', 'Synthetic' );
					update_post_meta( $id, '_delinker_model', 'Synthetic ' . $number );
				}
			}
		}
		$save( $state );
		echo wp_json_encode( $state );
		return;
	}
	if ( 'cleanup' === $mode ) {
		if ( false === $state ) {
			return;
		}
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( $state['users'] as $user ) {
			wp_delete_user( $user['id'] );
			clean_user_cache( $user['id'] );
			if ( get_user_by( 'id', $user['id'] ) ) {
				throw new RuntimeException( 'Owned local identity was not deleted.' );
			}
		}
		foreach ( $state['posts'] as $id ) {
			wp_delete_post( $id, true );
			if ( get_post( $id ) ) {
				throw new RuntimeException( 'Owned local record was not deleted.' );
			}
		}
		if ( isset( $state['file'], $state['directory'] ) ) {
			wp_delete_file( $state['file'] ); // Also handles failure before the first attachment.
			if ( file_exists( $state['file'] ) ) {
				throw new RuntimeException( 'Owned local upload file was not deleted.' );
			}
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_rmdir -- Remove only the owned, now-empty namespace; never recurse into unexpected files.
			if ( is_dir( $state['directory'] ) && ! rmdir( $state['directory'] ) ) {
				throw new RuntimeException( 'Owned local upload directory was not deleted.' );
			}
		}
		delete_option( 'linker_inventory_fixture_mutations' );
		delete_option( 'linker_inventory_fixture_revocation' );
		delete_option( $key );
		return;
	}
	throw new RuntimeException( 'Unknown native inventory fixture operation.' );
} )( $args );

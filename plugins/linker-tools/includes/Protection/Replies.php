<?php
/**
 * Native private reply receipts: completed retries never redo work.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use WP_Error;
use WP_REST_Response;

/** No raw request is stored; native private posts hold only the returned result. */
final class Replies {
	public const TYPE = 'linker_tool_reply';

	/** Register a non-public native record and bounded daily retention. */
	public function register(): void {
		( new ReplyPrivacy() )->register();
		register_post_type(
			self::TYPE,
			array(
				'public'           => false,
				'show_ui'          => false,
				'rewrite'          => false,
				'supports'         => array(),
				'delete_with_user' => true,
			)
		);
	}

	/**
	 * Allocate an empty native receipt after admission, before work.
	 * Privacy erasure/user deletion can remove it while the work runs.
	 *
	 * @param string $binding Verified identity binding.
	 * @param string $email Optional native-validated guest privacy address.
	 */
	public function open( string $binding, string $email = '' ): int {
		if ( '' === $email && get_current_user_id() > 0 ) {
			$email = (string) wp_get_current_user()->user_email;
		}
		$id = wp_insert_post(
			array(
				'post_type'    => self::TYPE,
				'post_status'  => 'private',
				'post_author'  => get_current_user_id(),
				'post_content' => '',
				'meta_input'   => array(
					'_linker_binding'   => $binding,
					'_linker_recipient' => is_email( $email ) ? \Linker\Commerce\Protection\Identity::recipient( $email ) : '',
					'_linker_expires'   => time() + DAY_IN_SECONDS,
				),
			),
			true
		);
		return is_wp_error( $id ) ? 0 : $id;
	}

	/**
	 * Update only the allocated record; an erased receipt cannot be recreated.
	 *
	 * @param int              $id Native placeholder ID.
	 * @param WP_REST_Response $reply Native response, PDF bytes encoded as JSON.
	 */
	public function finish( int $id, WP_REST_Response $reply ): int {
		if ( self::TYPE !== get_post_type( $id ) ) {
			return 0;
		}
		$data    = $reply->get_data();
		$stored  = array(
			'status'  => $reply->get_status(),
			'headers' => $reply->get_headers(),
			'binary'  => is_string( $data ),
			'data'    => is_string( $data ) ? base64_encode( $data ) : $data, // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Binary PDF bytes inside a native JSON receipt.
		);
		$updated = wp_update_post(
			array(
				'ID'           => $id,
				'post_content' => wp_slash( (string) wp_json_encode( $stored ) ),
			),
			true
		);
		return is_wp_error( $updated ) ? 0 : $updated;
	}

	/**
	 * Authorization is rechecked before restoring an already completed result.
	 *
	 * @param int    $id Ledger-owned native reply ID.
	 * @param string $binding Current identity.
	 */
	public function read( int $id, string $binding ): WP_REST_Response|WP_Error {
		if ( self::TYPE !== get_post_type( $id ) || (int) get_post_meta( $id, '_linker_expires', true ) < time() || ! hash_equals( (string) get_post_meta( $id, '_linker_binding', true ), $binding ) ) {
			return new WP_Error( 'linker_resource_result', __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-tools' ), array( 'status' => 409 ) );
		}
		$stored = json_decode( (string) get_post_field( 'post_content', $id ), true );
		if ( ! is_array( $stored ) || ! isset( $stored['status'], $stored['headers'] ) || ! array_key_exists( 'data', $stored ) ) {
			return new WP_Error( 'linker_resource_result', 'The saved result is unavailable.', array( 'status' => 409 ) );
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Restore the authenticated private PDF response, never executable code.
		return new WP_REST_Response( ! empty( $stored['binary'] ) ? base64_decode( (string) $stored['data'], true ) : $stored['data'], (int) $stored['status'], (array) $stored['headers'] );
	}

	/** Expired receipts hold no reason to retain a copy of a customer's answer. */
	public function expire(): void {
		$ids = get_posts(
			array(
				'post_type'      => self::TYPE,
				'post_status'    => 'any',
				'fields'         => 'ids',
				'posts_per_page' => 1000, // phpcs:ignore WordPress.WP.PostsPerPage.posts_per_page_posts_per_page -- Hourly cleanup can clear more than the journal's daily 10k receipt ceiling.
				'meta_query'     => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- Bounded private native receipt expiry, with no storefront query.
					array(
						'key'     => '_linker_expires',
						'value'   => time(),
						'compare' => '<',
						'type'    => 'NUMERIC',
					),
				),
			)
		);
		foreach ( $ids as $id ) {
			wp_delete_post( (int) $id, true );
		}
	}
}

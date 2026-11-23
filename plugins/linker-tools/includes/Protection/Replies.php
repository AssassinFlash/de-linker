<?php
/**
 * Native private reply receipts: completed retries never redo work.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Ledger;
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
	 * @param string $operation Native request UUID.
	 * @param string $fingerprint Owner-bound semantic input.
	 * @param int    $from Conversation selected before the response writes its cookie.
	 */
	public function open( string $binding, string $email = '', string $operation = '', string $fingerprint = '', int $from = 0 ): int {
		if ( '' === $email && get_current_user_id() > 0 ) {
			$email = (string) wp_get_current_user()->user_email;
		}
		$id = wp_insert_post(
			array(
				'post_type'    => self::TYPE,
				'post_status'  => 'private',
				'post_author'  => get_current_user_id(),
				'post_content' => '',
				'post_name'    => $operation,
				'meta_input'   => array(
					'_linker_binding'   => $binding,
					'_linker_input'     => $fingerprint,
					...( $from > 0 ? array( '_linker_previous_conversation' => $from ) : array() ),
					'_linker_recipient' => is_email( $email ) ? \Linker\Commerce\Protection\Identity::recipient( $email ) : '',
					'_linker_expires'   => time() + DAY_IN_SECONDS,
				),
			),
			true
		);
		return is_wp_error( $id ) ? 0 : $id;
	}

	/** Find the short-lived native operation by its indexed private post slug.
	 *
	 * @param string $operation Native UUID.
	 */
	public function operation( string $operation ): int {
		$post = get_page_by_path( $operation, OBJECT, array( self::TYPE ) );
		return $post instanceof \WP_Post ? $post->ID : 0;
	}

	/** Match a still-live result from before the individual receipt was introduced.
	 *
	 * @param string $operation Validated UUID.
	 * @return array<string,mixed>|null Previous receipt, if still inside its retry window.
	 */
	public function previous( string $operation ): ?array {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Read only the keyed entry of the old journal without taking its write lock.
		$raw   = $wpdb->get_var( $wpdb->prepare( "SELECT JSON_EXTRACT(option_value, %s) FROM {$wpdb->options} WHERE option_name = %s", '$.receipts."' . $operation . '"', Ledger::OPTION ) );
		$entry = is_string( $raw ) ? json_decode( $raw, true ) : null;
		return is_array( $entry ) && ( $entry['retry_until'] ?? 0 ) > time() ? $entry : null;
	}

	/**
	 * Update only the allocated record; an erased receipt cannot be recreated.
	 *
	 * @param int              $id Native placeholder ID.
	 * @param WP_REST_Response $reply Native response, PDF bytes encoded as JSON.
	 * @param string|null      $release_locale Language of an unsigned Genie result recovered from its thread.
	 */
	public function finish( int $id, WP_REST_Response $reply, ?string $release_locale = null ): int {
		if ( self::TYPE !== get_post_type( $id ) || '' === (string) get_post_meta( $id, '_linker_binding', true ) ) {
			return 0;
		}
		$data    = $reply->get_data();
		$stored  = array(
			'status'           => $reply->get_status(),
			'headers'          => $reply->get_headers(),
			'publication'      => EnginePublication::dependencies( $reply ),
			'publication_kind' => EnginePublication::kind( $reply ),
			...( null !== $release_locale ? array( 'genie_release_locale' => $release_locale ) : array() ),
			'binary'           => is_string( $data ),
			'data'             => is_string( $data ) ? base64_encode( $data ) : $data, // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Binary PDF bytes inside a native JSON receipt.
		);
		$content = wp_json_encode( $stored, JSON_HEX_TAG | JSON_HEX_AMP );
		if ( ! is_string( $content ) ) {
			return 0;
		}
		$updated = wp_update_post(
			array(
				'ID'           => $id,
				'post_content' => wp_slash( $content ),
			),
			true
		);
		return ! is_wp_error( $updated ) && get_post_field( 'post_content', $id, 'raw' ) === $content ? $id : 0;
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
		if ( is_array( $stored['data'] ) && isset( $stored['data']['job_id'], $stored['data']['conversation_id'] ) ) {
			if ( ! ( new \Linker\Tools\Genie\Conversations() )->may_use( (int) $stored['data']['conversation_id'] ) ) {
				return new WP_Error( 'linker_genie_job', 'Unknown turn.', array( 'status' => 404 ) );
			}
			if ( get_post_meta( $id, '_linker_genie_priced', true ) && ! \Linker\Tools\Genie\PublicationGuard::sees_prices() ) {
				return \Linker\Tools\Genie\PublicationGuard::refused();
			}
		}
		$dependencies = is_array( $stored['publication'] ?? null ) ? $stored['publication'] : array();
		$kind         = 'genie' === ( $stored['publication_kind'] ?? null ) ? 'genie' : 'engineering';
		if ( array() !== $dependencies ) {
			$valid = EnginePublication::validate( $dependencies, $kind );
			if ( is_wp_error( $valid ) ) {
				return $valid;
			}
		}
		if ( isset( $stored['genie_release_locale'] ) ) {
			$stream = ( new \Linker\Tools\Genie\PublicationGuard() )->release( $stored['data']['stream'], $dependencies, $stored['genie_release_locale'] );
			if ( is_wp_error( $stream ) ) {
				return $stream;
			}
			$stored['data']['stream'] = $stream;
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Restore the authenticated private PDF response, never executable code.
		$reply = new WP_REST_Response( ! empty( $stored['binary'] ) ? base64_decode( (string) $stored['data'], true ) : $stored['data'], (int) $stored['status'], (array) $stored['headers'] );
		if ( array() !== $dependencies ) {
			EnginePublication::remember( $reply, $dependencies, $kind );
		}
		/**
		 * Consumers can reject their older receipts that predate dependency proof.
		 *
		 * @since 0.1.0
		 */
		return apply_filters( 'linker_tools_restored_reply', $reply, $stored );
	}

	/** Expired receipts hold no reason to retain a copy of a customer's answer. */
	public function expire(): void {
		$ids = get_posts(
			array(
				'post_type'      => self::TYPE,
				'post_status'    => 'any',
				'fields'         => 'ids',
				'posts_per_page' => 1000, // phpcs:ignore WordPress.WP.PostsPerPage.posts_per_page_posts_per_page -- Keep each hourly cleanup bounded.
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

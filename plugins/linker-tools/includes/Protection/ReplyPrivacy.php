<?php
/**
 * Verified-email WordPress privacy lifecycle for private replay receipts.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Inquiry\Assessment\Lock;

/** Guest unlinked answers expire; linked receipts follow verified-email requests. */
final class ReplyPrivacy {
	/** Register the native requester-verification workflow. */
	public function register(): void {
		add_filter( 'wp_privacy_personal_data_exporters', array( $this, 'exporters' ) );
		add_filter( 'wp_privacy_personal_data_erasers', array( $this, 'erasers' ) );
	}

	/**
	 * Native exporter registration.
	 *
	 * @param array<string,mixed> $items Existing exporters.
	 * @return array<string,mixed>
	 */
	public function exporters( array $items ): array {
		$items['linker-tool-replies'] = array(
			'exporter_friendly_name' => sprintf( 'Genie / %s', __( 'Solution Configurator', 'linker-tools' ) ),
			'callback'               => array( $this, 'export' ),
		);
		return $items;
	}

	/**
	 * Native eraser registration.
	 *
	 * @param array<string,mixed> $items Existing erasers.
	 * @return array<string,mixed>
	 */
	public function erasers( array $items ): array {
		$items['linker-tool-replies'] = array(
			'eraser_friendly_name' => sprintf( 'Genie / %s', __( 'Solution Configurator', 'linker-tools' ) ),
			'callback'             => array( $this, 'erase' ),
		);
		return $items;
	}

	/**
	 * Export only records linked to WordPress's verified requester address.
	 *
	 * @param string $email Native verified email.
	 * @param int    $page Native pagination.
	 * @return array<string,mixed>
	 */
	public function export( string $email, int $page = 1 ): array {
		$ids  = $this->ids( $email, $page );
		$data = array();
		foreach ( $ids as $id ) {
			$data[] = array(
				'group_id'    => 'linker-tool-replies',
				'group_label' => sprintf( 'Genie / %s', __( 'Solution Configurator', 'linker-tools' ) ),
				'item_id'     => 'tool-reply-' . $id,
				'data'        => array(
					array(
						'name'  => __( 'Response', 'linker-tools' ),
						'value' => (string) get_post_field( 'post_content', $id ),
					),
				),
			);
		}
		return array(
			'data' => $data,
			'done' => count( $ids ) < 100,
		);
	}

	/**
	 * Remove a bounded page. Never refund dispatched work in the quota journal.
	 *
	 * @param string $email Native verified email.
	 * @param int    $page Native pagination; deletion always consumes the first page.
	 * @return array<string,mixed>
	 * @throws \RuntimeException Failed deletion cannot report successful erasure.
	 * @throws \InvalidArgumentException Invalid native page.
	 */
	public function erase( string $email, int $page = 1 ): array {
		if ( $page < 1 ) {
			throw new \InvalidArgumentException( 'invalid_privacy_page' );
		}
		$ids  = $this->ids( $email );
		$busy = false;
		foreach ( $ids as $id ) {
			$operation = (string) get_post_field( 'post_name', $id );
			if ( ! wp_is_uuid( $operation, 4 ) ) {
				if ( ! wp_delete_post( $id, true ) ) {
					throw new \RuntimeException( 'tool_reply_erasure_unavailable' );
				}
				continue;
			}
			$removed = Lock::run(
				'genie-operation-' . $operation,
				static function () use ( $id ): void {
					// The anonymous operation key prevents duplicate dispatch until the
					// original retry window expires. No customer data remains attached.
					$updated = wp_update_post(
						array(
							'ID'           => $id,
							'post_content' => '',
							'post_author'  => 0,
						),
						true
					);
					if ( is_wp_error( $updated ) ) {
						throw new \RuntimeException( 'tool_reply_erasure_unavailable' );
					}
					foreach ( array( '_linker_input', '_linker_recipient', '_linker_binding', '_linker_previous_conversation' ) as $meta ) {
						delete_post_meta( $id, $meta );
					}
				}
			);
			$busy    = $busy || ! $removed;
		}
		return array(
			'items_removed'  => array() !== $ids,
			'items_retained' => false,
			'messages'       => array(),
			'done'           => ! $busy && count( $ids ) < 100,
		);
	}

	/**
	 * Private HMAC association is separate from the public browser credential.
	 *
	 * @param string $email Verified requester.
	 * @param int    $page Native page.
	 * @return int[]
	 */
	private function ids( string $email, int $page = 1 ): array {
		if ( ! is_email( $email ) ) {
			return array();
		}
		$args    = array(
			'post_type'      => Replies::TYPE,
			'post_status'    => 'private',
			'fields'         => 'ids',
			'posts_per_page' => 100,
			'paged'          => max( 1, $page ),
			'orderby'        => 'ID',
			'order'          => 'ASC',
		);
		$account = get_user_by( 'email', $email );
		if ( false === $account ) {
			$args['meta_key']   = '_linker_recipient'; // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Bounded verified-email privacy workflow.
			$args['meta_value'] = Identity::recipient( $email ); // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Private recipient HMAC.
			return get_posts( $args );
		}
		// WP_Query has no native OR between author and meta. Keep its native
		// pagination/status/type selection and scope one prepared WHERE extension.
		$scope                              = wp_generate_uuid4();
		$args['linker_reply_privacy_scope'] = $scope;
		$args['suppress_filters']           = false;
		$where                              = static function ( string $sql, \WP_Query $query ) use ( $scope, $account, $email ): string {
			if ( $scope !== $query->get( 'linker_reply_privacy_scope' ) ) {
				return $sql;
			}
			global $wpdb;
			return $sql . $wpdb->prepare(
				" AND ({$wpdb->posts}.post_author = %d OR EXISTS (SELECT 1 FROM {$wpdb->postmeta} linker_reply_owner WHERE linker_reply_owner.post_id = {$wpdb->posts}.ID AND linker_reply_owner.meta_key = %s AND linker_reply_owner.meta_value = %s))",
				$account->ID,
				'_linker_recipient',
				Identity::recipient( $email )
			);
		};
		add_filter( 'posts_where', $where, 10, 2 );
		try {
			return get_posts( $args );
		} finally {
			remove_filter( 'posts_where', $where, 10 );
		}
	}
}

<?php
/**
 * Frozen planning references on native inquiries, including trashed orders.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Automattic\WooCommerce\Utilities\OrderUtil;

/** Read Woo's authoritative store directly so database errors cannot look like absence. */
final class ProjectReferences {
	private const LOCK_PREFIX = 'planning-project:';

	/**
	 * Check the transaction connection still owns every lock taken before HTTP.
	 *
	 * @param array<int,string> $projects Admitted projects.
	 * @throws \RuntimeException A required native project lock was lost.
	 */
	public static function require_locks( array $projects ): void {
		global $wpdb;
		foreach ( $projects as $project ) {
			$name = \Linker\Commerce\Inquiry\Assessment\Lock::name( self::LOCK_PREFIX . $project );
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Only this native connection may commit the project reference.
			if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT IS_USED_LOCK(%s) = CONNECTION_ID()', $name ) ) ) {
				throw new \RuntimeException( 'planning_project_lock_lost' );
			}
		}
	}

	/**
	 * Serialize the inquiry commit with the project's native deletion check.
	 *
	 * @param string          $project_id Owned planner project.
	 * @param callable():void $work Native project operation.
	 */
	public static function with_lock( string $project_id, callable $work ): bool {
		return \Linker\Commerce\Inquiry\Assessment\Lock::run( self::LOCK_PREFIX . $project_id, $work, guard_connection: true );
	}

	/**
	 * Read compact references and the full snapshots saved by the original writer.
	 *
	 * @param string $project_id Owned planner project.
	 * @throws \RuntimeException An unreadable order history cannot authorize deletion.
	 */
	public static function contains( string $project_id ): bool {
		global $wpdb;
		$hpos = OrderUtil::custom_orders_table_usage_is_enabled();
		if ( self::contains_preliminary( $project_id, $hpos ) ) {
			return true;
		}
		$cursor = 0;
		do {
			// Keyset pages bound PHP memory when older orders contain full report snapshots.
			// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Woo CRUD's status defaults omit trash and do not distinguish SQL failure from no matching orders.
			$rows = $hpos ? $wpdb->get_results(
				$wpdb->prepare( "SELECT m.id, m.meta_value FROM %i m JOIN %i o ON o.id = m.order_id WHERE o.type = 'shop_order' AND m.meta_key = %s AND m.id > %d ORDER BY m.id LIMIT 32", $wpdb->prefix . 'wc_orders_meta', $wpdb->prefix . 'wc_orders', Context::META, $cursor )
			) : $wpdb->get_results(
				$wpdb->prepare( "SELECT m.meta_id AS id, m.meta_value FROM %i m JOIN %i o ON o.ID = m.post_id WHERE o.post_type = 'shop_order' AND m.meta_key = %s AND m.meta_id > %d ORDER BY m.meta_id LIMIT 32", $wpdb->postmeta, $wpdb->posts, Context::META, $cursor )
			);
			// phpcs:enable
			if ( ! is_array( $rows ) || '' !== $wpdb->last_error ) {
				throw new \RuntimeException( 'planning_inquiry_history_unavailable' );
			}
			foreach ( $rows as $row ) {
				$cursor  = (int) $row->id;
				$entries = json_decode( (string) $row->meta_value, true );
				if ( ! is_array( $entries ) ) {
					throw new \RuntimeException( 'planning_inquiry_history_unreadable' );
				}
				foreach ( $entries as $entry ) {
					$id = $entry['reference']['project_id'] ?? $entry['handoff']['snapshot']['project_id'] ?? null;
					if ( ! is_string( $id ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $id ) ) {
						throw new \RuntimeException( 'planning_inquiry_history_unreadable' );
					}
					if ( $project_id === $id ) {
						return true;
					}
				}
			}
			$more = 32 === count( $rows );
		} while ( $more );
		return false;
	}
	/** Check the Woo reference written without a report.
	 *
	 * @param string $project_id Owned project.
	 * @param bool   $hpos Whether HPOS is authoritative.
	 * @throws \RuntimeException An unreadable order history cannot authorize deletion.
	 */
	private static function contains_preliminary( string $project_id, bool $hpos ): bool {
		global $wpdb;
		// Both native stores include trashed orders. Match the project and revision separator.
		$prefix = $wpdb->esc_like( $project_id . ':' ) . '%';
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Woo does not support meta_query in its CPT order query; an SQL failure must refuse deletion.
		$linked = $hpos ? $wpdb->get_var(
			$wpdb->prepare( "SELECT 1 FROM %i m JOIN %i o ON o.id = m.order_id WHERE o.type = 'shop_order' AND m.meta_key = %s AND m.meta_value LIKE %s LIMIT 1", $wpdb->prefix . 'wc_orders_meta', $wpdb->prefix . 'wc_orders', Context::PROJECT_META, $prefix )
		) : $wpdb->get_var(
			$wpdb->prepare( "SELECT 1 FROM %i m JOIN %i o ON o.ID = m.post_id WHERE o.post_type = 'shop_order' AND m.meta_key = %s AND m.meta_value LIKE %s LIMIT 1", $wpdb->postmeta, $wpdb->posts, Context::PROJECT_META, $prefix )
		);
		// phpcs:enable
		if ( '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'planning_inquiry_history_unavailable' );
		}
		return null !== $linked;
	}
}

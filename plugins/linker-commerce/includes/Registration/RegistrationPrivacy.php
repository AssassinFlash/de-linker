<?php
/**
 * Native verified-email privacy for the bounded pending registration handoff.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\RegistrationSlots;
use WP_Error;

/**
 * Native WordPress owns requester verification, user identity and deletion.
 */
final class RegistrationPrivacy {

	/**
	 * Add only the original framework privacy surfaces.
	 */
	public function register(): void {
		add_filter( 'wp_privacy_personal_data_exporters', array( $this, 'exporters' ) );
		add_filter( 'wp_privacy_personal_data_erasers', array( $this, 'erasers' ) );
		add_action( 'delete_user', array( $this, 'deleted' ) );
	}

	/**
	 * Register the native exporter.
	 *
	 * @param  array<string,mixed> $items Native exporters.
	 * @return array<string,mixed> Native exporter registration.
	 */
	public function exporters( array $items ): array {
		$items['linker-registration-notices'] = array(
			'exporter_friendly_name' => __( 'Registration notifications', 'linker-commerce' ),
			'callback'               => array( $this, 'export' ),
		);
		return $items;
	}

	/**
	 * Register the native eraser.
	 *
	 * @param  array<string,mixed> $items Native erasers.
	 * @return array<string,mixed> Native eraser registration.
	 */
	public function erasers( array $items ): array {
		$items['linker-registration-notices'] = array(
			'eraser_friendly_name' => __( 'Registration notifications', 'linker-commerce' ),
			'callback'             => array( $this, 'erase' ),
		);
		return $items;
	}

	/**
	 * Export this verified recipient's native registration records.
	 *
	 * @param  string $email Framework-verified requester.
	 * @param  int    $page  Framework page.
	 * @return array<string,mixed>|WP_Error Native privacy export or retryable read failure.
	 */
	public function export( string $email, int $page = 1 ): array|WP_Error {
		$data  = array();
		$users = self::users( $email, $page );
		if ( is_wp_error( $users ) ) {
			return $users;
		}
		foreach ( $users as $id ) {
			$state = RegistrationNotices::read( $id );
			if ( null === $state ) {
				continue;
			}
			$data[] = array(
				'group_id'    => 'linker-registration-notices',
				'group_label' => __( 'Registration notifications', 'linker-commerce' ),
				'item_id'     => 'registration-user-' . $id,
				'data'        => array(
					array(
						'name'  => __( 'Registration notifications', 'linker-commerce' ),
						'value' => (string) wp_json_encode( $state ),
					),
				),
			);
		}
		if ( 1 === $page ) {
			$owned = RegistrationSlots::owned_data( Identity::recipient( $email ) );
			if ( is_wp_error( $owned ) ) {
				return self::read_problem();
			}
			if ( array() !== array_filter( $owned ) ) {
				$data[] = array(
					'group_id'    => 'linker-registration-notices',
					'group_label' => __( 'Registration notifications', 'linker-commerce' ),
					'item_id'     => 'registration-interrupted',
					'data'        => array(
						array(
							'name'  => __( 'Interrupted registrations', 'linker-commerce' ),
							'value' => (string) wp_json_encode( $owned ),
						),
					),
				);
			}
		}
		return array(
			'data' => $data,
			'done' => count( $users ) < 128,
		);
	}

	/**
	 * Erasure removes the pending copy and its owned native jobs, never quotas.
	 *
	 * @param  string $email Framework-verified requester.
	 * @param  int    $page  Framework page.
	 * @return array<string,mixed> Explicit native privacy state.
	 */
	public function erase( string $email, int $page = 1 ): array {
		unset( $page ); // Removing owner markers shifts pages; always resume from the first remaining owner.
		// Erased owner markers disappear, so each retry starts at the first remaining page.
		$users = self::users( $email, 1 );
		if ( is_wp_error( $users ) ) {
			return array(
				'items_removed'  => false,
				'items_retained' => true,
				'messages'       => array( $users->get_error_message() ),
				'done'           => false,
			);
		}
		$done = true;
		foreach ( $users as $id ) {
			$done = RegistrationNotices::erase( $id ) && $done;
		}
		$done = RegistrationSlots::forget_owner( Identity::recipient( $email ) ) && $done;
		$done = count( $users ) < 128 && $done;
		return array(
			'items_removed'  => $done,
			'items_retained' => ! $done,
			'messages'       => $done ? array() : array( __( 'Registration notification data is busy. Please retry the erasure.', 'linker-commerce' ) ),
			'done'           => $done,
		);
	}

	/**
	 * Original recipient and current native address are independently owned privacy records.
	 *
	 * @param  string $email Framework-verified address.
	 * @param  int    $page  Framework page.
	 * @return list<int>|WP_Error Bounded native IDs or explicit unknown, never cached failed emptiness.
	 */
	private static function users( string $email, int $page ): array|WP_Error {
		$ids = array_map(
			'intval',
			get_users(
				array(
					'cache_results' => false,
					'fields'        => 'ID',
					'number'        => 128,
					'offset'        => max( 0, $page - 1 ) * 128,
					'orderby'       => 'ID',
					'order'         => 'ASC',
					'meta_key'      => RegistrationNotices::OWNER, // phpcs:ignore WordPress.DB.SlowDBQuery -- Framework-verified recipient, bounded native privacy page.
				'meta_value'        => Identity::recipient( $email ), // phpcs:ignore WordPress.DB.SlowDBQuery -- HMAC ownership is the only original-recipient selector.
				)
			)
		);
		if ( self::database_error() ) {
			return self::read_problem();
		}
		$current = get_user_by( 'email', $email );
		if ( self::database_error() ) {
			return self::read_problem();
		}
		if ( 1 === $page && $current instanceof \WP_User && ! in_array( $current->ID, $ids, true ) && null !== RegistrationNotices::read( $current->ID ) ) {
			$ids[] = $current->ID;
		}
		return array_values( $ids );
	}

	/**
	 * Native owner/current-user queries can independently change the driver error.
	 *
	 * @phpstan-impure
	 */
	private static function database_error(): bool {
		global $wpdb;
		return '' !== $wpdb->last_error;
	}

	/** A failed owner lookup never means this verified recipient has no records. */
	private static function read_problem(): WP_Error {
		return new WP_Error( 'linker_registration_privacy_unavailable', __( 'Registration notification data could not be read. Please try again.', 'linker-commerce' ) );
	}

	/**
	 * Deletion must not strand the user's original prepared notification elsewhere.
	 *
	 * @param  int $id Native account being deleted.
	 * @throws \RuntimeException A competing handoff must finish before deletion.
	 */
	public function deleted( int $id ): void {
		if ( ! RegistrationNotices::erase( $id ) ) {
			throw new \RuntimeException( 'registration_privacy_busy' );
		}
	}
}

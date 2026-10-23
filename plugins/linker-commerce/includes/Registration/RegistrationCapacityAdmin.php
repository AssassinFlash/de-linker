<?php
/**
 * Native staff visibility and explicit interrupted-registration dispositions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Protection\RegistrationSlots;

/**
 * WordPress capabilities/nonces own every write; no customer-facing admin route.
 */
final class RegistrationCapacityAdmin {

	private const PAGE = 'linker-registration-capacity';

	/**
	 * Native users screen and profile extension, without another app or CSS.
	 */
	public function register(): void {
		add_action( 'admin_menu', array( $this, 'menu' ) );
		add_action( 'admin_post_linker_registration_capacity', array( $this, 'act' ) );
		add_action( 'show_user_profile', array( $this, 'profile' ) );
		add_action( 'edit_user_profile', array( $this, 'profile' ) );
	}

	/**
	 * Existing staff permission is required, including native additional auth.
	 */
	public function menu(): void {
		add_users_page( __( 'Registration capacity', 'linker-commerce' ), __( 'Registration capacity', 'linker-commerce' ), 'edit_users', self::PAGE, array( $this, 'page' ) );
	}

	/**
	 * Durable current state, historical notices and bounded explicit dispositions.
	 */
	public function page(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			return;
		}
		echo '<div class="wrap"><h1>' . esc_html__( 'Registration capacity', 'linker-commerce' ) . '</h1>';
		$summary = RegistrationSlots::summary();
		if ( is_wp_error( $summary ) ) {
			echo '<p>' . esc_html( $summary->get_error_message() ) . '</p>';
		} else {
				echo '<table class="widefat striped"><tbody>';
			foreach ( array(
				'pending_users'  => __( 'Pending accounts', 'linker-commerce' ),
				'interrupted'    => __( 'Interrupted registrations', 'linker-commerce' ),
				'capacity'       => __( 'Account capacity', 'linker-commerce' ),
				'business_bytes' => __( 'Business profile bytes', 'linker-commerce' ),
				'reserved_bytes' => __( 'Reserved profile bytes', 'linker-commerce' ),
				'byte_capacity'  => __( 'Profile byte capacity', 'linker-commerce' ),
			) as $key => $label ) {
				echo '<tr><th>' . esc_html( $label ) . '</th><td>' . esc_html( (string) $summary[ $key ] ) . '</td></tr>';
			}
			echo '</tbody></table>';
		}
		$this->form( 'recover', '', __( 'Recover notifications', 'linker-commerce' ), false );
		echo '<h2>' . esc_html__( 'Registration notifications', 'linker-commerce' ) . '</h2>';
		foreach ( get_users(
			array(
				'meta_key' => RegistrationNotices::META, // phpcs:ignore WordPress.DB.SlowDBQuery -- Native staff-only bounded history.
			'number'       => 128,
			'orderby'      => 'ID',
			'order'        => 'DESC',
			)
		) as $user ) {
			if ( $user instanceof \WP_User ) {
				$this->profile( $user, true );
			}
		}
		echo '<h2>' . esc_html__( 'Interrupted registrations', 'linker-commerce' ) . '</h2>';
		$entries = RegistrationSlots::interrupted();
		if ( ! is_wp_error( $entries ) ) {
			foreach ( $entries as $key => $entry ) {
				echo '<p><code>' . esc_html( substr( $key, 0, 16 ) ) . '</code> · ' . esc_html( (string) ( $entry['bytes'] ?? 0 ) ) . ' bytes</p>';
				$this->form( 'resolve', $key, __( 'Mark as resolved', 'linker-commerce' ), true );
			}
		}
		echo '<h2>' . esc_html__( 'Recent staff decisions', 'linker-commerce' ) . '</h2><dl>';
		foreach ( get_option( 'linker_registration_dispositions', array() ) as $record ) {
			echo '<dt>' . esc_html( substr( $record['key'], 0, 16 ) ) . ' · ' . esc_html( (string) wp_date( 'Y-m-d H:i', $record['at'] ) ) . ' · ' . esc_html( (string) $record['by'] ) . '</dt><dd>' . esc_html( $record['reason'] ?? '' ) . '</dd>';
		}
		echo '</dl></div>';
	}

	/**
	 * This is queue acceptance status, never a delivered-mail claim.
	 *
	 * @param \WP_User $user    Native user.
	 * @param bool     $actions Action forms are only valid outside the native profile form.
	 */
	public function profile( \WP_User $user, bool $actions = false ): void {
		if ( ! current_user_can( 'edit_user', $user->ID ) ) {
			return;
		}
		$state = RegistrationNotices::read( $user->ID );
		if ( null === $state ) {
			return;
		}
		echo '<h3><a href="' . esc_url( get_edit_user_link( $user->ID ) ) . '">' . esc_html( $user->user_email ) . '</a></h3><dl>';
		foreach ( $state as $kind => $notice ) {
			$label = match ( $notice['state'] ?? '' ) {
				'accepted' => __( 'Accepted by the notification queue', 'linker-commerce' ),
				'skipped' => __( 'Notification skipped by policy', 'linker-commerce' ),
				'erased' => __( 'Notification data erased', 'linker-commerce' ),
				default => __( 'Account created; notification pending', 'linker-commerce' ),
			};
			echo '<dt>' . esc_html( 'team' === $kind ? __( 'Team notification', 'linker-commerce' ) : __( 'Registration receipt', 'linker-commerce' ) ) . '</dt><dd>' . esc_html( $label ) . ( isset( $notice['reason'] ) ? ' · ' . esc_html( $notice['reason'] ) : '' ) . '</dd>';
		}
		echo '</dl>';
		if ( $actions && 'core' === get_user_meta( $user->ID, '_linker_public_registration_entry', true ) ) {
			$this->form( 'approved', (string) $user->ID, __( 'Approve account', 'linker-commerce' ), false );
			$this->form( 'rejected', (string) $user->ID, __( 'Reject account', 'linker-commerce' ), true );
		}
	}

	/**
	 * Native POST handler; a busy/unknown result remains visible and unresolved.
	 */
	public function act(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			wp_die( esc_html__( 'You are not allowed to review accounts.', 'linker-commerce' ) );
		}
		check_admin_referer( 'linker_registration_capacity' );
		$decision = isset( $_POST['decision'] ) && is_string( $_POST['decision'] ) ? sanitize_key( wp_unslash( $_POST['decision'] ) ) : '';
		$key      = isset( $_POST['key'] ) && is_string( $_POST['key'] ) ? sanitize_text_field( wp_unslash( $_POST['key'] ) ) : '';
		$reason   = isset( $_POST['reason'] ) && is_string( $_POST['reason'] ) ? sanitize_textarea_field( wp_unslash( $_POST['reason'] ) ) : '';
		$done     = false;
		if ( 'recover' === $decision ) {
			RegistrationNotices::recover();
			$done = true;
		} elseif ( 'resolve' === $decision ) {
			$done = RegistrationSlots::resolve_interrupted( $key, $reason );
		} elseif ( in_array( $decision, array( Approval::APPROVED, Approval::REJECTED ), true ) && current_user_can( 'edit_user', (int) $key ) && 'core' === get_user_meta( (int) $key, '_linker_public_registration_entry', true ) ) {
			$done = ( new Approval() )->set( (int) $key, $decision, $reason );
			wp_cache_delete( (int) $key, 'user_meta' );
			$done = $done && get_user_meta( (int) $key, Approval::STATUS_META, true ) === $decision && get_current_user_id() === (int) get_user_meta( (int) $key, Approval::CHANGED_BY_META, true ) && 0 < (int) get_user_meta( (int) $key, Approval::CHANGED_AT_META, true );
		}
		if ( ! $done ) {
			wp_die( esc_html__( 'The registration state could not be confirmed. Please check the account and capacity before trying again.', 'linker-commerce' ) );
		}
		wp_safe_redirect( admin_url( 'users.php?page=' . self::PAGE ) );
		exit;
	}

	/**
	 * Native nonce form, with a required explicit evidence field for dispositions.
	 *
	 * @param string $decision Trusted action.
	 * @param string $key      Native ID or placeholder.
	 * @param string $label    Localized action.
	 * @param bool   $reason   Whether staff must give a reason.
	 */
	private function form( string $decision, string $key, string $label, bool $reason ): void {
		echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="linker_registration_capacity"><input type="hidden" name="decision" value="' . esc_attr( $decision ) . '"><input type="hidden" name="key" value="' . esc_attr( $key ) . '">';
		wp_nonce_field( 'linker_registration_capacity' );
		if ( $reason ) {
			echo '<p><label>' . esc_html__( 'Reason for this decision', 'linker-commerce' ) . '<textarea required maxlength="2048" name="reason"></textarea></label></p>';
		}
		submit_button( $label, 'secondary', 'submit', false );
		echo '</form>';
	}
}

<?php
/**
 * Status and review links on WordPress's own user screens.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_User;

/** The account-review card owns all decisions; these native screens link to it. */
final class ApprovalAdmin {

	/**
	 * Reads the same approval authority as the cards.
	 *
	 * @param Approval $approval Approval authority.
	 */
	public function __construct( private readonly Approval $approval ) {}

	/** Keeps status visibility and removes the former GET/profile write channels. */
	public function register(): void {
		add_filter( 'manage_users_columns', array( $this, 'column_header' ) );
		add_filter( 'manage_users_custom_column', array( $this, 'column_cell' ), 10, 3 );
		add_filter( 'user_row_actions', array( $this, 'row_action' ), 10, 2 );
		add_action( 'edit_user_profile', array( $this, 'profile_block' ) );
	}

	/**
	 * The approval column, first after the username.
	 *
	 * @param array<string, string> $columns Users list columns.
	 * @return array<string, string>
	 */
	public function column_header( array $columns ): array {
		$position = array_search( 'username', array_keys( $columns ), true );
		$column   = array( Approval::STATUS_META => __( 'Approval', 'linker-commerce' ) );
		if ( false === $position ) {
			return $columns + $column;
		}
		return array_slice( $columns, 0, (int) $position + 1, true )
			+ $column
			+ array_slice( $columns, (int) $position + 1, null, true );
	}

	/**
	 * The account's state and, where one was given, the reason; runs on
	 * manage_users_custom_column.
	 *
	 * @param string $output  Cell HTML so far.
	 * @param string $column  Column name.
	 * @param int    $user_id User.
	 */
	public function column_cell( string $output, string $column, int $user_id ): string {
		if ( Approval::STATUS_META !== $column ) {
			return $output;
		}
		if ( ! $this->approval->is_subject( $user_id ) ) {
			return $output;
		}
		$reason = $this->approval->reason( $user_id );
		return Approval::label( $this->approval->status( $user_id ) )
			. ( '' !== $reason ? '<br /><span class="description">' . esc_html( $reason ) . '</span>' : '' );
	}

	/**
	 * Every customer state can be reviewed again, including an approved account.
	 *
	 * @param array<string, string> $actions Native row actions.
	 * @param WP_User               $user    Customer.
	 * @return array<string, string>
	 */
	public function row_action( array $actions, WP_User $user ): array {
		if ( $this->can_review( $user->ID ) ) {
			$actions[ Approval::STATUS_META ] = $this->link( $user->ID );
		}
		return $actions;
	}

	/**
	 * WordPress still edits the profile; its status block opens the review card.
	 *
	 * @param WP_User $user Customer.
	 */
	public function profile_block( WP_User $user ): void {
		if ( ! $this->can_review( $user->ID ) ) {
			return;
		}
		echo '<h2>' . esc_html__( 'Linker approval', 'linker-commerce' ) . '</h2><p><strong>' . esc_html( Approval::label( $this->approval->status( $user->ID ) ) ) . '</strong></p>';
		if ( '' !== $this->approval->reason( $user->ID ) ) {
			echo '<p>' . esc_html( $this->approval->reason( $user->ID ) ) . '</p>';
		}
		echo '<p>' . wp_kses_post( $this->link( $user->ID ) ) . '</p>';
	}

	/**
	 * Uses WordPress's global and per-user capabilities, plus Approval's identity rule.
	 *
	 * @param int $user_id Customer.
	 */
	private function can_review( int $user_id ): bool {
		return current_user_can( 'edit_users' ) && current_user_can( 'edit_user', $user_id ) && $this->approval->is_subject( $user_id );
	}

	/**
	 * A read-only deep link to the single decision interface.
	 *
	 * @param int $user_id Customer.
	 */
	private function link( int $user_id ): string {
		return '<a href="' . esc_url( AccountsAdmin::url( $user_id ) ) . '">' . esc_html__( 'Review or change decision', 'linker-commerce' ) . '</a>';
	}
}

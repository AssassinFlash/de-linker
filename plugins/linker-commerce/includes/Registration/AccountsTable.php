<?php
/**
 * Native WordPress list table of reviewed and pending customer accounts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_List_Table;
use WP_User;

/** The historical list opens the same review card as the dashboard and drawer. */
final class AccountsTable extends WP_List_Table {

	/**
	 * Shared data and the validated GET filters (read-only).
	 *
	 * @param Accounts $accounts Customer set.
	 * @param Approval $approval Approval authority.
	 * @param string   $status   State filter, or all.
	 * @param string   $search   Search term.
	 */
	public function __construct( private readonly Accounts $accounts, private readonly Approval $approval, private readonly string $status, private readonly string $search ) {
		parent::__construct(
			array(
				'singular' => 'account',
				'plural'   => 'accounts',
				'ajax'     => false,
			)
		);
	}

	/**
	 * Native table columns.
	 *
	 * @return array<string, string>
	 */
	public function get_columns(): array {
		return array(
			'company'    => __( 'Company', 'linker-commerce' ),
			'contact'    => __( 'Contact', 'linker-commerce' ),
			'status'     => __( 'Approval', 'linker-commerce' ),
			'reason'     => __( 'Reason', 'linker-commerce' ),
			'registered' => __( 'Registered', 'linker-commerce' ),
		);
	}

	/** Filters by the same state authority and paginates with WP's per-page setting. */
	public function prepare_items(): void {
		$users = array();
		foreach ( $this->accounts->customers() as $user ) {
			if ( 'all' !== $this->status && $this->approval->status( $user->ID ) !== $this->status ) {
				continue;
			}
			$text = (string) get_user_meta( $user->ID, 'billing_company', true ) . ' ' . $user->display_name . ' ' . $user->user_email;
			if ( '' === $this->search || false !== stripos( $text, $this->search ) ) {
				$users[] = $user;
			}
		}
		$per_page              = $this->get_items_per_page( 'linker_accounts_per_page' );
		$this->_column_headers = array( $this->get_columns(), array(), array(), 'company' );
		$this->items           = array_slice( $users, ( $this->get_pagenum() - 1 ) * $per_page, $per_page );
		$this->set_pagination_args(
			array(
				'total_items' => count( $users ),
				'per_page'    => $per_page,
			)
		);
	}

	/** No matches is a normal state, including an empty pending filter. */
	public function no_items(): void {
		esc_html_e( 'No accounts match these filters.', 'linker-commerce' );
	}

	/**
	 * Native responsive row with a stable id for the live status update.
	 *
	 * @param WP_User $item Customer.
	 */
	public function single_row( $item ): void {
		echo '<tr id="linker-account-row-' . esc_attr( (string) $item->ID ) . '">';
		$this->single_row_columns( $item );
		echo '</tr>';
	}

	/**
	 * Values in the native table; links are reads, never state-changing GETs.
	 *
	 * @param WP_User $item        Customer.
	 * @param string  $column_name Column.
	 * @return string
	 */
	public function column_default( $item, $column_name ) {
		switch ( $column_name ) {
			case 'company':
				$company = (string) get_user_meta( $item->ID, 'billing_company', true );
				return '<strong><a data-linker-account="' . esc_attr( (string) $item->ID ) . '" href="' . esc_url( AccountsAdmin::url( $item->ID ) ) . '">' . esc_html( '' !== $company ? $company : $item->display_name ) . '</a></strong>';
			case 'contact':
				return esc_html( $item->display_name ) . '<br>' . esc_html( $item->user_email );
			case 'status':
				return '<span class="linker-account-status-label">' . esc_html( Approval::label( $this->approval->status( $item->ID ) ) ) . '</span>';
			case 'reason':
				return '<span class="linker-account-reason-value">' . esc_html( $this->approval->reason( $item->ID ) ) . '</span>';
			case 'registered':
				return esc_html( get_date_from_gmt( $item->user_registered, 'Y-m-d H:i' ) );
		}
		return '';
	}

	/**
	 * Native row_actions() supplies the responsive toggle itself. Returning it
	 * here replaces WP_List_Table's default toggle instead of appending a second.
	 *
	 * @param WP_User $item        Customer.
	 * @param string  $column_name Current column.
	 * @param string  $primary     Primary column.
	 * @return string
	 */
	protected function handle_row_actions( $item, $column_name, $primary ) {
		return $column_name === $primary ? $this->row_actions( array( 'review' => '<a data-linker-account="' . esc_attr( (string) $item->ID ) . '" href="' . esc_url( AccountsAdmin::url( $item->ID ) ) . '">' . esc_html__( 'Review or change decision', 'linker-commerce' ) . '</a>' ) ) : '';
	}

	/**
	 * Status filters with counts updated after a decision.
	 *
	 * @return array<string, string>
	 */
	protected function get_views(): array {
		$counts = $this->accounts->counts();
		$labels = array( 'all' => __( 'All accounts', 'linker-commerce' ) );
		foreach ( Approval::states() as $state ) {
			$labels[ $state ] = Approval::label( $state );
		}
		$views = array();
		foreach ( $labels as $state => $label ) {
			$count           = 'all' === $state ? array_sum( $counts ) : $counts[ $state ];
			$views[ $state ] = '<a href="' . esc_url(
				add_query_arg(
					array(
						'status' => $state,
						's'      => $this->search,
					),
					AccountsAdmin::url()
				)
			) . '"' . ( $state === $this->status ? ' class="current" aria-current="page"' : '' ) . '>' . esc_html( $label ) . ' <span class="count">(<span data-linker-account-count="' . esc_attr( $state ) . '">' . esc_html( (string) $count ) . '</span>)</span></a>';
		}
		return $views;
	}
}

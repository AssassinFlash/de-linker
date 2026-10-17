<?php
/**
 * The customer set and its staff-facing review data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Customer;
use WP_User;
use WP_User_Query;

/** Approval defines the customer set and state; registration defines the data. */
final class Accounts {

	/**
	 * Request-local aggregation, shared by every native mount and reader instance.
	 *
	 * @var array<string, int>|null
	 */
	private static ?array $request_counts = null;

	/**
	 * WordPress invalidates its users epoch on user/meta/role changes.
	 *
	 * @var string
	 */
	private static string $counts_version = '';

	/**
	 * Shared readers.
	 *
	 * @param Approval                $approval    Approval authority.
	 * @param RegistrationInformation $information Saved registration values.
	 * @param AccountSignals          $signals     Explainable clues and domain leads.
	 */
	public function __construct( private readonly Approval $approval, private readonly RegistrationInformation $information, private readonly AccountSignals $signals = new AccountSignals() ) {}

	/**
	 * Reviewable customers, oldest first, with the same identity rule as Approval.
	 *
	 * @return list<WP_User>
	 */
	public function customers(): array {
		$customers = array();
		foreach ( get_users(
			array(
				'role'    => 'customer',
				'orderby' => 'registered',
				'order'   => 'ASC',
			)
		) as $user ) {
			if ( $user instanceof WP_User && $this->approval->is_subject( $user->ID ) && current_user_can( 'edit_user', $user->ID ) ) {
				$customers[] = $user;
			}
		}
		return $customers;
	}

	/**
	 * Counts for the queue, menu and historical filters.
	 *
	 * @return array<string, int>
	 */
	public function counts(): array {
		global $wpdb;
		$version = get_current_blog_id() . ':' . wp_cache_get_last_changed( 'users' );
		if ( null !== self::$request_counts && self::$counts_version === $version ) {
			return self::$request_counts;
		}
		// WP_User_Query prepares the site's native customer-role SQL without
		// executing a user-list query. Excluding every other registered role
		// matches Approval::is_subject(), including customers with extra caps.
		$query = new WP_User_Query();
		$query->prepare_query(
			array(
				'role'         => 'customer',
				'role__not_in' => array_values( array_diff( array_keys( wp_roles()->roles ), array( 'customer' ) ) ),
				'count_total'  => false,
				'fields'       => 'ID',
			)
		);
		$state = $wpdb->prepare( // phpcs:ignore WordPress.DB.PreparedSQLPlaceholders.ReplacementsWrongNumber -- Four Approval states plus the pending default fill all placeholders.
			'CASE WHEN linker_state.meta_value IN (%s, %s, %s, %s) THEN linker_state.meta_value ELSE %s END',
			...array_merge( Approval::states(), array( Approval::PENDING ) )
		);
		// One grouped count, no WP_User/WC_Customer hydration. WordPress's users
		// last_changed epoch also invalidates this request cache after a decision
		// or role change (wp-includes/default-filters.php's user-meta/role hooks).
		// phpcs:disable WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching, WordPress.DB.PreparedSQL.InterpolatedNotPrepared, WordPress.DB.PreparedSQL.NotPrepared -- Prepared WP_User_Query fragments and prepared state/key values; cached only in this PHP request.
		$rows = $wpdb->get_results(
			$wpdb->prepare(
				"SELECT {$state} AS account_state, COUNT(DISTINCT {$wpdb->users}.ID) AS total {$query->query_from}
				LEFT JOIN {$wpdb->usermeta} AS linker_state ON linker_state.user_id = {$wpdb->users}.ID AND linker_state.meta_key = %s
				{$query->query_where} GROUP BY account_state",
				Approval::STATUS_META
			),
			ARRAY_A
		);
		// phpcs:enable
		$counts = array_fill_keys( Approval::states(), 0 );
		foreach ( $rows as $row ) {
			$counts[ $row['account_state'] ] = (int) $row['total'];
		}
		self::$request_counts = $counts;
		self::$counts_version = $version;
		return $counts;
	}

	/**
	 * The pending queue, or the focused account even after a decision.
	 *
	 * @param int    $focus  Customer to focus on, or zero for a state queue.
	 * @param string $status State queue; the red flag always uses pending.
	 * @return list<array<string, mixed>>
	 */
	public function items( int $focus = 0, string $status = Approval::PENDING ): array {
		$items = array();
		foreach ( $this->customers() as $user ) {
			if ( $focus > 0 ? $user->ID === $focus : $status === $this->approval->status( $user->ID ) ) {
				$items[] = $this->item( $user );
			}
		}
		return $items;
	}

	/**
	 * One card's data. Only defined registration fields and public identity leave PHP.
	 *
	 * @param WP_User $user Customer.
	 * @return array<string, mixed>
	 */
	public function item( WP_User $user ): array {
		$customer     = new WC_Customer( $user->ID );
		$company      = $customer->get_billing_company();
		$country      = $customer->get_billing_country();
		$country_name = WC()->countries->get_countries()[ $country ] ?? $country;
		$rows         = $this->information->rows( $user );
		$links        = array(
			array(
				'label' => 'Google',
				'url'   => 'https://www.google.com/search?q=' . rawurlencode( $company . ' ' . $country_name ),
			),
			array(
				'label' => 'North Data',
				'url'   => 'https://www.northdata.com/' . rawurlencode( $company ),
			),
		);
		$website      = '';
		foreach ( $rows as $row ) {
			if ( $row['website'] && '' !== esc_url_raw( $row['value'] ) ) {
				$website = esc_url_raw( $row['value'] );
				break;
			}
		}
		$domain_website = $this->signals->website_from_email( $user->user_email );
		if ( '' !== $website || '' !== $domain_website ) {
			$links[] = array(
				'label' => '' !== $website ? __( 'Company website', 'linker-commerce' ) : __( 'Website (from email domain)', 'linker-commerce' ),
				'url'   => '' !== $website ? $website : $domain_website,
			);
		}
		$vat = VatNumber::parse( (string) get_user_meta( $user->ID, VatProfile::VAT_META, true ) );
		if ( null !== $vat && $vat->is_checkable() ) {
			// VIES 7.3.0-HF1's form ignores URL parameters. Its own checkVatNumber
			// uses this public, number-addressed GET route (official app source,
			// read via Apify and browser-verified with a synthetic VAT, 2026-10-18).
			// Opening it checks that VAT directly; it never rewrites our saved verdict.
			$links[] = array(
				'label' => 'VIES',
				'url'   => 'https://ec.europa.eu/taxation_customs/vies/rest-api/ms/' . rawurlencode( $vat->country ) . '/vat/' . rawurlencode( $vat->number ),
			);
		}
		$switch  = class_exists( 'user_switching' ) ? \user_switching::maybe_switch_url( $user ) : false;
		$contact = trim( $customer->get_billing_first_name() . ' ' . $customer->get_billing_last_name() );
		$audit   = $this->approval->changed_by( $user->ID );
		$editor  = $audit['by'] > 0 ? get_userdata( $audit['by'] ) : false;
		return array(
			'id'           => $user->ID,
			'company'      => '' !== $company ? $company : $user->display_name,
			'country'      => $country_name,
			'businessType' => CustomerRole::label( (string) $customer->get_meta( CustomerRole::META ) ),
			'contact'      => '' !== $contact ? $contact : $user->display_name,
			'email'        => $user->user_email,
			'registered'   => get_date_from_gmt( $user->user_registered, 'Y-m-d H:i' ),
			'status'       => $this->approval->status( $user->ID ),
			'statusLabel'  => Approval::label( $this->approval->status( $user->ID ) ),
			'reason'       => $this->approval->reason( $user->ID ),
			'audit'        => 0 !== $audit['at'] ? wp_date( 'Y-m-d H:i', $audit['at'] ) . ( $editor instanceof WP_User ? ' · ' . $editor->display_name : '' ) : '',
			'fields'       => $rows,
			'signals'      => $this->signals->for_account( $user->ID, $company, $user->user_email ),
			'links'        => $links,
			'switchUrl'    => false !== $switch ? add_query_arg( 'redirect_to', home_url( '/' ), html_entity_decode( $switch, ENT_QUOTES, 'UTF-8' ) ) : '',
			'switchNote'   => class_exists( 'user_switching' ) ? __( 'You do not have permission to switch to this customer.', 'linker-commerce' ) : __( 'User Switching is not active.', 'linker-commerce' ),
		);
	}
}

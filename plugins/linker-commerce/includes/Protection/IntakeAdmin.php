<?php
/**
 * Native staff review capacity and honest session-bound customer receipt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WC_Order;

/** No new customer layout or CSS; existing Woo/LC surfaces own presentation. */
final class IntakeAdmin {
	/** Register native staff views and a version-bound revocation control. */
	public function register(): void {
		add_filter( 'seopress_titles_title', array( $this, 'title' ), 50 );
		// GermanTitles builds its independent title at priority 40. Apply the
		// saved-review state afterward on both SEO and core title paths.
		add_filter( 'pre_get_document_title', array( $this, 'title' ), 50 );
		add_filter( 'document_title_parts', array( $this, 'title_parts' ), 20 );
		add_action( 'admin_notices', array( $this, 'notice' ) );
		add_action( 'pre_get_posts', array( $this, 'classic_query' ) );
		add_filter( 'woocommerce_order_list_table_prepare_items_query_args', array( $this, 'query' ) );
		add_action( 'add_meta_boxes', array( $this, 'boxes' ) );
		add_action( 'admin_post_linker_campaign_rule', array( $this, 'rule' ) );
		add_filter( 'woocommerce_privacy_export_order_personal_data', array( $this, 'export' ), 10, 2 );
	}

	/**
	 * The browser title reflects the same authorized native saved-for-review state.
	 *
	 * @param string $title Native SEO title.
	 */
	public function title( string $title ): string {
		if ( ! is_wc_endpoint_url( 'order-received' ) ) {
			return $title;
		}
		$id    = absint( get_query_var( 'order-received' ) );
		$order = $id > 0 ? wc_get_order( $id ) : false;
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only native order key authorization.
		$key = isset( $_GET['key'] ) && is_string( $_GET['key'] ) ? sanitize_text_field( wp_unslash( $_GET['key'] ) ) : '';
		if ( $order instanceof WC_Order && hash_equals( $order->get_order_key(), $key ) && \Linker\Commerce\Mail\NotificationHold::held( $order ) ) {
			return str_replace( __( 'Inquiry received', 'linker-commerce' ), __( 'Inquiry saved for review', 'linker-commerce' ), $title );
		}
		return $title;
	}

	/**
	 * Core title counterpart when an SEO plugin does not own the title.
	 *
	 * @param array<string,string> $parts Native document title parts.
	 * @return array<string,string>
	 */
	public function title_parts( array $parts ): array {
		if ( isset( $parts['title'] ) ) {
			$parts['title'] = $this->title( $parts['title'] );
		}
		return $parts;
	}

	/** Aggregate staff visibility does not create one email per held request. */
	public function notice(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		$summary = Intake::pending_summary();
		if ( ! is_wp_error( $summary ) && $summary['count'] > 0 ) {
			/* translators: %d is the number of complete inquiries awaiting staff review. */
			echo '<div class="notice notice-warning"><p>' . esc_html( sprintf( __( '%d public requests are waiting for staff review. No individual notification has been sent for these requests.', 'linker-commerce' ), $summary['count'] ) ) . ' <a href="' . esc_url( $summary['url'] ) . '">' . esc_html__( 'View saved requests', 'linker-commerce' ) . '</a></p></div>';
		}
	}

	/**
	 * The native Woo list shows actual held records, without a second inbox.
	 *
	 * @param array<string,mixed> $args Native order list query.
	 * @return array<string,mixed>
	 */
	public function query( array $args ): array {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Staff read-only native listing filter.
		if ( current_user_can( 'manage_woocommerce' ) && isset( $_GET['linker_intake_review'] ) ) {
			$existing = $args['meta_query'] ?? array();
			// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- Native staff-only held-record listing, supports HPOS.
			$args['meta_query'] = array(
				'relation' => 'AND',
				array(
					'key'   => \Linker\Commerce\Inquiry\Assessment\Queue::PENDING,
					'value' => 'held',
				),
				array(
					'key'     => Intake::LANE_META,
					'value'   => array( 'verification', 'individual' ),
					'compare' => 'IN',
				),
			);
			if ( is_array( $existing ) && array() !== $existing ) {
				$args['meta_query'][] = $existing;
			}
		}
		return $args;
	}

	/**
	 * Classic Woo storage uses WordPress's native staff list query.
	 *
	 * @param \WP_Query $query Native posts query.
	 */
	public function classic_query( \WP_Query $query ): void {
		if ( ! is_admin() || ! $query->is_main_query() || 'shop_order' !== $query->get( 'post_type' ) ) {
			return;
		}
		// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- Preserve native staff query restrictions while adding bounded review filtering.
		$args = $this->query( array( 'meta_query' => $query->get( 'meta_query' ) ) );
		if ( isset( $args['meta_query'] ) ) {
			$query->set( 'meta_query', $args['meta_query'] );
		}
	}

	/** Native Woo edit screens share the same bounded registry view. */
	public function boxes(): void {
		foreach ( array( 'shop_order', 'woocommerce_page_wc-orders' ) as $screen ) {
			add_meta_box( 'linker-review-intake', __( 'Public request review', 'linker-commerce' ), array( $this, 'box' ), $screen, 'normal' );
		}
	}

	/**
	 * A saved result may be shown only through the submitter's own native session.
	 *
	 * @param WC_Order $order Actual saved inquiry.
	 */
	public static function remember( WC_Order $order ): void {
		wc_load_cart();
		WC()->session->set( 'linker_review_saved', $order->get_order_number() );
		if ( WC()->session instanceof \WC_Session_Handler ) {
			WC()->session->set_customer_session_cookie( true );
		}
	}

	/**
	 * No number is taken from a public query string.
	 *
	 * @param WC_Order|null $order Authorized native confirmation record, or own session.
	 */
	public static function saved_message( ?WC_Order $order = null ): string {
		$number = $order instanceof WC_Order ? $order->get_order_number() : (string) WC()->session->get( 'linker_review_saved', '' );
		/* translators: %s is the native inquiry number saved for this browser. */
		return '' !== $number ? sprintf( __( 'Your inquiry #%s is saved and waiting for review. We have not sent a confirmation email.', 'linker-commerce' ), $number ) : __( 'Please check the status of your inquiry before sending it again.', 'linker-commerce' );
	}

	/**
	 * Native staff data; content remains in the ordinary order editor.
	 *
	 * @param mixed $subject Native Woo order or WP post.
	 */
	public function box( mixed $subject ): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		$order  = $subject instanceof WC_Order ? $subject : wc_get_order( is_object( $subject ) && isset( $subject->ID ) ? (int) $subject->ID : 0 );
		$record = $order instanceof WC_Order ? $order->get_meta( Intake::META ) : null;
		if ( is_array( $record ) ) {
			echo '<p><strong>' . esc_html__( 'Saved for staff review', 'linker-commerce' ) . '</strong></p><dl><dt>' . esc_html__( 'Review class', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $record['lane'] ) . '</dd><dt>' . esc_html__( 'Rule version', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $record['rule'] ) . '</dd></dl>';
		}
		$state = get_option(
			IntakeStore::OPTION,
			array(
				'entries'        => array(),
				'campaign_count' => 0,
			)
		);
		if ( is_array( $state ) && is_array( $state['entries'] ?? null ) ) {
			echo '<h3>' . esc_html__( 'Unresolved review capacity', 'linker-commerce' ) . '</h3><ul>';
			foreach ( IntakeStore::CAPACITY as $lane => $capacity ) {
				$count = count( array_filter( $state['entries'], static fn ( array $entry ): bool => $entry['lane'] === $lane ) );
				echo '<li>' . esc_html( $lane . ': ' . $count . ' / ' . $capacity ) . '</li>';
			}
			echo '</ul><p>' . esc_html__( 'Confirmed activity attempts', 'linker-commerce' ) . ': ' . esc_html( (string) ( $state['campaign_count'] ?? 0 ) ) . '</p>';
		}
		$enabled = 'yes' !== get_option( Campaign::DISABLED, 'no' );
		echo '<p>' . esc_html__( 'Rule version', 'linker-commerce' ) . ': ' . esc_html( Campaign::VERSION ) . '</p><p>' . esc_html( $enabled ? __( 'Confirmed activity rule enabled', 'linker-commerce' ) : __( 'Confirmed activity rule disabled', 'linker-commerce' ) ) . '</p>';
		echo '<p><button class="button" type="submit" form="linker-campaign-rule">' . esc_html( $enabled ? __( 'Disable this rule', 'linker-commerce' ) : __( 'Enable this rule', 'linker-commerce' ) ) . '</button></p>';
		add_action(
			'admin_footer',
			static function () use ( $enabled ): void {
				echo '<form id="linker-campaign-rule" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="linker_campaign_rule" /><input type="hidden" name="disabled" value="' . esc_attr( $enabled ? 'yes' : 'no' ) . '" />';
				wp_nonce_field( 'linker_campaign_rule_' . Campaign::VERSION );
				echo '</form>';
			}
		);
	}

	/** Capability plus version-bound nonce; no customer input can switch this rule. */
	public function rule(): void {
		check_admin_referer( 'linker_campaign_rule_' . Campaign::VERSION );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_die( esc_html__( 'You cannot review this inquiry.', 'linker-commerce' ), '', array( 'response' => 403 ) );
		}
		$value = isset( $_POST['disabled'] ) && 'yes' === $_POST['disabled'] ? 'yes' : 'no';
		update_option( Campaign::DISABLED, $value, false );
		update_option(
			'linker_confirmed_campaign_decision',
			array(
				'at'       => time(),
				'user'     => get_current_user_id(),
				'version'  => Campaign::VERSION,
				'disabled' => $value,
			),
			false
		);
		wp_safe_redirect( admin_url( 'admin.php?page=wc-orders' ) );
		exit;
	}

	/**
	 * Added private native metadata follows the verified Woo export lifecycle.
	 *
	 * @param list<array{name:string,value:mixed}> $data Existing native export.
	 * @param WC_Order                             $order Verified requester's order.
	 * @return list<array{name:string,value:mixed}>
	 */
	public function export( array $data, WC_Order $order ): array {
		$value = $order->get_meta( Intake::META );
		if ( is_array( $value ) ) {
			$data[] = array(
				'name'  => __( 'Public request review', 'linker-commerce' ),
				'value' => wp_json_encode( $value ),
			);
		}
		return $data;
	}
}

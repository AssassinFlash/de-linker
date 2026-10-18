<?php
/**
 * Tests for Woo account data feeding LiveCanvas fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * The adapter stays behind Woo's account/login guards, and its filter preserves
 * Woo's customer/paging values. It must not disclose guest rows or accept PHP
 * hook names from a shortcode attribute.
 *
 * @covers \Linker\Commerce\Presentation\AccountTemplates
 */
final class AccountTemplatesTest extends TestCase {

	/** Logged-out requests retain Woo's forms and templates. */
	public function test_guest_keeps_native_template_and_cannot_read_rows(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$adapter = new AccountTemplates();
		$this->assertSame( '/woo/orders.php', $adapter->template( '/woo/orders.php', 'myaccount/orders.php' ) );
		$this->assertSame( '', $adapter->rows( array( 'type' => 'dashboard' ) ) );
	}

	/** Forms, email templates and checkout never route to account LC fragments. */
	public function test_only_signed_in_account_content_is_adapted(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction(
			'shortcode_exists',
			array(
				'args'   => array( 'lc_if' ),
				'return' => true,
			)
		);
		$adapter = new AccountTemplates();
		foreach ( array( 'myaccount/orders.php', 'myaccount/view-order.php', 'myaccount/dashboard.php' ) as $name ) {
			$this->assertStringEndsWith( '/templates/myaccount/livecanvas.php', $adapter->template( '/woo/native.php', $name ) );
		}
		foreach ( array( 'myaccount/form-login.php', 'myaccount/form-edit-account.php', 'myaccount/form-edit-address.php', 'checkout/thankyou.php', 'emails/customer-completed-order.php' ) as $name ) {
			$this->assertSame( '/woo/native.php', $adapter->template( '/woo/native.php', $name ) );
		}
	}

	/** An absent LC keeps the mature native Woo fallback. */
	public function test_without_lc_native_template_stays(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => false ) );
		$this->assertSame( '/woo/orders.php', ( new AccountTemplates() )->template( '/woo/orders.php', 'myaccount/orders.php' ) );
	}

	/** The tab only narrows statuses, without replacing Woo's ownership/paging. */
	public function test_open_tab_keeps_customer_and_pagination(): void {
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( string $value ): string => stripslashes( $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $value ): string => (string) preg_replace( '/[^a-z0-9_-]/', '', strtolower( $value ) ) ) );
		$adapter = new AccountTemplates();
		$query   = array(
			'customer_id' => 3,
			'page'        => 2,
			'limit'       => 10,
			'paginate'    => true,
		);
		unset( $_GET['inquiry-status'] );
		$this->assertSame( $query, $adapter->orders_query( $query ) );
		$_GET['inquiry-status'] = 'open';
		try {
			$this->assertSame( $query + array( 'status' => array( 'inquiry-received', 'proforma-issued' ) ), $adapter->orders_query( $query ) );
		} finally {
			unset( $_GET['inquiry-status'] );
		}
	}

	/** State shortcuts only narrow Woo's own query; arbitrary states are ignored. */
	public function test_state_shortcuts_preserve_customer_and_paging(): void {
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( string $value ): string => stripslashes( $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $value ): string => (string) preg_replace( '/[^a-z0-9_-]/', '', strtolower( $value ) ) ) );
		$adapter = new AccountTemplates();
		$query   = array(
			'customer_id' => 5,
			'page'        => 2,
			'limit'       => 10,
			'paginate'    => true,
		);
		try {
			foreach ( array( 'inquiry-received', 'proforma-issued', 'completed', 'cancelled' ) as $status ) {
				$_GET['inquiry-status'] = $status;
				$this->assertSame( $query + array( 'status' => array( $status ) ), $adapter->orders_query( $query ) );
			}
			$_GET['inquiry-status'] = 'processing';
			$this->assertSame( $query, $adapter->orders_query( $query ) );
			$_GET['inquiry-status'] = array( 'completed' );
			// @phpstan-ignore method.alreadyNarrowedType (the guard is the point: an array in $_GET must be ignored, not fatal. PHPStan proves the guarded branch dead and reads the assertion as redundant; at runtime it is the assertion.)
			$this->assertSame( $query, $adapter->orders_query( $query ) );
		} finally {
			unset( $_GET['inquiry-status'] );
		}
	}

	/** Native page links retain selection instead of silently widening on page two. */
	public function test_pagination_keeps_selected_state(): void {
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wc_get_endpoint_url', array( 'return' => static fn ( string $endpoint, string $page ): string => 'https://example.test/inquiries/' . $page . '/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . http_build_query( $query ) ) );
		$adapter = new AccountTemplates();
		$method  = new \ReflectionMethod( $adapter, 'page_url' );
		try {
			$_GET['inquiry-status'] = 'cancelled';
			$this->assertSame( 'https://example.test/inquiries/2/?inquiry-status=cancelled', $method->invoke( $adapter, 2 ) );
			$_GET['inquiry-status'] = 'open';
			$this->assertSame( 'https://example.test/inquiries/2/?inquiry-status=open', $method->invoke( $adapter, 2 ) );
			unset( $_GET['inquiry-status'] );
			$this->assertSame( 'https://example.test/inquiries/2/', $method->invoke( $adapter, 2 ) );
		} finally {
			unset( $_GET['inquiry-status'] );
		}
	}

	/** The inquiry row's own summary: how many products, and the number behind it. */
	public function test_inquiry_row_carries_the_product_count_and_the_view_label(): void {
		$this->visible_prices( true );
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $number ): string => (string) $number ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_status' )->andReturn( Statuses::RECEIVED );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( '' );
		$order->allows( 'get_date_created' )->andReturn( null );
		$order->allows( 'get_formatted_order_total' )->andReturn( '€1.00' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		$first = Mockery::mock( \WC_Order_Item_Product::class );
		$first->allows( 'get_quantity' )->andReturn( 2 );
		$second = Mockery::mock( \WC_Order_Item_Product::class );
		$second->allows( 'get_quantity' )->andReturn( 1 );
		$order->allows( 'get_items' )->andReturn( array( $first, $second ) );

		$row = ( new AccountTemplates() )->inquiry_row( $order );

		$this->assertSame( '3 products', $row['items-summary'] );
		$this->assertArrayNotHasKey( 'items-count', $row, 'The row carries the summary the list shows, not a second count nothing reads.' );
		$this->assertSame( 'View inquiry #20', $row['view-aria'] );
	}

	/** Account inquiry rows use the shared price answer, including a recorded zero. */
	public function test_inquiry_total_is_hidden_when_shared_price_rule_says_no(): void {
		$this->plain_text();
		$this->visible_prices( false );
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => 'Inquiry received' ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => '0' ) );
		$row = ( new AccountTemplates() )->inquiry_row( $this->inquiry( Statuses::RECEIVED, '' ) );
		$this->assertSame( '', $row['total'] );
	}

	/** Shortcode attributes cannot choose an arbitrary PHP action. */
	public function test_arbitrary_hook_is_not_invoked(): void {
		$this->assertSame( '', ( new AccountTemplates() )->hook( array( 'name' => 'delete_user' ) ) );
	}

	/**
	 * An inquiry in "Proforma invoice issued" renders a download link and the stored number.
	 * A received inquiry renders neither. The number is the order meta, never invented.
	 */
	public function test_proforma_issued_renders_the_download_and_the_number(): void {
		$this->visible_prices( true );
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $number ): string => (string) $number ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ),
			)
		);
		$adapter = new AccountTemplates();

		$issued = $adapter->inquiry_row( $this->inquiry( Statuses::PROFORMA, 'PI-2026-0008' ) );
		$this->assertSame( 'PI-2026-0008', $issued['proforma_number'] );
		$this->assertSame( '1', $issued['proforma'] );
		$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $issued['proforma_url'] );

		$bare = $adapter->inquiry_row( $this->inquiry( Statuses::PROFORMA, '' ) );
		$this->assertSame( '', $bare['proforma_number'] );
		$this->assertSame( '', $bare['proforma'] );
		$this->assertSame( '', $bare['proforma_url'] );

			$received = $adapter->inquiry_row( $this->inquiry( Statuses::RECEIVED, '' ) );
			$this->assertSame( '', $received['proforma'] );
			$this->assertSame( '', $received['proforma_number'] );
			$this->assertSame( '', $received['proforma_url'] );

			// Completed keeps the number and the download. The status word is not the gate.
			$completed = $adapter->inquiry_row( $this->inquiry( 'completed', 'DLK-PF-2026-0003' ) );
			$this->assertSame( 'DLK-PF-2026-0003', $completed['proforma_number'] );
			$this->assertSame( '1', $completed['proforma'] );
			$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $completed['proforma_url'] );
	}

		/**
		 * The inquiry detail and the Documents page both carry the number and a download link.
		 * German labels are the formal catalogue strings, not a translation invented in this test.
		 */
	public function test_detail_and_documents_both_carry_the_number_and_the_link(): void {
		$this->visible_prices( true );
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $number ): string => (string) $number ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ),
			)
		);
		WP_Mock::userFunction(
			'__',
			array(
				'return' => static function ( string $text ): string {
					return array(
						'Proforma invoice (PDF)' => 'Proformarechnung (PDF)',
						'Download (PDF)'         => 'Herunterladen (PDF)',
						'Proforma invoice %1$s (inquiry #%2$s)' => 'Proformarechnung %1$s (Anfrage #%2$s)',
					)[ $text ] ?? $text;
				},
			)
		);
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_url', array( 'return' => static fn ( string $url ): string => $url ) );

		$adapter = new AccountTemplates();
		$order   = $this->inquiry( Statuses::PROFORMA, 'DLK-PF-2026-0001' );
		$row     = $adapter->inquiry_row( $order );
		$detail  = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/livecanvas/account/proforma.html' );
		$summary = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/livecanvas/account/summary.html' );
		$listed  = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/livecanvas/account/document-row.html' );

		// Inquiry detail: the summary fragment includes the Proforma block, which prints the number and the link.
		$this->assertStringContainsString( 'type="proforma"', $summary );
		$this->assertStringContainsString( 'key="number"', $detail );
		$this->assertStringContainsString( 'key=\'url\'', $detail );
		$this->assertStringContainsString( 'data-action="proforma"', $detail );
		$this->assertSame( 'DLK-PF-2026-0001', $row['proforma_number'] );
		$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $row['proforma_url'] );
		$this->assertSame( 'Proformarechnung (PDF)', __( 'Proforma invoice (PDF)', 'linker-commerce' ) );

		// Documents: the row prints the title (number inside) and the same download URL.
		$this->assertStringContainsString( 'key="title"', $listed );
		$this->assertStringContainsString( 'key=\'url\'', $listed );
		$this->assertSame( 'Herunterladen (PDF)', __( 'Download (PDF)', 'linker-commerce' ) );
			$this->assertSame(
				'Proformarechnung DLK-PF-2026-0001 (Anfrage #20)',
				sprintf(
					/* translators: 1: Proforma number, 2: inquiry number. */
					__( 'Proforma invoice %1$s (inquiry #%2$s)', 'linker-commerce' ),
					$row['proforma_number'],
					$order->get_order_number()
				)
			);
	}

	/** Guests get no private account navigation. */
	public function test_nav_is_empty_for_guests(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$adapter = new AccountTemplates();
		$this->assertSame( '', $adapter->nav() );
	}

	/**
	 * Account states that retain the complete workspace.
	 *
	 * @return array<string, array{string}>
	 */
	public static function workspace_states(): array {
		return array(
			'pending'    => array( Approval::PENDING ),
			'approved'   => array( Approval::APPROVED ),
			'restricted' => array( Approval::RESTRICTED ),
		);
	}

	/** Pending customers keep the contact slot as well as the endpoint content. */
	public function test_pending_account_keeps_its_contact_slot(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::expectAction( 'linker_account_after_content' );
		( new AccountTemplates() )->hook( array( 'name' => 'after-content' ) );
		$this->assertConditionsMet();
	}

	/**
	 * An approved account's navigation groups the same menu the header dropdown
	 * reads: the workplace, then the account records with sign-out last. The
	 * dashboard is current when no endpoint is being read.
	 *
	 * @dataProvider workspace_states
	 * @param string $status Account state.
	 */
	public function test_nav_groups_the_account_menu_for_a_signed_in_account( string $status ): void {
		$this->plain_text();
		$this->approval_meta( array( Approval::STATUS_META => $status ) );
		WP_Mock::userFunction(
			'wc_get_account_menu_items',
			array(
				'return' => array(
					'dashboard'       => 'Overview',
					'orders'          => 'Inquiries',
					'saved-solutions' => 'Saved solutions',
					'documents'       => 'Documents',
					'edit-address'    => 'Company data',
					'edit-account'    => 'Account details',
					'customer-logout' => 'Sign out',
				),
			)
		);
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => static fn ( string $endpoint ): string => 'https://example.test/my-account/' . $endpoint . '/' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				/* Both shapes in use: (array, url) and (key, value, url). */
				'return' => static function ( $first, $second = '', string $third = '' ): string {
					return is_array( $first ) ? $second . '?' . http_build_query( $first ) : $third . '?' . $first . '=' . $second;
				},
			)
		);
		WP_Mock::userFunction( 'wc_logout_url', array( 'return' => static fn ( string $redirect ): string => 'https://example.test/logout/?redirect_to=' . rawurlencode( $redirect ) . '&_wpnonce=abc' ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$adapter = new AccountTemplates();
		$this->expand_fields( $adapter );

		$html = $adapter->nav();
		$this->assertStringContainsString( '<nav class="linker-account-nav"', $html );
		$this->assertSame( 2, substr_count( $html, 'linker-account-nav-group' ) );
		$this->assertStringContainsString( 'Workplace', $html );
		$this->assertStringContainsString( 'https://example.test/my-account/orders/', $html );
		// Sign-out is the nonce-carrying one-click URL, back on the account page
		// with the state the sign-in card reads. The plain endpoint URL would
		// ask for confirmation first.
		$this->assertStringContainsString( 'https://example.test/logout/?redirect_to=https%3A%2F%2Fexample.test%2Fmy-account%2F%3Fsigned-out%3Dtrue&_wpnonce=abc', $html );
		$this->assertStringNotContainsString( 'https://example.test/my-account/customer-logout/', $html );
		$this->assertStringContainsString( 'aria-current="page"', $html );
	}

	/**
	 * The dashboard renders one tile per inquiry state with that state's count,
	 * the newest inquiries as rows and the documents entry — empty documents
	 * fall back to the empty row, never to nothing.
	 */
	public function test_dashboard_tiles_rows_and_documents_entry(): void {
		$this->visible_prices( true );
		$this->plain_text();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $number ): string => (string) $number ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => static fn ( string $endpoint ): string => 'https://example.test/my-account/' . $endpoint . '/' ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ),
			)
		);
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		$orders = array(
			$this->inquiry( Statuses::RECEIVED, '' ),
			$this->inquiry( Statuses::PROFORMA, 'DLK-PF-2026-0001' ),
			$this->inquiry( 'completed', 'DLK-PF-2026-0002' ),
		);
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'return' => static function ( array $args ) use ( $orders ): array {
					$status = $args['status'] ?? array();
					return isset( $args['meta_key'] ) || array( Statuses::PROFORMA ) === $status ? array() : $orders;
				},
			)
		);
		$adapter = new AccountTemplates();
		$this->expand_fields( $adapter );

		$html = $adapter->rows( array( 'type' => 'dashboard' ) );
		$this->assertSame( 4, substr_count( $html, 'linker-account-tile-count' ) );
		foreach ( array( 'inquiry-received', 'proforma-issued', 'completed', 'cancelled' ) as $status ) {
			$this->assertStringContainsString( 'data-status="' . $status . '"', $html );
		}
		// Three orders: one per state, none cancelled.
		$this->assertSame( 3, substr_count( $html, '<span class="linker-account-tile-count">1</span>' ) );
		$this->assertStringContainsString( '<span class="linker-account-tile-count">0</span>', $html );
		$this->assertSame( 3, substr_count( $html, 'linker-account-row-number' ) );
		$this->assertSame( 3, substr_count( $html, '#20' ) );
		$this->assertStringContainsString( 'linker-account-panel', $html );
		$this->assertStringContainsString( 'linker-account-empty', $html );
	}

	/**
	 * The canonical price filter is a WordPress boundary, not a second rule.
	 *
	 * @param bool $visible The shared rule's answer.
	 */
	private function visible_prices( bool $visible ): void {
		$prices = WP_Mock::onFilter( 'linker_commerce_visitor_sees_prices' )->with( false );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $prices );
		$prices->reply( $visible );
	}

	/**
	 * Lets do_shortcode expand the field tags through the adapter's own field(),
	 * so a fragment's substituted values can be asserted; the other shortcodes
	 * stay as tags.
	 *
	 * @param AccountTemplates $adapter The adapter under test.
	 */
	private function expand_fields( AccountTemplates $adapter ): void {
		WP_Mock::userFunction(
			'do_shortcode',
			array(
				'return' => static function ( string $content ) use ( $adapter ): string {
					return (string) preg_replace_callback(
						'/\[linker_account_field key=["\']([a-z-]+)["\']\]/',
						static fn ( array $m ): string => $adapter->field( array( 'key' => $m[1] ) ),
						$content
					);
				},
			)
		);
	}

	/**
	 * An inquiry for the account-row assertions.
	 *
	 * @param string $status Status slug.
	 * @param string $number Stored Proforma number.
	 */
	private function inquiry( string $status, string $number ): WC_Order {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_status' )->andReturn( $status );
		$order->allows( 'has_status' )->andReturnUsing( static fn ( string $asked ): bool => $asked === $status );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( $number );
		$order->allows( 'get_items' )->andReturn( array() );
		$order->allows( 'get_date_created' )->andReturn( null );
		$order->allows( 'get_formatted_order_total' )->andReturn( '€1.00' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		return $order;
	}
}

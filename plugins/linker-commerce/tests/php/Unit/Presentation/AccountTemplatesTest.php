<?php
/**
 * Tests for Woo account data feeding LiveCanvas fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
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

	/** The account opens the same project through its current language entry. */
	public function test_planning_project_link_uses_current_language_and_preserves_identity(): void {
		$this->plain_text();
		$this->signed_in( 66 );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 66 ) );
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'solution-configurator' )->andReturn( new \WP_Post( (object) array( 'ID' => 80 ) ) );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'de' );
		WP_Mock::userFunction( 'pll_get_post' )->with( 80, 'de' )->andReturn( 800 );
		WP_Mock::userFunction( 'get_permalink' )->with( 800 )->andReturn( 'https://example.test/de/loesungskonfigurator/' );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . http_build_query( $query ) ) );
		WP_Mock::userFunction( 'wp_date', array( 'return' => '27 Oct 2026' ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( mixed $value ): bool => $value instanceof \WP_Error ) );
		$adapter = new AccountTemplates();
		$this->expand_fields( $adapter );
		$id       = str_repeat( 'a', 32 );
		$projects = WP_Mock::onFilter( 'linker_commerce_planning_projects' )->with( null );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $projects );
		$projects->reply(
			array(
				array(
					'id'         => $id,
					'title'      => 'Same owned project',
					'updated_at' => 1793040000,
				),
			)
		);
		$html = $adapter->rows( array( 'type' => 'planning-projects' ) );
		$this->assertStringContainsString( 'https://example.test/de/loesungskonfigurator/?project=' . $id . '#lp-overview', $html );
		$this->assertStringContainsString( 'Same owned project', $html );
		$this->assertStringNotContainsString( 'saved_solution=', $html );
		$this->assertStringNotContainsString( 'linker_solution_to_draft', $html );
	}

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
		$order->allows( 'get_item_count' )->andReturn( 3 );
		$order->allows( 'get_meta' )->with( '_linker_inquiry_source' )->andReturn( '' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		$first = Mockery::mock( \WC_Order_Item_Product::class );
		$first->allows( 'get_quantity' )->andReturn( 2 );
		$first->allows( 'get_meta' )->with( \Linker\Commerce\Gating\PriceDisplay::ITEM_REASON_META )->andReturn( '' );
		$second = Mockery::mock( \WC_Order_Item_Product::class );
		$second->allows( 'get_quantity' )->andReturn( 1 );
		$second->allows( 'get_meta' )->with( \Linker\Commerce\Gating\PriceDisplay::ITEM_REASON_META )->andReturn( '' );
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

	/** An approved customer cannot read a monetary total for an unpriced inquiry. */
	public function test_approved_unpriced_inquiry_has_no_total(): void {
		$this->plain_text();
		$this->visible_prices( true );
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => 'Inquiry received' ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => '1' ) );
		$item = Mockery::mock( \WC_Order_Item_Product::class );
		$item->allows( 'get_quantity' )->andReturn( 1 );
		$item->allows( 'get_meta' )->with( \Linker\Commerce\Gating\PriceDisplay::ITEM_REASON_META )->andReturn( 'approval' );
		$item->allows( 'get_total' )->andReturn( '0' );
		$row = ( new AccountTemplates() )->inquiry_row( $this->inquiry( Statuses::RECEIVED, '', array( $item ) ) );
		$this->assertSame( '', $row['total'] );
	}

	/** The pending inquiry summary omits its monetary field, including its label. */
	public function test_pending_summary_has_no_empty_amount_label(): void {
		$this->plain_text();
		$this->visible_prices( false );
		WP_Mock::userFunction( 'add_shortcode' );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => 'Inquiry received' ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => '0' ) );
		$adapter = new AccountTemplates();
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $adapter, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $adapter, 'orders_query' ) );
		$adapter->register();
		$this->expand_fields( $adapter );
		ob_start();
		AccountTemplates::output(
			array(
				'template_name' => 'myaccount/view-order.php',
				'args'          => array( 'order' => $this->inquiry( Statuses::RECEIVED, '' ) ),
			)
		);
		$html = (string) ob_get_clean();
		$this->assertStringNotContainsString( 'Amount', $html );
		$this->assertStringNotContainsString( '€', $html );
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
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );
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
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );
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
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );
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
	 * A saved solution shows its design report only when the file is stored.
	 * The link is not a price gate: a pending account still gets it, and
	 * another customer's solution is omitted.
	 */
	public function test_saved_solution_links_its_design_report_without_prices(): void {
		$projects = WP_Mock::onFilter( 'linker_commerce_planning_projects' )->with( null );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $projects );
		$projects->reply( null );
		$this->visible_prices( false );
		$this->plain_text();
		WP_Mock::userFunction( 'add_shortcode' );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		WP_Mock::userFunction( 'wp_date', array( 'return' => '9 Oct 2026' ) );
		WP_Mock::userFunction( 'get_post_timestamp', array( 'return' => 1700000000 ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '<input type="hidden" name="_wpnonce" value="n" />' ) );
		$root = sys_get_temp_dir() . '/linker-report-gate-' . getmypid();
		WP_Mock::userFunction( 'home_url' )->andReturn( 'https://example.test/' );
		mkdir( $root . '/solution-reports/45', 0777, true );
		file_put_contents( $root . '/solution-reports/45/design-report.pdf', '%PDF-1.4' );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $root ) ) );
		WP_Mock::userFunction( 'wc_get_product', array( 'times' => 0 ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ): string {
					if ( 45 === $id && SavedSolutions::ITEMS_META === $key ) {
						return '[{"product_id":9,"quantity":2}]';
					}
					if ( 45 === $id && SavedSolutions::DESIGN_META === $key ) {
						return '{"snapshot":{"kind":"residential","publication":{"products":[{"product_id":9,"product_revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}],"documents":[],"reference_inputs":[],"engineering_contract":2,"compatibility_revision":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"selected":{"lines":[{"product":{"id":9,"brand":"EcoFlow","model":"Recorded model at save"},"quantity":2}]}}}';
					}
					return SavedSolutions::REPORT_META === $key && 45 === $id ? '45/design-report.pdf' : '';
				},
			)
		);
		$saved          = new SavedSolutions( new PrivateFiles( 'solution-reports' ), '/plugin/templates/' );
		$with_report    = (object) array(
			'ID'          => 45,
			'post_author' => 5,
			'post_title'  => 'Munich home',
		);
		$without_report = (object) array(
			'ID'          => 46,
			'post_author' => 5,
			'post_title'  => 'No report yet',
		);
		$other          = (object) array(
			'ID'          => 47,
			'post_author' => 9,
			'post_title'  => 'Someone else',
		);
		$adapter        = new AccountTemplates();
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $adapter, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $adapter, 'orders_query' ) );
		$adapter->register();
		$this->expand_fields( $adapter );
		ob_start();
		AccountTemplates::output(
			array(
				'template_name' => 'myaccount/linker-saved-solutions.php',
				'args'          => array(
					'saved'     => $saved,
					'solutions' => array( $with_report, $without_report, $other ),
				),
			)
		);
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'Munich home', $html );
		$this->assertStringContainsString( 'No report yet', $html );
		$this->assertStringContainsString( '2 × EcoFlow Recorded model at save', $html );
		$this->assertStringNotContainsString( 'Someone else', $html );
		$this->assertSame( 1, substr_count( $html, 'Design report (PDF)' ) );
		$this->assertStringNotContainsString( 'name="linker_solution_to_draft"', $html );
		$this->assertSame( 2, substr_count( $html, 'This saved solution needs a new calculation before it can be added to your solution draft.' ) );
		$this->assertStringContainsString( 'linker-document=report&id=45', $html );
		$this->assertStringNotContainsString( 'linker-document=report&id=46', $html );
		$this->assertStringNotContainsString( 'linker-document=report&id=47', $html );
	}

	/** Legacy product references have a current, published way forward without authorising an old design. */
	public function test_legacy_solution_has_current_product_links_and_recalculation_guidance(): void {
		$projects = WP_Mock::onFilter( 'linker_commerce_planning_projects' )->with( null );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $projects );
		$projects->reply( null );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . http_build_query( $query ) ) );
		$this->visible_prices( false );
		$this->plain_text();
		WP_Mock::userFunction( 'add_shortcode' );
		WP_Mock::userFunction( 'wp_date', array( 'return' => '9 Oct 2026' ) );
		WP_Mock::userFunction( 'get_post_timestamp', array( 'return' => 1700000000 ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '<input type="hidden" name="_wpnonce" value="n" />' ) );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			static fn ( int $id, string $key ): string => SavedSolutions::ITEMS_META === $key ? '[{"product_id":9,"quantity":2},{"product_id":10,"quantity":1}]' : ''
		);
		WP_Mock::userFunction( 'determine_locale' )->andReturn( 'de_DE_formal' );
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing( static fn ( int $id, string $language ): int => 'de' === $language ? $id * 10 : $id );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->once()->andReturn( true );
		WP_Mock::userFunction( 'has_filter' )->with( 'linker_commerce_facts_product_id' )->andReturn( true );
		foreach (
			array(
				90  => 9,
				100 => 10,
			) as $display_id => $source_id
		) {
			/**
			 * The filter factory supplies its filter-specific responder.
			 *
			 * @var \WP_Mock\Filter_Responder $filter
			 */
			$filter = WP_Mock::onFilter( 'linker_commerce_facts_product_id' )->with( $display_id );
			$filter->reply( $source_id );
		}
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( static fn ( int $id ): string => 10 === $id ? 'draft' : 'publish' );
		$product = Mockery::mock( \WC_Product::class );
		$product->expects( 'get_name' )->andReturn( 'Aktuelles Woo Modell' );
		$product->expects( 'get_permalink' )->andReturn( 'https://example.test/de/produkt/current/' );
		WP_Mock::userFunction( 'wc_get_product' )->once()->with( 90 )->andReturn( $product );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'de' );
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'solution-configurator' )->andReturn( new \WP_Post( (object) array( 'ID' => 80 ) ) );
		WP_Mock::userFunction( 'get_permalink' )->with( 800 )->andReturn( 'https://example.test/de/loesungskonfigurator/' );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => sys_get_temp_dir() ) ) );
		$adapter = new AccountTemplates();
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $adapter, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $adapter, 'orders_query' ) );
		$adapter->register();
		$this->expand_fields( $adapter );
		ob_start();
		AccountTemplates::output(
			array(
				'template_name' => 'myaccount/linker-saved-solutions.php',
				'args'          => array(
					'saved'     => new SavedSolutions( new PrivateFiles( 'solution-reports' ), '/plugin/templates/' ),
					'solutions' => array(
						(object) array(
							'ID'          => 45,
							'post_author' => 5,
							'post_title'  => 'Legacy original',
						),
					),
				),
			)
		);
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'Aktuelles Woo Modell', $html );
		$this->assertStringContainsString( 'https://example.test/de/produkt/current/', $html );
		$this->assertStringContainsString( '1 × Product 10', $html );
		$this->assertStringContainsString( 'Legacy original', $html );
		$this->assertStringContainsString( 'This saved solution needs a new calculation before it can be added to your solution draft.', $html );
		$this->assertStringContainsString( 'Open the Solution Configurator', $html );
		$this->assertStringContainsString( 'https://example.test/de/loesungskonfigurator/', $html );
		$this->assertStringNotContainsString( 'name="linker_solution_to_draft"', $html );
		$this->assertStringContainsString( 'name="linker_solution_remove"', $html );
	}

	/**
	 * The canonical price filter is a WordPress boundary, not a second rule.
	 *
	 * @param bool $visible The shared rule's answer.
	 */
	private function visible_prices( bool $visible ): void {
		$this->approval_meta( array( Approval::STATUS_META => $visible ? Approval::APPROVED : Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
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
						'/\[linker_account_(field|rows|text) (key|type)=["\']([a-z-]+)["\']\]/',
						static fn ( array $m ): string => $adapter->{$m[1]}( array( $m[2] => $m[3] ) ),
						$content
					);
				},
			)
		);
	}

	/**
	 * An inquiry for the account-row assertions.
	 *
	 * @param string                        $status Status slug.
	 * @param string                        $number Stored Proforma number.
	 * @param array<\WC_Order_Item_Product> $items Inquiry product lines.
	 */
	private function inquiry( string $status, string $number, array $items = array() ): WC_Order {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_status' )->andReturn( $status );
		$order->allows( 'has_status' )->andReturnUsing( static fn ( string $asked ): bool => $asked === $status );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( $number );
		$order->allows( 'get_items' )->andReturn( $items );
		$order->allows( 'get_item_count' )->andReturn( count( $items ) );
		$order->allows( 'get_meta' )->with( '_linker_inquiry_source' )->andReturn( '' );
		$order->allows( 'get_date_created' )->andReturn( null );
		$order->allows( 'get_formatted_order_total' )->andReturn( '€1.00' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		return $order;
	}
}

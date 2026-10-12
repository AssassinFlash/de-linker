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
		$this->assertSame( '', $adapter->rows( array( 'type' => 'groups' ) ) );
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
		$adapter = new AccountTemplates();
		$query   = array(
			'customer_id' => 3,
			'page'        => 2,
			'limit'       => 10,
			'paginate'    => true,
		);
		unset( $_GET['inquiries'] );
		$this->assertSame( $query, $adapter->orders_query( $query ) );
		$_GET['inquiries'] = 'open';
		try {
			$this->assertSame( $query + array( 'status' => array( 'inquiry-received', 'proforma-issued' ) ), $adapter->orders_query( $query ) );
		} finally {
			unset( $_GET['inquiries'] );
		}
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
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
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
		WP_Mock::userFunction( 'wc_get_order_status_name', array( 'return' => static fn ( string $status ): string => $status ) );
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

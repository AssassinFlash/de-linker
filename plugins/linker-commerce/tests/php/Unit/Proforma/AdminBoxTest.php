<?php
/**
 * Tests for the Proforma box on the inquiry screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\AdminBox;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Order_Item_Product;
use WP_Mock;

/**
 * Tests for AdminBox.
 *
 * @covers \Linker\Commerce\Proforma\AdminBox
 */
final class AdminBoxTest extends TestCase {

	/**
	 * Option values of the test.
	 *
	 * @var array<string, mixed>
	 */
	private array $option_values = array( Options::BANK_IBAN => 'DE89370400440532013000' );

	/**
	 * Translation and escaping return their input; options from $option_values.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->option_values[ $name ] ?? $default_value ) );
		$_POST = array();
	}

	/**
	 * Clears the posted form.
	 */
	public function tearDown(): void {
		$_POST = array();
		parent::tearDown();
	}

	/**
	 * A box with the real issuer.
	 */
	private function box(): AdminBox {
		$options = new Options();
		return new AdminBox( new Issuer( $options, new Sequence(), new Document( $options ), new Renderer( '/plugin/linker-commerce.php' ), new PrivateFiles( Issuer::DIRECTORY ), new PriceDisplay( new CommerceState() ) ) );
	}

	/**
	 * An inquiry.
	 *
	 * @param string $status Status.
	 * @param string $number Proforma number.
	 * @return WC_Order&\Mockery\MockInterface
	 */
	private function inquiry( string $status, string $number = '' ) {
		$line = Mockery::mock( WC_Order_Item_Product::class );
		$line->allows( 'get_meta' )->andReturn( '' );
		$line->allows( 'get_total' )->andReturn( '100' );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_status' )->andReturn( $status );
		$order->allows( 'get_items' )->andReturn( array( $line ) );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( $number );
		$order->allows( 'get_meta' )->with( Issuer::ISSUED_META )->andReturn( '1760000000' );
		return $order;
	}

	/**
	 * The box appears on the inquiry screen of both order storages, nowhere else.
	 */
	public function test_add(): void {
		WP_Mock::userFunction( 'wc_get_page_screen_id', array( 'return' => 'woocommerce_page_wc-orders' ) );
		$box = $this->box();
		WP_Mock::userFunction(
			'add_meta_box',
			array(
				'times' => 1,
				'args'  => array( 'linker-proforma', 'Proforma invoice', array( $box, 'render' ), 'woocommerce_page_wc-orders', 'side', 'high' ),
			)
		);
		WP_Mock::userFunction(
			'add_meta_box',
			array(
				'times' => 1,
				'args'  => array( 'linker-proforma', 'Proforma invoice', array( $box, 'render' ), 'shop_order', 'side', 'high' ),
			)
		);

		$box->add( 'woocommerce_page_wc-orders' );
		$box->add( 'shop_order' );
		$box->add( 'product' );

		$this->assertConditionsMet();
	}

	/**
	 * A received inquiry shows the button; one that cannot get a Proforma shows why; an issued one shows number, dates and the PDF.
	 */
	public function test_render(): void {
		$box = $this->box();

		ob_start();
		$box->render( $this->inquiry( Statuses::RECEIVED ) );
		$this->assertStringContainsString( '<button type="submit" class="button button-primary" name="linker_issue_proforma" value="1">Issue Proforma</button>', (string) ob_get_clean() );

		ob_start();
		$box->render( $this->inquiry( 'cancelled' ) );
		$this->assertSame( '<p>Only a received inquiry gets a Proforma invoice.</p>', ob_get_clean() );

		WP_Mock::userFunction( 'wp_date', array( 'return' => static fn ( string $format, int $time ): string => gmdate( 'Y-m-d', $time ) ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		ob_start();
		$box->render( $this->inquiry( Statuses::PROFORMA, 'PI-2026-0001' ) );
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( '<strong>PI-2026-0001</strong>', $html );
		$this->assertStringContainsString( 'Issued 2025-10-09', $html );
		$this->assertStringContainsString( 'Valid until 2025-11-08', $html );
		$this->assertStringContainsString( 'https://example.test/?linker-document=proforma&amp;id=20', str_replace( '&', '&amp;', $html ) );
	}

	/**
	 * The button issues the Proforma; a refusal becomes an admin error; without the button or the capability nothing happens.
	 */
	public function test_process(): void {
		$box = $this->box();
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'wc_get_order', array( 'return' => $this->inquiry( 'completed' ) ) );

		$box->process( 20 );

		$_POST[ AdminBox::BUTTON ] = '1';
		WP_Mock::expectAction( 'linker_test_meta_box_error', 'Only a received inquiry gets a Proforma invoice.' );
		$box->process( 20 );
		$this->assertConditionsMet();
	}

	/**
	 * No other order actions; the list says "Inquiry", shows the Proforma number and no shipping column.
	 */
	public function test_actions_and_columns(): void {
		$box = $this->box();

		$this->assertSame( array(), $box->order_actions() );
		$this->assertSame(
			array(
				'cb'              => '<input type="checkbox" />',
				'order_number'    => 'Inquiry',
				'order_status'    => 'Status',
				'linker_proforma' => 'Proforma',
				'order_total'     => 'Total',
			),
			$box->columns(
				array(
					'cb'               => '<input type="checkbox" />',
					'order_number'     => 'Order',
					'order_status'     => 'Status',
					'shipping_address' => 'Ship to',
					'order_total'      => 'Total',
				)
			)
		);

		ob_start();
		$box->column( 'linker_proforma', $this->inquiry( Statuses::PROFORMA, 'PI-2026-0001' ) );
		$box->column( 'order_total', $this->inquiry( Statuses::PROFORMA, 'PI-2026-0001' ) );
		$this->assertSame( 'PI-2026-0001', ob_get_clean() );
	}
}

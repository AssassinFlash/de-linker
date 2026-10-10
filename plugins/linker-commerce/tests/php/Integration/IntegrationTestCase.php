<?php
/**
 * Base of the integration tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use PHPUnit\Framework\TestCase;
use WC_Customer;
use WC_Order;
use WC_Product_Simple;

/**
 * Creates customers, products and inquiries in the local instance and removes
 * them again after each test.
 */
abstract class IntegrationTestCase extends TestCase {

	/**
	 * Skips unless the integration configuration ran the bootstrap: LINKER_WP_ROOT
	 * alone is not the mark, because `just test` also exports it for other
	 * plugins while running this suite under the unit bootstrap (WP_Mock), where
	 * a real WordPress is not loaded (phpunit.integration.xml.dist sets
	 * LINKER_INTEGRATION and checks LINKER_WP_ROOT before any test runs).
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Removals, run in reverse order after the test.
	 *
	 * @var list<callable(): void>
	 */
	private array $cleanup = array();

	/**
	 * Runs the removals and logs out.
	 */
	protected function tearDown(): void {
		foreach ( array_reverse( $this->cleanup ) as $remove ) {
			$remove();
		}
		$this->cleanup = array();
		wp_set_current_user( 0 );
		parent::tearDown();
	}

	/**
	 * Registers a removal.
	 *
	 * @param callable(): void $remove The removal.
	 */
	protected function later( callable $remove ): void {
		$this->cleanup[] = $remove;
	}

	/**
	 * A random tag for names and addresses of test data.
	 */
	protected static function tag(): string {
		return strtolower( wp_generate_password( 8, false ) );
	}

	/**
	 * A customer with a German company address.
	 */
	protected function customer(): WC_Customer {
		$tag = self::tag();
		$id  = wc_create_new_customer( "linker-it-{$tag}@example.test", "linker-it-{$tag}", wp_generate_password( 24 ) );
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);
		$customer = new WC_Customer( $id );
		$customer->set_billing_company( 'Linker Integration Test GmbH' );
		$customer->set_billing_first_name( 'Maria' );
		$customer->set_billing_last_name( 'Beispiel' );
		$customer->set_billing_address_1( 'Teststraße 1' );
		$customer->set_billing_postcode( '39179' );
		$customer->set_billing_city( 'Barleben' );
		$customer->set_billing_country( 'DE' );
		$customer->set_billing_email( "linker-it-{$tag}@example.test" );
		$customer->save();
		return $customer;
	}

	/**
	 * A published simple product with ten in stock.
	 *
	 * @param string $price Regular price, '' for none.
	 */
	protected function product( string $price ): WC_Product_Simple {
		$product = new WC_Product_Simple();
		$product->set_name( 'Linker integration test product ' . self::tag() );
		$product->set_status( 'publish' );
		$product->set_regular_price( $price );
		$product->set_manage_stock( true );
		$product->set_stock_quantity( 10 );
		$product->save();
		$this->later(
			static function () use ( $product ): void {
				$product->delete( true );
			}
		);
		return $product;
	}

	/**
	 * Logs in a customer, or logs out with 0.
	 *
	 * @param int $user_id User.
	 */
	protected function as_user( int $user_id ): void {
		wp_set_current_user( $user_id );
	}

	/**
	 * An inquiry the customer sends from a solution draft, through WooCommerce's
	 * checkout and the Proforma gateway, as the request page does.
	 *
	 * @param WC_Customer                               $customer The customer, logged in.
	 * @param array<int, array{WC_Product_Simple, int}> $lines    Products and quantities.
	 */
	protected function send_inquiry( WC_Customer $customer, array $lines ): WC_Order {
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->customer = new WC_Customer( $customer->get_id(), true );
		WC()->cart->empty_cart();
		foreach ( $lines as [ $product, $quantity ] ) {
			$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), $quantity ) );
		}
		WC()->cart->calculate_totals();
		$order_id = WC()->checkout()->create_order(
			array(
				'payment_method'     => 'linker_proforma',
				'billing_company'    => $customer->get_billing_company(),
				'billing_first_name' => $customer->get_billing_first_name(),
				'billing_last_name'  => $customer->get_billing_last_name(),
				'billing_address_1'  => $customer->get_billing_address_1(),
				'billing_postcode'   => $customer->get_billing_postcode(),
				'billing_city'       => $customer->get_billing_city(),
				'billing_country'    => $customer->get_billing_country(),
				'billing_email'      => $customer->get_billing_email(),
			)
		);
		$this->assertIsInt( $order_id );
		$this->later(
			static function () use ( $order_id ): void {
				$order = wc_get_order( $order_id );
				if ( $order instanceof WC_Order ) {
					$order->delete( true );
				}
			}
		);
		$gateway = WC()->payment_gateways()->payment_gateways()['linker_proforma'];
		$this->assertSame( 'success', $gateway->process_payment( $order_id )['result'] );
		$order = wc_get_order( $order_id );
		$this->assertInstanceOf( WC_Order::class, $order );
		return $order;
	}
}

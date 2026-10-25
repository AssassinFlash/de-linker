<?php
/**
 * Base of the integration tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\CapacityHealth;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\TestMode;
use PHPUnit\Framework\TestCase;
use WC_Customer;
use WC_Order;
use WC_Product_Simple;

/**
 * Creates customers, products and inquiries in the local instance and removes
 * them again after each test.
 */
abstract class IntegrationTestCase extends TestCase {

	/** Every fixture delivery uses this synthetic tester (AGENTS §5). */
	protected const TESTER = 'tester246@example.test';

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
	 * Every test starts with the mail isolation below.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->isolate_mail();
		$this->isolate_public_connection();
		// In-process fixtures drive their own consumer. Do not let a separate HTTP
		// request consume them before that test installs its simulated provider.
		$queue_runner = static fn (): bool => false;
		add_filter( 'action_scheduler_allow_async_request_runner', $queue_runner, 999 );
		$wake         = static function ( $pre, $args, $url ) {
			if ( str_contains( $url, 'action=as_async_request_queue_runner' ) ) {
				return new \WP_Error( 'fixture_native_queue_wake_blocked' );
			}
			return false === $pre && str_contains( $url, 'action=linker_inquiry_assessment_wake' )
				? new \WP_Error( 'fixture_async_blocked' ) : $pre;
		};
		add_filter( 'pre_http_request', $wake, 999, 3 );
		$this->later(
			static function () use ( $wake, $queue_runner ): void {
				remove_filter( 'pre_http_request', $wake, 999 );
				remove_filter( 'action_scheduler_allow_async_request_runner', $queue_runner, 999 );
			}
		);
	}

	/** Each test has its own public connection window, restored on exit. */
	private function isolate_public_connection(): void {
		$exists                 = array_key_exists( 'REMOTE_ADDR', $_SERVER );
		$address                = $_SERVER['REMOTE_ADDR'] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact runner value for restoration.
		$_SERVER['REMOTE_ADDR'] = '127.0.0.246';
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- preserve the atomic counters without an object cache between SQL and the test.
		$pattern = $wpdb->esc_like( 'linker_commerce_limit_' ) . '%';
		$rows    = $wpdb->get_results( $wpdb->prepare( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s", $pattern ), ARRAY_A );
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $pattern ) );
		$this->later(
			static function () use ( $exists, $address, $pattern, $rows ): void {
				global $wpdb;
				$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $pattern ) );
				foreach ( $rows as $row ) {
					$wpdb->insert( $wpdb->options, array_merge( $row, array( 'autoload' => 'off' ) ) );
				}
				// phpcs:enable
				if ( $exists ) {
					$_SERVER['REMOTE_ADDR'] = $address;
				} else {
					unset( $_SERVER['REMOTE_ADDR'] );
				}
			}
		);
	}

	/**
	 * Gives the test a fresh send quota and an Outbox queue it can count on:
	 * the instance's send record (Throttle::OPTION) is put aside and comes
	 * back afterwards, and every queue row the test writes — with its pending
	 * attempts — is removed, failed or not. Without it a run leaves its
	 * queued and failed messages behind, and the next run's digest counts
	 * them and its sends meet a full daily quota (review of #221, round 1).
	 * setUp() calls it first, so its removal runs after the test's own.
	 */
	private function isolate_mail(): void {
		$capacity_health = get_option( CapacityHealth::OPTION );
		$test_to         = get_option( TestMode::OPTION );
		( new TestMode() )->enable( self::TESTER );
		$ledger = get_option( OptionBudgetLedger::OPTION );
		delete_option( OptionBudgetLedger::OPTION );
		$sends  = get_option( Throttle::OPTION );
		$marker = self::newest_mail_job();
		delete_option( Throttle::OPTION );
		$this->later(
			static function () use ( $sends, $marker, $test_to, $ledger, $capacity_health ): void {
				if ( false === $capacity_health ) {
					delete_option( CapacityHealth::OPTION );
				} else {
					update_option( CapacityHealth::OPTION, $capacity_health, false );
				}
				if ( false === $ledger ) {
					delete_option( OptionBudgetLedger::OPTION );
				} else {
					update_option( OptionBudgetLedger::OPTION, $ledger, false );
				}
				if ( false === $test_to ) {
					delete_option( TestMode::OPTION );
				} else {
					update_option( TestMode::OPTION, $test_to, false );
				}
				foreach ( self::mail_jobs_after( $marker ) as $id ) {
					as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
					wp_delete_post( $id, true );
				}
				if ( false === $sends ) {
					delete_option( Throttle::OPTION );
				} else {
					update_option( Throttle::OPTION, $sends, false );
				}
			}
		);
	}

	/**
	 * The newest Outbox queue row's id, 0 when the queue is empty.
	 */
	protected static function newest_mail_job(): int {
		$ids = self::mail_jobs_after( 0 );
		return array() === $ids ? 0 : max( $ids );
	}

	/**
	 * The ids of the Outbox queue rows written after $marker, oldest first.
	 *
	 * @param int $marker A row id; 0 for every row.
	 * @return list<int>
	 */
	protected static function mail_jobs_after( int $marker ): array {
		$ids = get_posts(
			array(
				'post_type'      => JobStore::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => -1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
				'fields'         => 'ids',
			)
		);
		return array_values( array_filter( array_map( 'intval', $ids ), static fn ( int $id ): bool => $id > $marker ) );
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
		// The fixture is an approved partner account: every journey in these
		// tests runs with prices open. Ticket 73's own tests set the other
		// states on top of this one.
		update_user_meta( $id, \Linker\Commerce\Registration\Approval::STATUS_META, \Linker\Commerce\Registration\Approval::APPROVED );
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
	 * Applies one approval action as the admin-post handler does. The actor
	 * is user 1, so the audit stamp is the staff account and not the customer.
	 *
	 * @param WC_Customer $customer The account.
	 * @param string      $status   The state to set.
	 * @param string      $reason   The reason, required for restrict and reject.
	 */
	protected function set_state( WC_Customer $customer, string $status, string $reason = '' ): void {
		wp_set_current_user( 1 );
		$written = ( new \Linker\Commerce\Registration\Approval() )->set( $customer->get_id(), $status, $reason );
		$this->assertTrue( $written, "The {$status} action was written" );
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

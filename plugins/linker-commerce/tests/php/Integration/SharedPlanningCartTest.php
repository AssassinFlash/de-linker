<?php
/**
 * Shared Woo carts carry products across native principals.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Automattic\WooCommerce\StoreApi\Utilities\CartTokenUtils;
use Linker\Commerce\Planning\DraftTransfer;
use WC_Session_Handler;

/** Native shared-cart initialization and repeat visits. @coversNothing */
final class SharedPlanningCartTest extends IntegrationTestCase {
	/** The source keeps its projects and the recipient keeps projects added after the clone. */
	public function test_shared_cart_copies_quantities_without_transferring_private_reports(): void {
		$this->as_user( 0 );
		$cookies = $_COOKIE;
		$query   = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Preserve the test runner request.
		$cookie  = 'wp_woocommerce_session_' . constant( 'COOKIEHASH' );
		unset( $_COOKIE[ $cookie ], $_GET['session'] );
		$present = static function ( $enabled, $name, $value ) {
			$_COOKIE[ $name ] = $value;
			return false;
		};
		add_filter( 'woocommerce_set_cookie_enabled', $present, 10, 3 );
		$this->later(
			static function () use ( $cookies, $query, $present ): void {
				remove_filter( 'woocommerce_set_cookie_enabled', $present );
				$_COOKIE = $cookies;
				$_GET    = $query;
			}
		);
		$source = $this->native_session();
		$source->set_customer_session_cookie( true );
		$product  = $this->product( '60' )->get_id();
		$original = array(
			'product_id'             => $product,
			'quantity'               => 4,
			DraftTransfer::LINE_META => 'original-project',
		);
		$source->set( 'cart', array( 'battery' => $original ) );
		$source->set( 'removed_cart_contents', array( 'removed' => $original ) );
		$source->set( DraftTransfer::CONTEXTS, array( 'original-project' => 'original project notes' ) );
		$source->set( DraftTransfer::RECEIPTS, array( 'source-receipt' ) );
		$source->save_data();

		unset( $_COOKIE[ $cookie ] );
		$_GET['session'] = CartTokenUtils::get_cart_token( $source->get_customer_id() );
		$recipient       = $this->native_session();
		$this->assertNotSame( $source->get_customer_id(), $recipient->get_customer_id() );
		$this->assertSame( $source->get_customer_id(), $recipient->get( 'previous_customer_id' ) );
		$this->assertNull( $recipient->get( DraftTransfer::CONTEXTS ) );
		$this->assertNull( $recipient->get( DraftTransfer::RECEIPTS ) );
		$row = array(
			'product_id' => $product,
			'quantity'   => 4,
		);
		$this->assertSame( array( 'battery' => $row ), $recipient->get( 'cart' ) );
		$this->assertSame( array( 'removed' => $row ), $recipient->get( 'removed_cart_contents' ) );
		$this->assertSame( $original, $source->get( 'cart' )['battery'] );
		$this->assertSame( array( 'source-receipt' ), $source->get( DraftTransfer::RECEIPTS ) );

		$own = array(
			'product_id'             => $product,
			'quantity'               => 2,
			DraftTransfer::LINE_META => 'recipient-project',
		);
		$recipient->set(
			'cart',
			array(
				'battery' => $row,
				'new'     => $own,
			)
		);
		$recipient->set( DraftTransfer::CONTEXTS, array( 'recipient-project' => 'recipient notes' ) );
		$recipient->set( DraftTransfer::RECEIPTS, array( 'recipient-receipt' ) );
		$recipient->save_data();
		$return = $this->native_session();
		$this->assertSame( $recipient->get_customer_id(), $return->get_customer_id() );
		$this->assertSame( $own, $return->get( 'cart' )['new'] );
		$this->assertSame( array( 'recipient-project' => 'recipient notes' ), $return->get( DraftTransfer::CONTEXTS ) );
		$this->assertSame( array( 'recipient-receipt' ), $return->get( DraftTransfer::RECEIPTS ) );
	}

	/** Initialize a fresh request through Woo's selected session handler. */
	private function native_session(): WC_Session_Handler {
		/** This filter is documented in WooCommerce::initialize_session(). */
		$class   = apply_filters( 'woocommerce_session_handler', WC_Session_Handler::class ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Native Woo extension point.
		$session = new $class();
		$this->assertInstanceOf( WC_Session_Handler::class, $session );
		$session->init();
		$this->later(
			static function () use ( $session ): void {
				remove_action( 'shutdown', array( $session, 'save_data' ), 20 );
				remove_action( 'wp_logout', array( $session, 'destroy_session' ) );
				$session->delete_session( $session->get_customer_id() );
			}
		);
		return $session;
	}
}

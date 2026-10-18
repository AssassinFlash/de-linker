<?php
/**
 * Isolated records, mail and limits for local browser tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\E2E;

use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use RuntimeException;

// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Local test fixtures preserve atomic rate rows and identify their own queue records; no production execution.

/** Each fixture restores only its own options and synthetic records. */
final class BrowserFixture {

	/**
	 * Requires the isolated local site's file mail sink.
	 *
	 * @param string $key Fixture option.
	 * @param string $tester Single local recipient.
	 * @throws RuntimeException When the site is not an isolated local instance.
	 */
	public function __construct( private readonly string $key, private readonly string $tester ) {
		if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
			throw new RuntimeException( 'Local isolated WordPress required.' );
		}
		foreach ( array( $key, Throttle::OPTION, TestMode::OPTION ) as $option ) {
			wp_cache_delete( $option, 'options' );
		}
	}

	/**
	 * Holds all mail and saves the original counters and recipient option.
	 *
	 * @param string $email Unique customer email identifying owned records.
	 * @throws RuntimeException When a previous fixture still requires cleanup.
	 */
	public function setup( string $email ): void {
		if ( false !== get_option( $this->key ) ) {
			throw new RuntimeException( 'Browser fixture already exists; clean it up first.' );
		}
		global $wpdb;
		$state = array(
			'email'     => $email,
			'options'   => array(
				Throttle::OPTION => get_option( Throttle::OPTION ),
				TestMode::OPTION => get_option( TestMode::OPTION ),
			),
			'marker'    => (int) $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts} WHERE post_type='linker_mail_job'" ),
			'limits'    => $wpdb->get_results( $wpdb->prepare( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( 'linker_commerce_limit_' ) . '%' ), ARRAY_A ),
			'transient' => get_transient( 'linker_contact_' . md5( '127.0.0.1' ) ),
			'products'  => array(),
		);
		update_option( $this->key, $state, false );
		$this->clear_limits();
		delete_transient( 'linker_contact_' . md5( '127.0.0.1' ) );
		( new TestMode() )->enable( $this->tester );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false );
	}

	/**
	 * Stored fixture values, read across CLI and browser requests.
	 *
	 * @return array<string, mixed>
	 * @throws RuntimeException When setup has not saved fixture state.
	 */
	public function state(): array {
		$state = get_option( $this->key );
		if ( ! is_array( $state ) ) {
			throw new RuntimeException( 'No browser fixture to read or restore.' );
		}
		return $state;
	}

	/**
	 * Registers a synthetic product for cleanup before the next browser step.
	 *
	 * @param int $id Product id.
	 */
	public function add_product( int $id ): void {
		$state               = $this->state();
		$state['products'][] = $id;
		update_option( $this->key, $state, false );
	}

	/**
	 * The synthetic customer's inquiries.
	 *
	 * @return array<\WC_Order>
	 */
	public function orders(): array {
		return wc_get_orders(
			array(
				'billing_email' => $this->state()['email'],
				'limit'         => -1,
			)
		);
	}

	/**
	 * Newer queue rows must also belong to the fixture's unique email.
	 *
	 * @return list<int>
	 */
	public function jobs(): array {
		global $wpdb;
		$state = $this->state();
		$ids   = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE post_type='linker_mail_job' AND ID > %d ORDER BY ID", $state['marker'] ) );
		return array_values(
			array_filter(
				array_map( 'intval', $ids ),
				static function ( int $id ) use ( $state ): bool {
					$message = json_decode( get_post_meta( $id, '_linker_mail_message', true ), true );
					return is_array( $message ) && ( in_array( $state['email'], $message['to'], true ) || str_contains( $message['body'], $state['email'] ) );
				}
			)
		);
	}

	/** Removes only this local run's atomic public rate counters. */
	private function clear_limits(): void {
		global $wpdb;
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( 'linker_commerce_limit_' ) . '%' ) );
	}

	/**
	 * Restores saved state and removes owned records even after a failed assertion.
	 *
	 * @param bool $delete_customer This fixture also created the synthetic customer.
	 */
	public function cleanup( bool $delete_customer = false ): void {
		global $wpdb;
		$state = $this->state();
		foreach ( $this->orders() as $order ) {
			$order->delete( true );
		}
		foreach ( $this->jobs() as $id ) {
			as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
			wp_delete_post( $id, true );
		}
		foreach ( $state['products'] as $id ) {
			$product = wc_get_product( $id );
			if ( $product ) {
				$product->delete( true );
			}
		}
		$user = $delete_customer ? get_user_by( 'email', $state['email'] ) : false;
		if ( $user ) {
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user->ID );
		}
		foreach ( $state['options'] as $option => $value ) {
			if ( false === $value ) {
				delete_option( $option );
			} else {
				update_option( $option, $value, false );
			}
			wp_cache_delete( $option, 'options' );
		}
		$this->clear_limits();
		foreach ( $state['limits'] as $row ) {
			$wpdb->insert( $wpdb->options, array_merge( $row, array( 'autoload' => 'off' ) ) );
		}
		delete_transient( 'linker_contact_' . md5( '127.0.0.1' ) );
		if ( false !== $state['transient'] ) {
			set_transient( 'linker_contact_' . md5( '127.0.0.1' ), $state['transient'], HOUR_IN_SECONDS );
		}
		delete_option( $this->key );
		wp_cache_delete( $this->key, 'options' );
	}
}
